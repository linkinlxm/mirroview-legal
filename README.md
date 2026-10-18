# mirroview website

This directory is a self-contained static site for `https://mirroview.liljackson.org/`. GitHub Pages can publish it from the repository root. It has four routes: `index.html`, `privacy.html`, `terms.html`, and `support.html`. Each page contains English and Simplified Chinese text. `styles.css` is the only browser asset. The site has no client-side scripts, external fonts, forms, trackers, or build step.

Run the local content and link check before publishing:

```sh
python3 check_site.py
```

Keep `CNAME` and `.nojekyll` at the published root. After creating the separate repository and enabling GitHub Pages, configure the DNS record for `mirroview.liljackson.org` to point to that Pages site. DNS and Pages settings are outside this directory.

The public copy covers the current iPhone/iPad release (iOS/iPadOS 17+), recommends the same reachable local Wi-Fi for initial sessions, and describes nearby sharing without guaranteeing every router-free or mixed-network setup. Diagnostic export is voluntary and stays local until the user shares it. Update both languages when shipped behavior changes; do not turn source implementation or simulator checks into claims of real-device E2E reliability.
