#!/usr/bin/env python3
"""Turn the raw catalogue sources into the files the app fetches.

Each catalogue becomes one self-contained, content-hashed text file under
assets/catalogs/. Self-contained matters: Messier and Caldwell are selections
out of NGC/IC, but giving them their own copies of the 219 rows they need costs
about a kilobyte and means enabling Messier never has to pull the 74 KB NGC file
down behind it.

The encoding exists because the positions are the payload - dropping every
other field only saves a fifth, while sorting by catalogue number, storing the
id as a gap from the previous row and delta-coding the coordinates saves a
third and keeps everything. Fields per row:

    gap,dRA,dDec,type,mag,maj,min,pa,name,desig

gap    number of skipped ids before this one, blank when consecutive
dRA    RA in hours, as a delta from the previous row, 3dp
dDec   Dec in degrees, as a delta from the previous row, 2dp
type   OpenNGC type code, or the catalogue's own kind
mag    visual (else blue) magnitude, 1dp
maj    major axis in arcmin, min minor axis, pa position angle in degrees
name   common name, where the object has one
desig  cross-designation, for the catalogues that are selections

Sources: OpenNGC (CC-BY-SA-4.0) for NGC/IC and the Messier numbers; VizieR for
Sharpless VII/20, Barnard VII/220A, van den Bergh VII/21, Lynds dark nebulae
VII/7A and Arp VII/192; Wikipedia for the Caldwell and Herschel 400 lists.

VizieR hands back B1950 coordinates unless you ask otherwise - Sh2-1 sits 0.76
degrees from its J2000 position - so the fetches below pass -c.eq=J2000.
"""
import csv, gzip, hashlib, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, 'assets', 'catalogs')
SRC  = os.environ.get('CATALOG_SRC', os.path.join(ROOT, 'build', 'catalog-src'))

def fetch(url, path, desc):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sys.stderr.write('fetching %s\n' % desc)
    req = urllib.request.Request(url, headers={'User-Agent': 'astroplanner-catalog-build/1.0'})
    with urllib.request.urlopen(req, timeout=180) as r, open(path, 'wb') as f:
        f.write(r.read())
    return path

def vizier(source, cols, path, desc):
    q = urllib.parse.urlencode({'-source': source, '-out': cols,
                                '-out.max': 'unlimited', '-c.eq': 'J2000'})
    return fetch('https://vizier.cds.unistra.fr/viz-bin/asu-tsv?' + q, path, desc)

def tsv(path):
    """VizieR TSV: comment lines, a header, a row of dashes, then the data."""
    rows, hdr, sep = [], None, False
    with open(path, encoding='utf-8', errors='replace') as f:
        for ln in f:
            ln = ln.rstrip('\n')
            if ln.startswith('#') or not ln.strip():
                continue
            if set(ln.replace('\t', '')) <= set('-'):
                sep = True; continue
            if hdr is None:
                hdr = ln.split('\t'); continue
            if sep:
                rows.append(dict(zip(hdr, ln.split('\t'))))
    return rows

def hms(s):
    h, m, sec = s.split(':'); return int(h) + int(m) / 60 + float(sec) / 3600
def dms(s):
    sg = -1 if s.strip()[0] == '-' else 1
    d, m, sec = s.strip().lstrip('+-').split(':')
    return sg * (int(d) + int(m) / 60 + float(sec) / 3600)
def f1(v, fmt='%.1f'):
    try: return fmt % float(v)
    except (TypeError, ValueError): return ''

