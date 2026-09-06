#!/usr/bin/env python3
"""Build the star layer: only stars a person can name.

Three naming systems reach the chart, and they are not one catalogue:

  proper names   the IAU Catalog of Star Names, the only one of the three
                 anybody actually administers - 452 names, one spelling each
  Bayer          Greek (and a few Latin) letters, Johann Bayer, Uranometria
                 1603; a convention nobody maintains
  Flamsteed      numbers by right ascension within a constellation, assigned
                 in Lalande's 1783 edition of Flamsteed's observations

A star is in this file if it has at least one of them, and out if it has
none. That is the whole selection rule: no magnitude cut, no "brightest N".
Stars carrying nothing but catalogue numbers - HD, HIP, SAO and the rest -
are not named in any sense a chart label can use, so they are dropped, which
is what takes the Bright Star Catalogue's 9,110 down to about a third.

Positions and magnitudes come from the Bright Star Catalogue (VizieR V/50);
proper names are merged in from the IAU-CSN by HR number, and the handful of
IAU-named stars too faint for the BSC are carried in from the IAU-CSN itself,
which has its own coordinates.

Written the way the deep-sky catalogues are: delta-encoded against the value
the reader will reconstruct rather than against the previous input, so the
error cannot accumulate down the file.
"""
import gzip, hashlib, pathlib, sys, urllib.parse, urllib.request

BSC = ('https://vizier.cds.unistra.fr/viz-bin/asu-tsv?' + urllib.parse.urlencode(
    {'-source': 'V/50/catalog', '-out': 'HR,Name,_RAJ2000,_DEJ2000,Vmag',
     '-out.max': 'unlimited', '-c.eq': 'J2000'}))
CSN = 'http://www.pas.rochester.edu/~emamajek/WGSN/IAU-CSN.txt'

# The Bright Star Catalogue writes the Greek letter as a three-letter code.
GREEK = {'Alp': 'α', 'Bet': 'β', 'Gam': 'γ', 'Del': 'δ', 'Eps': 'ε', 'Zet': 'ζ',
         'Eta': 'η', 'The': 'θ', 'Iot': 'ι', 'Kap': 'κ', 'Lam': 'λ', 'Mu': 'μ',
         'Nu': 'ν', 'Xi': 'ξ', 'Omi': 'ο', 'Pi': 'π', 'Rho': 'ρ', 'Sig': 'σ',
         'Tau': 'τ', 'Ups': 'υ', 'Phi': 'φ', 'Chi': 'χ', 'Psi': 'ψ', 'Ome': 'ω'}


def fetch(url, cache):
    p = pathlib.Path(cache)
    if not p.exists():
        print('fetching', url.split('?')[0], flush=True)
        p.write_bytes(urllib.request.urlopen(url, timeout=300).read())
    return p.read_text(encoding='utf-8', errors='replace')


def bsc_rows(text):
    """VizieR TSV: comments, a header, a row of dashes, then the data."""
    rows, hdr, sep = [], None, False
    for ln in text.split('\n'):
        if ln.startswith('#'):
            continue
        ln = ln.rstrip('\r')
        if hdr is None:
            if ln.strip():
                hdr = ln.split('\t')
            continue
        if not sep:
            if ln and set(ln.replace('\t', '')) <= set('-'):
                sep = True
            continue
        if ln.strip():
            rows.append(dict(zip(hdr, ln.split('\t'))))
    return rows


def csn_rows(text):
    """Fixed width, and the columns are where the header says they are."""
    out = []
    for ln in text.split('\n'):
        if not ln.strip() or ln.startswith('#'):
            continue
        f = lambda a, b: ln[a:b].strip() if len(ln) > a else ''
        name, hr, con = f(0, 17), f(36, 48), f(61, 64)
        if not name or name.startswith('$'):
            continue          # the file's own footnote line
        out.append({'name': name, 'desig': hr, 'con': con,
                    'mag': f(81, 86), 'ra': f(104, 114), 'dec': f(115, 125)})
    return out


