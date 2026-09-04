# Imaging Planner

A single-page astrophotography session planner. For a given site, date and
altitude threshold it shows how many hours of astronomical darkness (Sun below
−18°) each patch of sky is actually usable for.

- **Usable dark hours by RA / Dec** — heatmap of usable hours across the whole
  sky, with the ecliptic, the Moon and its ±30° dimming radius overlaid.
- **Hours above altitude** — hours above 0/20/40/60/80° as a function of
  declination, for the current latitude.

Presets for several remote observatories (Starfront, Death Valley, Utah Desert,
Sierra, Dark Sky New Mexico, Deep Sky Chile), or use your own coordinates /
browser geolocation. Either view exports to PNG.

Everything runs client-side; there is no backend and no network access at
runtime.

## Hosting

Live at <https://astroplanner.ambroslabs.io>, on Cloudflare Pages.

The site is fully static. `.github/workflows/deploy.yml` runs
`scripts/build.sh` on every push to `main` and uploads the resulting `dist/`
to Cloudflare Pages. The source tree makes no external requests — React and
the fonts are vendored — so a clone runs standalone and offline, and the
analytics beacon is injected only at build time when `CF_WEB_ANALYTICS_TOKEN`
is set. A fork therefore never reports to someone else's account.

CI needs two repository secrets, `CLOUDFLARE_API_TOKEN` (Account → Cloudflare
Pages: Edit) and `CLOUDFLARE_ACCOUNT_ID`, plus the `CF_WEB_ANALYTICS_TOKEN`
variable. A fork with none of them set still builds; only the deploy step fails.

`_worker.js` runs in front of the static assets and does one thing: 301 the
project's canonical `astroplanner.pages.dev` URL to the custom domain, so the
site has a single address. Per-deployment preview URLs are left alone.

## Local preview

```sh
python3 -m http.server 8000
# http://localhost:8000
```

Opening `index.html` over `file://` does not work — the runtime fetches its
scripts and fonts over HTTP.

## Layout

```
index.html                     markup + component logic (x-dc format)
_worker.js                     Pages worker: pages.dev -> domain, catalogue caching
scripts/build.sh               assembles dist/, injects the analytics beacon
scripts/build-catalogs.py      regenerates assets/catalogs/ from the source lists
assets/catalogs/*.txt          deep-sky catalogues, content-hashed, fetched on demand
assets/js/dc-runtime.js        renderer for the x-dc document
assets/js/react*.min.js        React 18.3.1 UMD builds, vendored
assets/fonts/*.woff2           Inter and Archivo subsets, vendored
```

`index.html` was unpacked from a self-contained HTML export: the embedded
base64 assets were written out as real files and the CDN references rewired to
the vendored copies via `window.__resources`.


## Catalogues

Ten deep-sky catalogues, 14,861 objects: Messier, Caldwell, Herschel 400, NGC,
IC, Sharpless, Barnard, van den Bergh, Lynds dark nebulae and Arp. Messier is
the only one on by default.

Each is a separate file under `assets/catalogs/`, fetched the first time its
layer is switched on and not before - turning NGC on costs 74 KB gzipped once,
and never turning it on costs nothing. Every filename carries a hash of its own
contents, so the bytes behind a URL can never change, which is what lets
`_worker.js` serve them `immutable` with a one-year max-age: a reader downloads
each catalogue at most once ever rather than revalidating it on every visit.
That has to happen in the worker, because Pages ignores `_headers` for anything
served through an advanced-mode `_worker.js`.

Rows are stored as deltas from the row before, which is worth about a third
against plain values and keeps every field - position, type, magnitude, major
and minor axis, position angle and common name. Each delta is measured from the
value the decoder will have reconstructed rather than the true one, so rounding
cannot accumulate down the file.

Regenerate with `python3 scripts/build-catalogs.py`. It fetches from OpenNGC
(CC-BY-SA-4.0) for NGC, IC and the Messier numbers, VizieR for Sharpless,
Barnard, van den Bergh, Lynds and Arp, Wikipedia for the Caldwell and
Herschel 400 lists, and SIMBAD for the popular names the source lists omit -
without which the Horsehead cannot be found by the only word anyone calls it.
It prints the `CATALOGS` block to paste into `index.html`, since the filenames
change whenever the data does.
