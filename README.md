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

The site is fully static. `scripts/build.sh` assembles the deployable tree into
`dist/`; deploys are currently made by hand from there. The source tree makes no
external requests — React and the fonts are vendored — so a clone runs
standalone and offline, and the analytics beacon is injected only at build time
when `CF_WEB_ANALYTICS_TOKEN` is set. A fork therefore never reports to someone
else's account.

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
assets/js/dc-runtime.js        renderer for the x-dc document
assets/js/react*.min.js        React 18.3.1 UMD builds, vendored
assets/fonts/*.woff2           Inter and Archivo subsets, vendored
```

`index.html` was unpacked from a self-contained HTML export: the embedded
base64 assets were written out as real files and the CDN references rewired to
the vendored copies via `window.__resources`.