def parse_name(nm):
    """The BSC name field is ten fixed columns: Flamsteed, Bayer, a
       superscript for the members of a lettered series, constellation."""
    nm = (nm or '').ljust(10)
    flam, letter, sup, con = nm[0:3].strip(), nm[3:6].strip(), nm[6:7].strip(), nm[7:10].strip()
    bayer = ''
    if letter in GREEK:
        bayer = GREEK[letter] + (sup if sup else '')
    elif letter and len(letter) <= 2 and letter.isalpha():
        bayer = letter          # Bayer's Latin letters, once the Greek ran out
    return flam, bayer, con


def b36(n):
    s, neg = '', n < 0
    n = abs(n)
    while True:
        s = '0123456789abcdefghijklmnopqrstuvwxyz'[n % 36] + s
        n //= 36
        if not n:
            return ('-' + s) if neg else s


def main():
    out_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    cache = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else '.')
    bsc = bsc_rows(fetch(BSC, cache / 'bsc.tsv'))
    csn = csn_rows(fetch(CSN, cache / 'csn.txt'))
    print(f'{len(bsc)} Bright Star Catalogue rows, {len(csn)} IAU names', flush=True)

    proper = {}
    for c in csn:
        if c['desig'].startswith('HR '):
            proper[c['desig'][3:].strip()] = c['name']

    stars, seen_hr = [], set()
    for r in bsc:
        try:
            ra, dec, mag = float(r['_RAJ2000']), float(r['_DEJ2000']), float(r['Vmag'])
        except (ValueError, KeyError):
            continue            # novae and clusters ride along in the BSC with no magnitude
        hr = r.get('HR', '').strip()
        flam, bayer, con = parse_name(r.get('Name', ''))
        nm = proper.get(hr, '')
        if not (nm or bayer or flam):
            continue            # numbers only: nothing a label could say
        seen_hr.add(hr)
        stars.append((ra, dec, mag, con, bayer, flam, nm))

    # IAU-named stars too faint for the Bright Star Catalogue, from the IAU's
    # own coordinates. Small - a few dozen - but they are named stars, and the
    # rule is that a named star is in.
    extra = 0
    for c in csn:
        if c['desig'].startswith('HR ') and c['desig'][3:].strip() in seen_hr:
            continue
        try:
            ra, dec = float(c['ra']), float(c['dec'])
            mag = float(c['mag'])
        except ValueError:
            continue
        stars.append((ra, dec, mag, c['con'], '', '', c['name']))
        extra += 1

    stars.sort(key=lambda s: (round(s[1]), s[0]))
    lines, pra, pdec = [], 0, 0
    for ra, dec, mag, con, bayer, flam, nm in stars:
        ira, idec = round(ra * 3600), round(dec * 3600)      # arcseconds
        lines.append(','.join([b36(ira - pra), b36(idec - pdec), b36(round(mag * 100)),
                               con, bayer, flam, nm]))
        pra, pdec = ira, idec                                # against the reconstructed value

    body = ('# named stars: proper name, Bayer, Flamsteed. '
            'dRA,dDec (arcsec, base36 deltas), mag*100, constellation, Bayer, Flamsteed, proper name\n'
            + '\n'.join(lines) + '\n')
    h = hashlib.sha256(body.encode()).hexdigest()[:12]
    dest = out_dir / ('stars.%s.txt' % h)
    dest.write_text(body, encoding='utf-8')
    gz = len(gzip.compress(body.encode(), 9))
    named = sum(1 for s in stars if s[6])
    print(f'{len(stars)} stars  ({named} with a proper name, '
          f'{sum(1 for s in stars if s[4])} Bayer, {sum(1 for s in stars if s[5])} Flamsteed, '
          f'{extra} carried from the IAU list alone)')
    print(f'wrote {dest}  {len(body)/1024:.0f} KB raw, {gz/1024:.0f} KB gzipped')


if __name__ == '__main__':
    main()
