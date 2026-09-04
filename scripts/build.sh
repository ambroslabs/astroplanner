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
OUT="${BUILD_OUT:-$ROOT/dist}"

rm -rf "$OUT"; mkdir -p "$OUT"
cp "$ROOT/index.html" "$OUT/index.html"
if [[ "${BUILD_WORKER:-1}" != "0" ]]; then cp "$ROOT/_worker.js" "$OUT/_worker.js"; fi
cp -r "$ROOT/assets" "$OUT/assets"

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
badge = ('<div style="position:fixed;left:0;top:0;z-index:60;background:#8C2F2F;'
         'color:#fff;font:700 11px/1 Inter,sans-serif;letter-spacing:.14em;'
         'padding:6px 10px;border-bottom-right-radius:3px;pointer-events:none">'
         'BETA</div>\n')
html = open(path, encoding='utf-8').read()
assert html.count('</body>') == 1, 'expected exactly one </body>'
open(path, 'w', encoding='utf-8').write(html.replace('</body>', badge + '</body>'))
BADGE
  echo "build: stamped as beta"
fi
echo "build: $OUT ready ($(find "$OUT" -type f | wc -l) files)"
