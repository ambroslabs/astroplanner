#!/usr/bin/env bash
# Assemble the deployable site into dist/.
#
# The source tree deliberately makes no external requests: React and the fonts
# are vendored, so a clone runs standalone and offline. Analytics is therefore
# not committed - it is injected here, only when a token is supplied, so the
# repository stays neutral and a fork never reports to someone else's account.
#
#   CF_WEB_ANALYTICS_TOKEN   Cloudflare Web Analytics *site token* - the value
#                            inside data-cf-beacon in the snippet the dashboard
#                            shows you, NOT the site tag. They are two different
#                            fields on the same site record and the tag is
#                            silently rejected by the beacon endpoint.
#                            Optional; without it the build is byte-identical
#                            to source. Leave it unset when the zone already has
#                            automatic installation enabled - the edge injects
#                            its own beacon and a second one breaks both.
#   BUILD_SRC                Tree to build from. Defaults to this repository,
#                            and is pointed elsewhere to build /beta out of a
#                            second checkout.
#   BUILD_OUT                Where to write it. Defaults to dist/.
#   BUILD_BETA               1 to stamp the page as the beta copy. Two
#                            identical deployments are worse than one: the
#                            point is to try something and look at it, which
#                            needs the page to say which one you are looking
#                            at.
#   BUILD_WORKER             0 to leave _worker.js out. Pages only runs the one
#                            at the root of the deployment, so a nested copy
#                            would be a confusing dead file.
set -euo pipefail
ROOT="${BUILD_SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export ROOT
OUT="${BUILD_OUT:-$ROOT/dist}"

rm -rf "$OUT"; mkdir -p "$OUT"
cp "$ROOT/index.html" "$OUT/index.html"
if [[ "${BUILD_WORKER:-1}" != "0" ]]; then cp "$ROOT/_worker.js" "$OUT/_worker.js"; fi
cp -r "$ROOT/assets" "$OUT/assets"
# The attribution travels with the deployment, not only with the repository:
# ODbL and CC BY-SA both make it a condition of use, and the page links to it.
# Served as .txt so a browser shows it rather than offering to download it.
cp "$ROOT/ATTRIBUTION.md" "$OUT/attribution.txt"
cp "$ROOT/LICENSE" "$OUT/license.txt"
cp -r "$ROOT/licenses" "$OUT/licenses"

# The offline copy. The worker and the manifest only go out with the root
# deployment: /beta reads its catalogues from /assets/, which a worker
# registered under /beta/ cannot intercept, so it would install something that
# looked offline-capable and had no data in it.
if [[ "${BUILD_BETA:-0}" != "1" ]]; then
  cp "$ROOT/manifest.webmanifest" "$OUT/manifest.webmanifest"
  # The precache list is written from what is actually in dist/ rather than
  # kept by hand: catalogue filenames carry a hash of their contents, so a
  # hand-written list would go on asking for the file that was there last time.
  python3 - "$OUT" <<'SW'
import hashlib, os, sys
out = sys.argv[1]
files = ['/', '/manifest.webmanifest']
for base, _, names in os.walk(os.path.join(out, 'assets')):
    for n in sorted(names):
        rel = os.path.relpath(os.path.join(base, n), out).replace(os.sep, '/')
        # The social card is for other people's link previews, not for us.
        if rel == 'assets/social-card.png':
            continue
        files.append('/' + rel)
files.sort()
sw = open(os.path.join(os.environ['ROOT'], 'sw.js'), encoding='utf-8').read()
# The stamp is the digest of everything the worker will cache, so a deployment
# that changes nothing keeps its cache and one that changes anything replaces it.
h = hashlib.sha256()
for f in files:
    h.update(f.encode())
    path = os.path.join(out, f.lstrip('/')) if f != '/' else os.path.join(out, 'index.html')
    with open(path, 'rb') as fh:
        h.update(hashlib.sha256(fh.read()).digest())
sw = sw.replace('BUILD_STAMP', h.hexdigest()[:12])
sw = sw.replace('/*BUILD_ASSETS*/', ',\n  '.join("'%s'" % f for f in files))
open(os.path.join(out, 'sw.js'), 'w', encoding='utf-8').write(sw)
print('build: service worker caches %d files' % len(files))
SW
fi

if [[ -n "${CF_WEB_ANALYTICS_TOKEN:-}" ]]; then
  python3 - "$OUT/index.html" "$CF_WEB_ANALYTICS_TOKEN" <<'PY'
import sys
path, token = sys.argv[1], sys.argv[2]
html = open(path, encoding='utf-8').read()
tag = ('<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" '
       'data-cf-beacon=\'{"token": "%s"}\'></script>\n' % token)
assert html.count('</body>') == 1, 'expected exactly one </body>'
open(path, 'w', encoding='utf-8').write(html.replace('</body>', tag + '</body>'))
PY
  echo "build: analytics beacon injected"
else
  echo "build: no CF_WEB_ANALYTICS_TOKEN, analytics omitted"
fi
if [[ "${BUILD_BETA:-0}" == "1" ]]; then
  python3 - "$OUT/index.html" <<'BADGE'
import sys
path = sys.argv[1]
badge = ('<div style="position:fixed;left:0;bottom:0;z-index:60;background:#8C2F2F;'
         'color:#fff;font:700 11px/1 Inter,sans-serif;letter-spacing:.14em;'
         'padding:6px 10px;border-top-right-radius:3px;pointer-events:none">'
         'BETA</div>\n')
html = open(path, encoding='utf-8').read()
assert html.count('</body>') == 1, 'expected exactly one </body>'
open(path, 'w', encoding='utf-8').write(html.replace('</body>', badge + '</body>'))
BADGE
  # Point the beta copy at the root's catalogue directory. The file names
  # carry a hash of their contents, so the two copies share one URL and one
  # cached download wherever the data is the same, and get separate files
  # automatically wherever it differs.
  python3 - "$OUT/index.html" <<'BASE'
import sys
path = sys.argv[1]
old = "CATALOG_BASE = 'assets/catalogs/';"
new = "CATALOG_BASE = '/assets/catalogs/';"
html = open(path, encoding='utf-8').read()
assert html.count(old) == 1, 'expected exactly one CATALOG_BASE'
open(path, 'w', encoding='utf-8').write(html.replace(old, new))
BASE
  # The attribution is deployed with each copy, so the beta page must link to
  # its own rather than to the root's - which carries main's data, and does not
  # exist at all until this reaches main.
  python3 - "$OUT/index.html" <<'ATTR'
import sys
path = sys.argv[1]
html = open(path, encoding='utf-8').read()
for old, new in [('href="/attribution.txt"', 'href="/beta/attribution.txt"'),
                 ('href="/license.txt"', 'href="/beta/license.txt"')]:
    assert html.count(old) == 1, 'expected exactly one ' + old
    html = html.replace(old, new)
# The manifest belongs to the root deployment and its start_url is the root, so
# offering to install from here would install the other site.
tag = '<link rel="manifest" href="/manifest.webmanifest">\n'
assert html.count(tag) == 1, 'expected exactly one manifest link'
html = html.replace(tag, '')
open(path, 'w', encoding='utf-8').write(html)
ATTR
  echo "build: stamped as beta"
fi
echo "build: $OUT ready ($(find "$OUT" -type f | wc -l) files)"
