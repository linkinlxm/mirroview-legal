# mirroview website

This directory is a static site for `https://mirroview.liljackson.org/`. GitHub Pages publishes the generated HTML from the repository root. Each configured language has complete Home, Privacy, Terms, and Support pages. English retains the original root URLs. Other languages use `/<locale>/index.html`, `privacy.html`, `terms.html`, and `support.html`. The language picker stays on the equivalent page. The site has no client-side scripts, external fonts, forms, or trackers.

`languages.json` defines the supported locale codes and native language names. Plain-text translations live in `locales/<locale>.json`. Every dictionary must have the same semantic keys and placeholders as `locales/en.json`. `{email}` is replaced with the fixed support email link during rendering. `page-structure.json` defines shared section/list structure. Review all added or changed translations through AGY before generating release files.

Supply a real, matching-language App screenshot marketing image at `assets/<locale>/screen-sharing.png`, sized 1920×1280. The renderer permits the old English/Chinese images as development fallbacks; the release check rejects fallbacks.

Generate and check all configured languages before publishing:

```sh
python3 build_site.py
python3 check_site.py --require-localized-assets
```

Keep `CNAME` and `.nojekyll` at the published root. After creating the separate repository and enabling GitHub Pages, configure the DNS record for `mirroview.liljackson.org` to point to that Pages site. DNS and Pages settings are outside this directory.

The check validates every dictionary, placeholder, generated page, local link, language route, canonical URL, hreflang alternate, image reference, and the content security policy. To preview only complete base languages during development, pass the same `--locales en,zh-Hans` subset to both scripts. A subset check does not verify the full release.

The public copy covers the current iPhone/iPad release (iOS/iPadOS 17+), recommends the same reachable local Wi-Fi for initial sessions, and describes nearby sharing without guaranteeing every router-free or mixed-network setup. Diagnostic export is voluntary and stays local until the user shares it. Preserve the original policy/terms effective date, October 2, 2026. Update every language when shipped behavior changes; source or simulator checks do not establish real-device E2E reliability.
