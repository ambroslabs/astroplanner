#!/usr/bin/env python3
"""Build the constellation boundary layer: the regions, not the figures.

The chart already draws constellation figures - the stick shapes people
recognise. This is the other thing the word means: the 88 regions the IAU
divided the whole sky into in 1930, which between them account for every
point on the sphere and leave no gaps.

Eugene Delporte drew them along meridians and parallels of B1875, so in that
frame every boundary is either a line of constant right ascension or a line
of constant declination and nothing else. That is worth keeping. Precessing
the vertices to J2000 - which is what most published versions of this data
ship - turns each straight line into a shallow curve, and then the file has
to carry interpolated points to describe the curve: the standard J2000 point
list is 12,948 points where the original is 1,651 vertices.

So this ships the original. The 1,651 vertices are exact - right ascension
lands on a whole second of time and declination on a whole arcminute, every
time, once the source file's five printed decimals are rounded back - and the
page precesses and subdivides them at load, to whatever tolerance it wants.
The reconstruction was checked against the published J2000 point list: the
worst vertex disagrees by 0.15 arcseconds, which is a twentieth of a pixel at
the chart's deepest zoom.

Each polygon is stored whole rather than as a set of edges, because the page
wants two different things out of it. Drawing wants edges, deduplicated -
every interior boundary is shared by two constellations, so 1,651 edges are
really 866. Naming a region wants the polygon, so a ray cast from a point can
count crossings and say which constellation it landed in. Both come out of
the same lines.

Source: VI/49 constbnd.dat at CDS, prepared by Bill J. Gray from Delporte's
boundaries, listing each constellation's vertices in traversal order with the
constellation across each edge.
"""
import gzip, hashlib, math, pathlib, sys, urllib.request

SRC = 'https://cdsarc.cds.unistra.fr/viz-bin/nph-Cat/txt?VI/49/constbnd.dat'
# constbnd.dat spells these its own way; the chart knows them by the codes
# OpenNGC uses, where Serpens is two entries because the sky says so.
RENAME = {'Cra': 'CrA', 'Ser1': 'Se1', 'Ser2': 'Se2'}


def fetch(url, cache):
    p = pathlib.Path(cache)
    if not p.exists():
        print('fetching', url, flush=True)
        p.write_bytes(urllib.request.urlopen(url, timeout=300).read())
    return p.read_text(encoding='utf-8', errors='replace')


def polygons(text):
    """Vertices per constellation, in traversal order. A blank adjacent
       constellation marks the first vertex of a new polygon."""
    rows = []
    for ln in text.split('\n'):
        if not ln.strip() or ln[0] in '#-' or 'RAhr' in ln:
            continue
        try:
            ra = float(ln[0:8])
        except ValueError:
            continue
        rows.append((ra, float(ln[9:18]), ln[19:23].strip(), ln[24:28].strip()))
    blocks, cur = [], None
    for r in rows:
        if r[3] == '':
            if cur:
                blocks.append(cur)
            cur = [r]
        else:
            cur.append(r)
    blocks.append(cur)
    out = []
    for b in blocks:
        pts = [(round(v[0] * 3600), round(v[1] * 60)) for v in b]
        if pts[-1] == pts[0]:
            pts.pop()          # every block closes by repeating its first vertex
        out.append((RENAME.get(b[0][2], b[0][2]), pts))
    return out


def b36(n):
    s, neg = '', abs(n)
    while True:
        s = '0123456789abcdefghijklmnopqrstuvwxyz'[neg % 36] + s
        neg //= 36
        if not neg:
            return ('-' + s) if n < 0 else s


def main():
    out_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    cache = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else '.')
    polys = polygons(fetch(SRC, cache / 'constbnd.dat'))
    print('%d polygons, %d vertices' % (len(polys), sum(len(p[1]) for p in polys)))

    # Exactness, asserted rather than assumed: every step moves in one axis
    # only, which is what lets a vertex cost one number instead of two.
    for name, pts in polys:
        ring = pts + [pts[0]]
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            assert (a[0] == b[0]) != (a[1] == b[1]), (name, a, b)

    lines = []
    for name, pts in polys:
        steps = []
        ring = pts + [pts[0]]
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            if a[1] == b[1]:
                d = (b[0] - a[0] + 43200) % 86400 - 43200      # RA, the short way
                steps.append('a' + b36(d))
            else:
                steps.append('d' + b36(b[1] - a[1]))
        lines.append('%s|%d,%d|%s' % (name, pts[0][0], pts[0][1], ','.join(steps)))

    body = ('# IAU constellation boundaries, Delporte 1930, on the B1875 equinox '
            'he drew them on.\n'
            '# One line per constellation: abbreviation, first vertex as right '
            'ascension in\n'
            '# seconds of time and declination in arcminutes, then one step per '
            'edge - "a" for a\n'
            '# move in right ascension, "d" for a move in declination, base 36 and '
            'signed. The\n'
            '# last step closes the ring. Source: VI/49 constbnd.dat at CDS.\n'
            + '\n'.join(lines) + '\n')
    h = hashlib.sha256(body.encode()).hexdigest()[:12]
    dest = out_dir / ('bounds.%s.txt' % h)
    dest.write_text(body, encoding='utf-8')
    print('wrote %s  %.0f KB raw, %.0f KB gzipped'
          % (dest, len(body) / 1024, len(gzip.compress(body.encode(), 9)) / 1024))


if __name__ == '__main__':
    main()
