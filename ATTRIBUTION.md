# Attribution and licences

Everything this planner draws comes from someone else's work. This file records
what each piece is, where it came from, and what its licence asks of us. Three of
these licences make attribution a condition of use rather than a courtesy, so
this file is part of what the site distributes, not a footnote to it.

A plain-text copy is served at <https://astroplanner.ambroslabs.io/attribution.txt>
and linked from the chart itself.

---

## Deep-sky object catalogues

### OpenNGC — NGC and IC, and the data behind Messier, Caldwell and Herschel 400

Positions, object types, apparent sizes, position angles, magnitudes, surface
brightnesses, Hubble types and constellation assignments.

- Source: <https://github.com/mattiaverga/OpenNGC>
- Author: Mattia Verga
- Licence: **CC BY-SA 4.0** — see `licenses/CC-BY-SA-4.0.txt`
- DOI: [10.21938/y.1ejWUD_MQ6b_eDFoVbbw](https://dc.zah.uni-heidelberg.de/voidoi/q/lp/custom/10.21938/y.1ejWUD_MQ6b_eDFoVbbw)

**Share-alike.** The catalogue files under `assets/catalogs/` are a derivative of
this database, and are therefore themselves offered under CC BY-SA 4.0. They are
served as plain text at stable URLs; anyone may take them.

### VizieR — Sharpless, Barnard, van den Bergh, Lynds and Arp

Positions and diameters, retrieved from the VizieR catalogue access tool at CDS.

| Layer | VizieR catalogue | Original publication |
| --- | --- | --- |
| Sharpless | VII/20 | Sharpless (1959), *ApJS* **4**, 257 |
| Barnard | VII/220A | Barnard (1927), *A photographic atlas of selected regions of the Milky Way* |
| van den Bergh | VII/21 | van den Bergh (1966), *AJ* **71**, 990 |
| Lynds dark nebulae | VII/7A | Lynds (1962), *ApJS* **7**, 1 |
| Arp | VII/192 | Arp (1966), *ApJS* **14**, 1 |

- Service: <https://vizier.cds.unistra.fr/> — DOI [10.26093/cds/vizier](https://doi.org/10.26093/cds/vizier)
- Rules of usage: <https://cds.unistra.fr/vizier-org/licences_vizier.html>

> This research has made use of the VizieR catalogue access tool, CDS,
> Strasbourg Astronomical Observatory, France (DOI: 10.26093/cds/vizier).
> The original description of the VizieR service was published in 2000, A&AS
> 143, 23 — Ochsenbein, Bauer & Marcout.

**Note on scope.** VizieR states the data are free of usage in a scientific
context, that the original authors and publications must be cited, and that
*commercial usage is subject to rules depending on the origin of each
catalogue*. This site is free to use and carries no advertising. Anyone
intending to make commercial use of it should check the individual catalogues
first.

### SIMBAD — common names, and the stars in the constellation figures

Popular names for objects whose source catalogues carry none, and the coordinates
of the naked-eye stars the constellation lines are drawn between.

- Service: <https://simbad.cds.unistra.fr/>

> This research has made use of the SIMBAD database, operated at CDS,
> Strasbourg, France. The original description of the SIMBAD service was
> published in 2000, A&AS 143, 9 — Wenger et al.

### Wikipedia — the Messier, Caldwell and Herschel 400 membership lists

Which objects belong to each list, and the common names attached to them, read
from the raw wikitext of *Messier object*, *Caldwell catalogue* and *Herschel 400
Catalogue*.

- Licence: **CC BY-SA 4.0** — see `licenses/CC-BY-SA-4.0.txt`
- <https://en.wikipedia.org/wiki/Messier_object>
- <https://en.wikipedia.org/wiki/Caldwell_catalogue>
- <https://en.wikipedia.org/wiki/Herschel_400_Catalogue>

---

## Time zones

### Zone boundaries — OpenStreetMap via timezone-boundary-builder

`assets/catalogs/timezones.*.txt` is a 0.1° raster of IANA zone names for the
whole globe, built by `scripts/build-timezones.py` from the boundary set below.

- Source: <https://github.com/evansiroky/timezone-boundary-builder> (release 2026c)
- Underlying data: © OpenStreetMap contributors, <https://www.openstreetmap.org/copyright>
- Licence: **ODbL 1.0** — see `licenses/ODbL-1.0.txt`
  (the project's own *code* is MIT; the released *data* is ODbL)

**Share-alike.** The raster is a derived database and is therefore itself offered
under ODbL 1.0. It is served as plain text at a stable URL and the script that
produces it is in this repository, so anyone may reproduce or take it.

### Zone rules — the IANA time zone database

Offsets and daylight-saving rules are never shipped by this site. It resolves a
place to an IANA zone *name* and hands that name to the browser, which applies
its own copy of the tz database through `Intl.DateTimeFormat`.

- <https://www.iana.org/time-zones> — the tz database is in the public domain.

---

## Typefaces

Both are served from `assets/fonts/`, subset to the ranges the page uses.

| Family | Copyright | Licence |
| --- | --- | --- |
| Inter | © 2016 The Inter Project Authors | **OFL 1.1** — `assets/fonts/OFL-Inter.txt` |
| Archivo | © 2020 The Archivo Project Authors | **OFL 1.1** — `assets/fonts/OFL-Archivo.txt` |

---

## Software

| Component | Licence |
| --- | --- |
| React 18.3.1 (`react`, `react-dom`, loaded from unpkg) | MIT — © Meta Platforms, Inc. and affiliates |

---

## Astronomy the site computes rather than fetches

Solar and lunar positions, planetary positions from Keplerian elements, sidereal
time, hour angles and the dark-window arithmetic are all computed in
`index.html` from standard published formulae. The planetary elements are the
J2000 set with rates from the JPL Solar System Dynamics group's *Approximate
Positions of the Major Planets*, <https://ssd.jpl.nasa.gov/planets/approx_pos.html>,
which is US Government work and not subject to copyright.

Observatory names and coordinates are matters of public fact, listed for
convenience; no affiliation or endorsement is implied.
