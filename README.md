# mirroview website

This directory is a self-contained static site for `https://mirroview.liljackson.org/`. GitHub Pages can publish it from the repository root. It has four routes: `index.html`, `privacy.html`, `terms.html`, and `support.html`. Each page contains English and Simplified Chinese text. `styles.css` is the only browser asset. The site has no client-side scripts, external fonts, forms, trackers, or build step.

Run the local content and link check before publishing:

```sh
python3 check_site.py
```

Keep `CNAME` and `.nojekyll` at the published root. After creating the separate repository and enabling GitHub Pages, configure the DNS record for `mirroview.liljackson.org` to point to that Pages site. DNS and Pages settings are outside this directory.

The current public copy describes same reachable local Wi-Fi and the release WebRTC path. It does not treat development-only direct media, diagnostic logs, or no-access-point experiments as release features. Update both languages when the shipped behavior changes.
