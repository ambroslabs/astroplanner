#!/usr/bin/env bash
# Assemble the deployable site into dist/.
#
# The source tree deliberately makes no external requests: React and the fonts
# are vendored, so a clone runs standalone and offline. Analytics is therefore
# not committed - it is injected here, only when a token is supplied, so the
# repository stays neutral and a fork never reports to someone else's account.
#
#   CF_WEB_ANALYTICS_TOKEN   Cloudflare Web Analytics site tag. Optional;
#                            without it the build is byte-identical to source.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist"

rm -rf "$OUT"; mkdir -p "$OUT"
cp "$ROOT/index.html" "$OUT/index.html"
cp "$ROOT/_worker.js" "$OUT/_worker.js"
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
echo "build: dist/ ready ($(find "$OUT" -type f | wc -l) files)"