def encode(objs):
    """objs: (id, ra_hours, dec_deg, type, mag, maj, min, pa, name, desig).

    Each delta is measured from the position the decoder will actually have
    reconstructed, not from the true previous one. Measured from the true value,
    every row's rounding is inherited by the next and the error walks: M31, 30
    rows in, landed 28 arcsec out, and NGC 7000, 7000 rows in, 1524 arcsec - a
    quarter of a degree, and silently, since nothing about the file looks wrong.
    Feeding back the rounded value holds every row to half a quantum, 1.8
    arcsec, no matter how far into the file it sits.
    """
    objs = sorted(objs, key=lambda o: o[0])
    out, pn, ra_acc, dec_acc = [], 0, 0.0, 0.0
    for n, ra, dec, ty, mag, maj, mnr, pa, name, desig in objs:
        gap = n - pn - 1
        dra = round(ra - ra_acc, 3)
        ddec = round(dec - dec_acc, 3)
        ra_acc += dra
        dec_acc += ddec
        out.append(','.join([
            str(gap) if gap else '', '%.3f' % dra, '%.3f' % ddec,
            ty or '', mag or '', maj or '', mnr or '', pa or '',
            (name or '').replace(',', ' '), (desig or '').replace(',', ' ')]))
        pn = n
    return '\n'.join(out)

def write(name, objs):
    body = encode(objs)
    digest = hashlib.sha256(body.encode()).hexdigest()[:12]
    for old in os.listdir(OUT):
        if old.startswith(name + '.') and old.endswith('.txt'):
            os.remove(os.path.join(OUT, old))
    fn = '%s.%s.txt' % (name, digest)
    with open(os.path.join(OUT, fn), 'w', encoding='utf-8') as f:
        f.write(body)
    gz = len(gzip.compress(body.encode()))
    print('  %-10s %5d objects  %7.1f KB raw  %6.1f KB gz  %s' %
          (name, len(objs), len(body) / 1024, gz / 1024, fn))
    return fn, len(objs)

# ---------------------------------------------------------------- OpenNGC ----
# Types that are not objects you would point a telescope at: duplicate entries,
# things later shown not to exist, and plain stars logged by mistake.
SKIP = {'Dup', 'NonEx', '*', '**', '*Ass', 'Other', 'Nova'}

def open_ngc():
    path = fetch('https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/'
                 'database_files/NGC.csv', os.path.join(SRC, 'NGC.csv'), 'OpenNGC')
    rows = list(csv.DictReader(open(path, encoding='utf-8'), delimiter=';'))
    by_desig = {}
    for r in rows:
        if r['RA'] and r['Dec']:
            by_desig[r['Name']] = r
    return rows, by_desig

def mag_of(r):
    for k in ('V-Mag', 'B-Mag'):
        if r.get(k):
            try: return '%.1f' % float(r[k])
            except ValueError: pass
    return ''

def row_of(r, n, desig=''):
    return (n, hms(r['RA']), dms(r['Dec']), r['Type'], mag_of(r),
            f1(r['MajAx']), f1(r['MinAx']), f1(r['PosAng'], '%.0f'),
            (r['Common names'] or '').split(',')[0].strip(), desig)

def ngc_ic(rows, prefix):
    out = []
    for r in rows:
        if not r['Name'].startswith(prefix) or r['Type'] in SKIP: continue
        if not r['RA'] or not r['Dec']: continue
        m = re.match(r'^%s(\d+)' % prefix, r['Name'])
        # Skip the lettered sub-components - NGC0650A, IC2431 NED02 and 733 more.
        # They are pieces of an object rather than objects you would go and
        # image, and not one of them carries a common name.
        if not m or not re.fullmatch(r'%s\d+' % prefix, r['Name']): continue
        out.append(row_of(r, int(m.group(1))))
    return out

# Messier objects OpenNGC cannot supply: M24 is a star cloud, M40 a double star,
# M45 the Pleiades - none of them carry an NGC number of their own.
EXTRA_M = {
    24: (18.2833, -18.50, 'Cl+N', '4.6', '90.0', '', '', 'Sagittarius Star Cloud', 'IC 4715'),
    40: (12.3706,  58.08, '**',   '9.6', '0.8',  '', '', 'Winnecke 4',             'WNC 4'),
    45: ( 3.7900,  24.11, 'OCl',  '1.6', '110.0','', '', 'Pleiades',               'Mel 22'),
}
# M102 is the catalogue's own open question - either a second look at M101 or
# NGC 5866. OpenNGC declines to assign it, so take the usual modern reading and
# say which object it is rather than leave a hole at 102.
M102 = 'NGC5866'

