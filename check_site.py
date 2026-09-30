#!/usr/bin/env python3
"""Check the static site's local links and deployment metadata."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
DOMAIN = "mirroview.liljackson.org"
PAGES = ("index.html", "privacy.html", "terms.html", "support.html")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.canonical = []
        self.title = False
        self.description = False
        self.viewport = False
        self.h1 = 0
        self.languages = set()
        self.embedded_assets = []
        self.has_script_or_form = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if attrs.get("lang"):
            self.languages.add(attrs["lang"])
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "link":
            if attrs.get("rel") == "canonical":
                self.canonical.append(attrs.get("href"))
            if attrs.get("rel") == "stylesheet":
                self.links.append(attrs.get("href", ""))
        if tag in ("script", "form"):
            self.has_script_or_form = True
        if tag in ("img", "video", "audio", "source", "iframe"):
            self.embedded_assets.append(attrs.get("src") or attrs.get("srcset") or "")
        if tag == "title":
            self.title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "meta" and attrs.get("name") == "description":
            self.description = bool(attrs.get("content"))
        if tag == "meta" and attrs.get("name") == "viewport":
            self.viewport = bool(attrs.get("content"))


def main():
    errors = []
    if (ROOT / "CNAME").read_text().strip() != DOMAIN:
        errors.append("CNAME must contain the exact domain")
    if not (ROOT / ".nojekyll").exists():
        errors.append(".nojekyll is missing")

    pages = {}
    for name in PAGES:
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing {name}")
            continue
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        pages[name] = parser
        expected = f"https://{DOMAIN}/" + ("" if name == "index.html" else name)
        if parser.canonical != [expected]:
            errors.append(f"{name}: expected canonical {expected}")
        if not (parser.title and parser.description and parser.viewport and parser.h1 == 1):
            errors.append(f"{name}: missing title, description, viewport, or one h1")
        if not {"en", "zh-Hans"}.issubset(parser.languages):
            errors.append(f"{name}: missing English or Chinese language marker")
        if not all(other in parser.links for other in PAGES):
            errors.append(f"{name}: main navigation lacks a page")
        if parser.has_script_or_form or parser.embedded_assets:
            errors.append(f"{name}: unexpected script, form, or embedded asset")
        if "mailto:mirroview@liljackson.org" not in " ".join(parser.links):
            if name in ("privacy.html", "terms.html", "support.html"):
                errors.append(f"{name}: contact email is missing")

    for name, parser in pages.items():
        for link in parser.links:
            parts = urlsplit(link)
            if parts.scheme in ("mailto", "https"):
                continue
            if parts.scheme or parts.netloc:
                errors.append(f"{name}: unsupported link {link}")
                continue
            target = unquote(parts.path) or name
            if target.startswith("/") or ".." in Path(target).parts:
                errors.append(f"{name}: nonlocal path {link}")
                continue
            if not (ROOT / target).is_file():
                errors.append(f"{name}: broken link {link}")
            if parts.fragment:
                target_page = pages.get(target)
                if target_page and parts.fragment not in target_page.ids:
                    errors.append(f"{name}: missing anchor {link}")

    if errors:
        for error in errors:
            print("FAIL", error)
        raise SystemExit(1)
    print(f"PASS {len(PAGES)} pages, internal links, bilingual markers, canonical URLs, CNAME, .nojekyll")


if __name__ == "__main__":
    main()
