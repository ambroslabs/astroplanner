#!/usr/bin/env python3
"""Rasterise the IANA timezone boundaries into a lookup the page can carry.

The page needs one thing from a latitude and longitude: the name of the zone,
after which the browser's own tzdata does the rest - offsets, DST, everything.
So this stores names on a grid rather than polygons, which turns a 24MB
boundary set into a file the size of a small catalogue.

Land only. Every cell the polygons do not cover is ocean, and gets the nautical
zone for its longitude as Etc/GMT+n - a real IANA name the browser already
knows - so every coordinate on Earth resolves to something.

Rows run south to north, each row run-length encoded as (length, zone index).
"""
import json, sys, zipfile, hashlib, pathlib
import numpy as np
import shapely
from shapely.geometry import shape

STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
SRC = sys.argv[1]
NX, NY = int(round(360 / STEP)), int(round(180 / STEP))

print(f"grid {NX} x {NY} at {STEP} deg", flush=True)
with zipfile.ZipFile(SRC) as z:
    name = [n for n in z.namelist() if n.endswith(".json") or n.endswith(".geojson")][0]
    print("reading", name, flush=True)
    gj = json.loads(z.read(name))

feats = gj["features"]
print(f"{len(feats)} zones", flush=True)

# cell centres
xs = -180 + (np.arange(NX) + 0.5) * STEP
ys = -90 + (np.arange(NY) + 0.5) * STEP

names = []
grid = np.full((NY, NX), -1, dtype=np.int16)
for fi, f in enumerate(feats):
    tzid = f["properties"].get("tzid") or f["properties"].get("tz_name1st")
    idx = len(names); names.append(tzid)
    geom = shape(f["geometry"])
    x0, y0, x1, y1 = geom.bounds
    i0, i1 = max(0, int((x0 + 180) / STEP) - 1), min(NX, int((x1 + 180) / STEP) + 2)
    j0, j1 = max(0, int((y0 + 90) / STEP) - 1), min(NY, int((y1 + 90) / STEP) + 2)
    if i1 <= i0 or j1 <= j0: continue
    gx, gy = np.meshgrid(xs[i0:i1], ys[j0:j1])
    prepared = shapely.prepare(geom) or geom
    hit = shapely.contains_xy(geom, gx.ravel(), gy.ravel()).reshape(gy.shape)
    block = grid[j0:j1, i0:i1]
    block[hit & (block < 0)] = idx
    grid[j0:j1, i0:i1] = block
    if fi % 25 == 0:
        print(f"  {fi}/{len(feats)}  {tzid}", flush=True)

# ocean: nautical zones from longitude, as names the browser already knows
filled = int((grid >= 0).sum())
print(f"land cells {filled} of {NY*NX} ({100*filled/(NY*NX):.1f}%)", flush=True)
naut = {}
for i in range(NX):
    off = int(round(xs[i] / 15.0))
    off = max(-12, min(12, off))
    nm = "UTC" if off == 0 else ("Etc/GMT%+d" % -off)
    if nm not in naut:
        naut[nm] = len(names); names.append(nm)
    col = grid[:, i]
    col[col < 0] = naut[nm]
    grid[:, i] = col

# run-length encode each row
def b36(n):
    s = ""
    while True:
        s = "0123456789abcdefghijklmnopqrstuvwxyz"[n % 36] + s
        n //= 36
        if not n: return s

rows = []
for j in range(NY):
    row = grid[j]
    cuts = np.flatnonzero(np.diff(row)) + 1
    starts = np.concatenate(([0], cuts))
    lens = np.diff(np.concatenate((starts, [NX])))
    rows.append(",".join(b36(int(l)) + ":" + b36(int(row[s])) for s, l in zip(starts, lens)))

out = ["# lat/lon -> IANA time zone, %g deg grid, rows south to north" % STEP,
       "S %g" % STEP, "N " + "|".join(names)] + rows
text = "\n".join(out) + "\n"
h = hashlib.sha256(text.encode()).hexdigest()[:12]
dest = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else ".") / ("timezones.%s.txt" % h)
dest.write_text(text)
import gzip
gz = len(gzip.compress(text.encode(), 9))
print(f"wrote {dest}  {len(text)/1024:.0f} KB raw, {gz/1024:.0f} KB gzipped, "
      f"{sum(len(r.split(',')) for r in rows)} runs, {len(names)} zones", flush=True)
