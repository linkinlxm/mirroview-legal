#!/usr/bin/env python3
"""Render the static site from reviewed, complete locale dictionaries."""

import argparse
import html
import json
import posixpath
import string
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent
DOMAIN = "https://mirroview.liljackson.org"
EMAIL = "mirroview@liljackson.org"
PAGE_FILES = {"home": "index.html", "privacy": "privacy.html", "terms": "terms.html", "support": "support.html"}
LANGUAGES = json.loads((ROOT / "languages.json").read_text(encoding="utf-8"))
STRUCTURE = json.loads((ROOT / "page-structure.json").read_text(encoding="utf-8"))


def route(locale, page):
    filename = PAGE_FILES[page]
    return PurePosixPath(filename) if locale == "en" else PurePosixPath(locale, filename)


def public_url(locale, page):
    path = str(route(locale, page))
    if page == "home":
        path = path.removesuffix("index.html")
    return f"{DOMAIN}/{path}"


def relative(current, target):
    return posixpath.relpath(str(target), str(current.parent))


def placeholders(value):
    return sorted(field for _, field, _, _ in string.Formatter().parse(value) if field is not None)


def dictionaries(locales):
    reference = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
    result = {}
    for locale in locales:
        path = ROOT / "locales" / f"{locale}.json"
        if not path.is_file():
            raise ValueError(f"Missing reviewed locale dictionary: {path.relative_to(ROOT)}")
        values = json.loads(path.read_text(encoding="utf-8"))
        if values.keys() != reference.keys():
            missing = sorted(reference.keys() - values.keys())
            extra = sorted(values.keys() - reference.keys())
            raise ValueError(f"{locale}: missing keys {missing}; extra keys {extra}")
        for key, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{locale}: {key} must contain text")
            if placeholders(value) != placeholders(reference[key]):
                raise ValueError(f"{locale}: {key} changed placeholders")
            if "<" in value or ">" in value:
                raise ValueError(f"{locale}: {key} contains markup; translations must be plain text")
        result[locale] = values
    return result


def image_for(locale):
    localized = PurePosixPath("assets", locale, "screen-sharing.png")
    if (ROOT / localized).is_file():
        return localized, False
    fallback = "screen-sharing-zh.png" if locale == "zh-Hans" else "screen-sharing-en.png"
    return PurePosixPath("assets", fallback), True