def messier_names():
    """OpenNGC names only 30 of the 110, and a search box is only as good as
    the names in it - nobody looks up 'NGC 6720', they look up 'Ring Nebula'."""
    src = open(wiki('Messier_object', os.path.join(SRC, 'messier.wiki')),
               encoding='utf-8').read()
    names = {}
    for block in re.split(r'\n\|-', src):
        # Rows open with  ! scope="row" | [[Crab Nebula|M1]]  and the columns
        # then run NGC/IC number, common name, image, type... Take the name by
        # position: scanning for the first cell that reads like prose picks up
        # the constellation column for the objects that have no name, and
        # "M2 Aquarius" is exactly the kind of wrong a search box repeats back.
        m = re.search(r'!\s*scope="row"\s*\|\s*\[\[[^\]]*\|M(\d{1,3})\]\]', block)
        if not m: continue
        n = int(m.group(1))
        if n in names: continue
        cells = re.findall(r'^\|\s*(.*)$', block, re.M)
        if len(cells) > 1:
            nm = plausible_name(unlink(cells[1]))
            if nm: names[n] = nm
    return names

def messier(rows):
    out, names = [], messier_names()
    for r in rows:
        if not r['M']: continue
        try: n = int(r['M'])
        except ValueError: continue
        row = list(row_of(r, n, r['Name']))
        if not row[8] and names.get(n): row[8] = names[n]
        out.append(tuple(row))
    have = {o[0] for o in out}
    for n, v in EXTRA_M.items():
        if n not in have:
            out.append((n,) + v)
    if 102 not in have:
        r = {x['Name']: x for x in rows}.get(M102)
        if r: out.append(row_of(r, 102, 'NGC 5866'))
    return out

# ---------------------------------------------------------- wiki selections ---
def wiki(page, path):
    return fetch('https://en.wikipedia.org/w/index.php?title=%s&action=raw'
                 % urllib.parse.quote(page), path, page)

def unlink(t):
    # Templates first: {{sdash}} renders as an em-dash and means "this one has
    # no common name", so it has to become empty rather than survive as a name.
    t = re.sub(r'\{\{[^{}]*\}\}', '', t)
    t = re.sub(r'<ref[^>]*>.*?</ref>|<ref[^>]*/>', '', t, flags=re.S)
    t = re.sub(r'<[^>]+>', '', t)
    t = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', t)
    t = re.sub(r'\[\[([^\]]*)\]\]', r'\1', t)
    t = re.sub(r"''|&nbsp;|style=.*", '', t)
    return t.strip()

def plausible_name(c):
    """A common name, or nothing. Wiki cells also carry image markup, footnote
    refs and bare designations, and any of those silently become a bad search
    result, so this only accepts something that reads like prose."""
    c = re.sub(r'\(.*?\)', '', c).strip(' \'"\u2013\u2014-')
    if not c or len(c) > 40: return ''
    if re.search(r'[|=<>\[\]{}]|File:|frameless|thumb|upright|\dpx\b', c): return ''
    if re.match(r'(?i)(NGC|IC|M|C)\s*\d+$', c): return ''
    if not re.match(r"^[A-Za-z][A-Za-z0-9 '\u2019.\u00e9\u00fc\u03c7&/-]*$", c): return ''
    if not re.search(r'[A-Za-z]{3}', c): return ''
    return c

# The three Caldwell entries with no NGC or IC number of their own.
EXTRA_C = {
    9:  (22.9567, 62.5486, 'Neb',  '7.7', '50.0',  '', '', 'Cave Nebula',     'Sh2-155'),
    41: ( 4.4500, 15.8700, 'OCl',  '0.5', '330.0', '', '', 'Hyades',          'Mel 25'),
    99: (12.8833,-63.0000, 'DrkN', '',    '420.0', '', '', 'Coalsack Nebula', 'Cr 264'),
}

