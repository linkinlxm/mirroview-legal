#!/usr/bin/env python3
"""Validate every translated page, local link, language route, and image."""

import argparse
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import build_site


ROOT = Path(__file__).resolve().parent


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.canonical = []
        self.alternates = {}
        self.title = False
        self.description = False
        self.viewport = False
        self.csp = None
        self.h1 = 0
        self.lang = None
        self.images = []
        self.unexpected_embeds = []

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "link":
            if attrs.get("rel") == "canonical":
                self.canonical.append(attrs.get("href"))
            if attrs.get("rel") == "alternate":
                self.alternates[attrs.get("hreflang")] = attrs.get("href")
            if attrs.get("rel") == "stylesheet":
                self.links.append(attrs.get("href", ""))
        if tag in ("script", "form", "iframe", "video", "audio", "source"):
            self.unexpected_embeds.append(tag)
        if tag == "img":
            self.images.append(attrs)
            self.links.append(attrs.get("src", ""))
        if tag == "title":
            self.title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "meta":
            if attrs.get("name") == "description":
                self.description = bool(attrs.get("content"))
            if attrs.get("name") == "viewport":
                self.viewport = bool(attrs.get("content"))
            if attrs.get("http-equiv", "").lower() == "content-security-policy":
                self.csp = attrs.get("content")


def local_target(name, value):
    parts = urlsplit(value)
    if parts.scheme == "mailto":
        if parts.path != build_site.EMAIL:
            raise ValueError(f"unexpected mail recipient: {value}")
        return None, None
    if parts.scheme or parts.netloc:
        if parts.scheme != "https" or parts.netloc != urlsplit(build_site.DOMAIN).netloc:
            raise ValueError(f"unexpected external destination: {value}")
        target = ROOT / unquote(parts.path).lstrip("/")
    else:
        target = ROOT / name.parent / unquote(parts.path) if parts.path else ROOT / name
    target = target.resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError(f"path escapes the site: {value}")
    if target.is_dir():
        target = target / "index.html"
    return target, parts.fragment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locales", help="Comma-separated locale subset for development")
    parser.add_argument("--require-localized-assets", action="store_true", help="Reject fallback images; use for release verification")
    args = parser.parse_args()
    locales = args.locales.split(",") if args.locales else list(build_site.LANGUAGES)
    errors = []
    if (ROOT / "CNAME").read_text().strip() != urlsplit(build_site.DOMAIN).netloc:
        errors.append("CNAME must contain the exact domain")
    if not (ROOT / ".nojekyll").is_file():
        errors.append(".nojekyll is missing")
    try:
        build_site.dictionaries(locales)
    except (ValueError, KeyError) as error:
        errors.append(str(error))
    command = [sys.executable, str(ROOT / "build_site.py"), "--check"]
    if args.locales:
        command.extend(["--locales", args.locales])
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        errors.append(result.stderr.strip() or result.stdout.strip())
    pages = {}
    for locale in locales:
        for page in build_site.PAGE_FILES:
            name = build_site.route(locale, page)
            path = ROOT / name
            if not path.is_file():
                errors.append(f"missing {name}")
                continue
            parsed = PageParser()
            parsed.feed(path.read_text(encoding="utf-8"))
            pages[path.resolve()] = parsed
            if parsed.lang != locale:
                errors.append(f"{name}: expected html lang={locale}")
            if parsed.canonical != [build_site.public_url(locale, page)]:
                errors.append(f"{name}: incorrect canonical")
            expected_alternates = {key: build_site.public_url(key, page) for key in locales}
            expected_alternates["x-default"] = build_site.public_url("en", page)
            if parsed.alternates != expected_alternates:
                errors.append(f"{name}: incomplete or incorrect hreflang alternates")
            if not (parsed.title and parsed.description and parsed.viewport and parsed.h1 == 1):
                errors.append(f"{name}: missing title, description, viewport, or one h1")
            if parsed.csp != "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'":
                errors.append(f"{name}: content security policy changed")
            if parsed.unexpected_embeds:
                errors.append(f"{name}: unexpected script, form, or embedded media")
            for other in build_site.PAGE_FILES:
                expected = build_site.relative(name, build_site.route(locale, other))
                if expected not in parsed.links:
                    errors.append(f"{name}: navigation lacks {other}")
            for other in locales:
                expected = build_site.relative(name, build_site.route(other, page))
                if expected not in parsed.links:
                    errors.append(f"{name}: language picker lacks {other}")
            if f"mailto:{build_site.EMAIL}" not in parsed.links:
                errors.append(f"{name}: contact email missing")
            if page == "home":
                expected_image, fallback = build_site.image_for(locale)
                if args.require_localized_assets and fallback:
                    errors.append(f"{name}: localized hero image missing")
                if len(parsed.images) != 1:
                    errors.append(f"{name}: expected one product image")
                for image in parsed.images:
                    expected_src = build_site.relative(name, expected_image)
                    if image.get("src") != expected_src or not image.get("alt"):
                        errors.append(f"{name}: image source or alt text incorrect")
                    if image.get("width") != "1920" or image.get("height") != "1280":
                        errors.append(f"{name}: image needs exact 1920×1280 dimensions")
            elif parsed.images:
                errors.append(f"{name}: unexpected product image")
    for path, parsed in pages.items():
        name = path.relative_to(ROOT)
        for link in parsed.links + list(parsed.alternates.values()) + parsed.canonical:
            try:
                target, fragment = local_target(name, link)
            except ValueError as error:
                errors.append(f"{name}: {error}")
                continue
            if target is None:
                continue
            if not target.is_file():
                errors.append(f"{name}: broken link {link}")
            if fragment and target in pages and fragment not in pages[target].ids:
                errors.append(f"{name}: missing anchor {link}")
    if errors:
        for error in errors:
            print("FAIL", error)
        raise SystemExit(1)
    mode = "localized images" if args.require_localized_assets else "development image fallbacks permitted"
    print(f"PASS {len(pages)} pages, {len(locales)} languages, complete dictionaries/placeholders, links, hreflang, canonical URLs, CSP, {mode}")


if __name__ == "__main__":
    main()