def render(locale, page, values, locales):
    current = route(locale, page)
    def t(key):
        text = html.escape(values[key])
        email = f'<!--email_off--><a href="mailto:{EMAIL}">{EMAIL}</a><!--/email_off-->'
        return text.replace("{email}", email)
    def link(page_id):
        return html.escape(relative(current, route(locale, page_id)), quote=True)
    def nav(footer=False):
        links = []
        for other in PAGE_FILES:
            active = ' aria-current="page"' if page == other else ""
            links.append(f'<a href="{link(other)}"{active}>{t("nav." + other)}</a>')
        if footer:
            links.append(f'<!--email_off--><a href="mailto:{EMAIL}">{t("nav.email")}</a><!--/email_off-->')
        label = "nav.footer" if footer else "nav.main"
        return f'<nav class="{"footer-nav" if footer else "nav"}" aria-label="{t(label)}">' + "".join(links) + "</nav>"
    alternatives = []
    language_links = []
    for target in locales:
        url = html.escape(public_url(target, page), quote=True)
        alternatives.append(f'  <link rel="alternate" hreflang="{target}" href="{url}">')
        active = ' aria-current="page"' if target == locale else ""
        legacy = ' id="zh"' if locale == "en" and target == "zh-Hans" else ""
        href = html.escape(relative(current, route(target, page)), quote=True)
        language_links.append(f'<a href="{href}" lang="{target}" hreflang="{target}"{active}{legacy}>{html.escape(LANGUAGES[target])}</a>')
    alternatives.append(f'  <link rel="alternate" hreflang="x-default" href="{html.escape(public_url("en", page), quote=True)}">')
    language_picker = f'<details class="language-picker"><summary>{t("nav.language")} · {html.escape(LANGUAGES[locale])}</summary><nav aria-label="{t("nav.language")}">' + "".join(language_links) + "</nav></details>"
    heading = f'<p class="eyebrow">{t(page + ".eyebrow")}</p><h1>{t(page + ".heading")}</h1><p class="lede">{t(page + ".lede")}</p>'
    image, fallback = image_for(locale)
    if page == "home":
        content = f'<section class="hero"><div class="wrap">{heading}<div class="hero-actions"><a class="button" href="{link("support")}">{t("home.cta.support")}</a><a class="button secondary" href="{link("privacy")}">{t("home.cta.privacy")}</a></div></div></section>'
        content += f'<figure class="product-visual wrap"><img src="{html.escape(relative(current, image), quote=True)}" width="1920" height="1280" alt="{t("home.image_alt")}" fetchpriority="high" decoding="async"></figure>'
        content += f'<section class="section"><div class="wrap"><h2>{t("home.connection.heading")}</h2><div class="grid">'
        for part in ("pair", "screen", "control"):
            content += f'<article class="card"><h3>{t("home." + part + ".heading")}</h3><p>{t("home." + part + ".body")}</p></article>'
        content += f'</div></div></section><section class="section"><div class="wrap"><h2>{t("home.limits.heading")}</h2><p class="lede">{t("home.limits.body")}</p><p><a href="{link("terms")}">{t("home.cta.terms")}</a></p></div></section>'
        main_class = ""
    else:
        content = heading + f'<p class="meta">{t("date.updated" if page == "support" else "date.effective")}</p>'
        if page == "support":
            content += f'<div class="notice"><p>{t("support.notice")}</p></div>'
        for section in STRUCTURE[page]["sections"]:
            content += f'<section><h2>{t(section["heading"])}</h2>'
            for block in section["blocks"]:
                if block["tag"] == "p":
                    content += f'<p>{t(block["key"])}</p>'
                else:
                    tag = block["tag"]
                    content += f'<{tag}>' + "".join(f'<li>{t(key)}</li>' for key in block["items"]) + f'</{tag}>'
            content += "</section>"
        main_class = ' class="page prose"'
    document = f'''<!doctype html>
<html lang="{locale}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{t(page + ".description")}">
  <meta name="referrer" content="no-referrer">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'">
  <link rel="canonical" href="{html.escape(public_url(locale, page), quote=True)}">
{chr(10).join(alternatives)}
  <link rel="stylesheet" href="{html.escape(relative(current, PurePosixPath("styles.css")), quote=True)}">
  <title>{t(page + ".title")}</title>
</head>
<body>
  <a class="skip" href="#main">{t("nav.skip")}</a>
  <header class="masthead"><div class="wrap"><a class="brand" href="{link("home")}"><span class="brand-mark" aria-hidden="true"></span>mirroview</a>{nav()}{language_picker}</div></header>
  <main id="main"{main_class}>{content}</main>
  <footer class="footer"><div class="wrap"><span>© 2026 mirroview</span>{nav(footer=True)}</div></footer>
</body>
</html>
'''
    return document, {"locale": locale, "page": page, "path": str(current), "image": str(image) if page == "home" else None, "image_fallback": fallback if page == "home" else False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locales", help="Comma-separated locale subset for development; default: every configured language")
    parser.add_argument("--check", action="store_true", help="Fail if committed HTML differs from dictionary rendering")
    args = parser.parse_args()
    locales = args.locales.split(",") if args.locales else list(LANGUAGES)
    if "en" not in locales or any(locale not in LANGUAGES for locale in locales):
        raise SystemExit("Locale selection must include en and use configured languages")
    values = dictionaries(locales)
    manifest = []
    stale = []
    for locale in locales:
        for page in PAGE_FILES:
            document, entry = render(locale, page, values[locale], locales)
            destination = ROOT / route(locale, page)
            if args.check:
                if not destination.is_file() or destination.read_text(encoding="utf-8") != document:
                    stale.append(str(destination.relative_to(ROOT)))
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(document, encoding="utf-8")
            manifest.append(entry)
    if stale:
        raise SystemExit("Stale generated pages: " + ", ".join(stale))
    if not args.check:
        (ROOT / "site-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f'{"Verified" if args.check else "Rendered"} {len(manifest)} pages in {len(locales)} languages')


if __name__ == "__main__":
    main()