def caldwell(by_desig):
    src = open(wiki('Caldwell_catalogue', os.path.join(SRC, 'caldwell.wiki')),
               encoding='utf-8').read()
    src = src[src.index('== Caldwell objects'):]
    out, missing = [], []
    for block in re.split(r'\n\|-', src):
        m = re.search(r'\|\s*(?:\{\{hs\|\d+\}\})?C(\d{1,3})\s*\n', block)
        if not m: continue
        n = int(m.group(1))
        cells = [unlink(c) for c in re.findall(r'^\|\s*(.*)$', block, re.M)]
        desig = cells[1] if len(cells) > 1 else ''
        name  = cells[2] if len(cells) > 2 else ''
        # "NGC 869 & NGC 884" - take the first, it is where the label goes.
        d = re.match(r'(NGC|IC)\s*(\d+)', desig)
        if d:
            key = '%s%04d' % (d.group(1), int(d.group(2)))
            r = by_desig.get(key)
            if r:
                row = list(row_of(r, n, '%s %s' % (d.group(1), int(d.group(2)))))
                nm = plausible_name(name)
                if nm: row[8] = nm
                out.append(tuple(row)); continue
        missing.append((n, desig))
    for n, v in EXTRA_C.items():
        if n not in {o[0] for o in out}: out.append((n,) + v)
    unresolved = [x for x in missing if x[0] not in EXTRA_C]
    if unresolved:
        sys.stderr.write('  caldwell unresolved: %s\n' % unresolved)
    return out

def herschel400(by_desig):
    src = open(wiki('Herschel_400_Catalogue', os.path.join(SRC, 'h400.wiki')),
               encoding='utf-8').read()
    src = src[src.index('=='):]
    seen, out = set(), []
    for block in re.split(r'\n\|-', src):
        m = re.search(r'\[\[(?:[^\]|]*\|)?NGC\s*(\d{1,4})', block)
        if not m: continue
        n = int(m.group(1))
        if n in seen: continue
        r = by_desig.get('NGC%04d' % n)
        if not r: continue
        seen.add(n)
        out.append(row_of(r, n, 'NGC %d' % n))
    return out

# ------------------------------------------------------------ VizieR lists ---
def vz_rows(rows, idcol, kind, diam=None, radius=None, area=None, magcol=None):
    """One row per id; the first entry wins where a catalogue repeats an id."""
    seen = {}
    for r in rows:
        try:
            n = int(str(r.get(idcol, '')).strip())
            ra = float(r['_RAJ2000']) / 15.0
            dec = float(r['_DEJ2000'])
        except (TypeError, ValueError, KeyError):
            continue
        if n in seen: continue
        maj = ''
        if diam: maj = f1(r.get(diam))
        elif radius:
            try: maj = '%.1f' % (2 * float(r[radius]))
            except (TypeError, ValueError, KeyError): maj = ''
        elif area:
            # Lynds gives square degrees; show the circle of the same area.
            try: maj = '%.1f' % (2 * (float(r[area]) / 3.14159265) ** 0.5 * 60)
            except (TypeError, ValueError, KeyError): maj = ''
        seen[n] = (n, ra, dec, kind, f1(r.get(magcol)) if magcol else '',
                   maj, '', '', '', '')
    return list(seen.values())

# SIMBAD carries the popular names the source lists do not: the Barnard
# catalogue has no name column at all, so without this the Horsehead is
# unfindable by the only word anyone calls it. Matched on the plain numbered
# designations - the lettered sub-clouds (Barnard 18F) are not rows we carry.
SIMBAD_TAP = 'https://simbad.cds.unistra.fr/simbad/sim-tap/sync'
SIMBAD_PREFIX = {'BARNARD': 'barnard', 'VDB': 'vdb', 'LDN': 'lynds', 'APG': 'arp'}

def simbad_names():
    adql = ("SELECT i2.id AS desig, i1.id AS cname "
            "FROM ident AS i1 JOIN ident AS i2 ON i1.oidref = i2.oidref "
            "WHERE i1.id LIKE 'NAME %' AND (i2.id LIKE 'Barnard %' OR i2.id LIKE 'VDB %' "
            "OR i2.id LIKE 'LDN %' OR i2.id LIKE 'APG %')")
    q = urllib.parse.urlencode({'request': 'doQuery', 'lang': 'ADQL',
                                'format': 'csv', 'maxrec': '20000', 'query': adql})
    path = fetch(SIMBAD_TAP + '?' + q, os.path.join(SRC, 'simbad-names.csv'), 'SIMBAD names')
    out = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        m = re.match(r'([A-Za-z]+)\s+(\d+)$', (r.get('desig') or '').strip())
        if not m: continue
        cat = SIMBAD_PREFIX.get(m.group(1).upper())
        nm = plausible_name((r.get('cname') or '').replace('NAME ', '', 1))
        if not cat or not nm: continue
        key = (cat, int(m.group(2)))
        # Several aliases per object; keep the first, they arrive best-known first.
        out.setdefault(key, nm)
    return out

def apply_names(rows, cat, names):
    out = []
    for o in rows:
        o = list(o)
        if not o[8]:
            o[8] = names.get((cat, o[0]), '')
        out.append(tuple(o))
    return out

def main():
    os.makedirs(OUT, exist_ok=True)
    rows, by_desig = open_ngc()
    sn = simbad_names()
    print('building catalogues into assets/catalogs/')
    manifest = {}
    manifest['messier']   = write('messier',   messier(rows))
    manifest['caldwell']  = write('caldwell',  caldwell(by_desig))
    manifest['herschel']  = write('herschel',  herschel400(by_desig))
    manifest['ngc']       = write('ngc',       ngc_ic(rows, 'NGC'))
    manifest['ic']        = write('ic',        ngc_ic(rows, 'IC'))
    manifest['sharpless'] = write('sharpless', apply_names(vz_rows(
        tsv(vizier('VII/20/catalog', 'Sh2,_RAJ2000,_DEJ2000,Diam',
                   os.path.join(SRC, 'sh2.tsv'), 'Sharpless')), 'Sh2', 'HII', diam='Diam'), 'sharpless', sn))
    manifest['barnard']   = write('barnard',   apply_names(vz_rows(
        tsv(vizier('VII/220A/barnard', 'Barn,_RAJ2000,_DEJ2000,Diam',
                   os.path.join(SRC, 'barnard.tsv'), 'Barnard')), 'Barn', 'DrkN', diam='Diam'), 'barnard', sn))
    manifest['vdb']       = write('vdb',       apply_names(vz_rows(
        tsv(vizier('VII/21/catalog', 'VdB,_RAJ2000,_DEJ2000,BRadMax,Vmag',
                   os.path.join(SRC, 'vdb.tsv'), 'van den Bergh')), 'VdB', 'RfN',
        radius='BRadMax', magcol='Vmag'), 'vdb', sn))
    manifest['lynds']     = write('lynds',     apply_names(vz_rows(
        tsv(vizier('VII/7A/ldn', 'LDN,_RAJ2000,_DEJ2000,Area',
                   os.path.join(SRC, 'ldn.tsv'), 'Lynds dark nebulae')), 'LDN', 'DrkN', area='Area'), 'lynds', sn))
    manifest['arp']       = write('arp',       apply_names(vz_rows(
        tsv(vizier('VII/192/arplist', 'Arp,_RAJ2000,_DEJ2000',
                   os.path.join(SRC, 'arp.tsv'), 'Arp')), 'Arp', 'G'), 'arp', sn))
    print('\npaste into CATALOGS in index.html:')
    for k, (fn, n) in manifest.items():
        print("    %-10s file: '%s', n: %d" % (k + ':', fn, n))

if __name__ == '__main__':
    main()
