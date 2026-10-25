#!/usr/bin/env bash
# evalguard landing page -> GitHub Pages
# Usage:  GITHUB_TOKEN=ghp_xxxx  ./PUSH_PAGES.sh
set -euo pipefail

REPO="${REPO:-evalguard}"
DESC="Static checker for LLM/agent evaluation scripts. 368-failure-mode canon."
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../site/index.html"

: "${GITHUB_TOKEN:?Need GITHUB_TOKEN=ghp_xxxx (scope: repo)}"
[ -f "$SRC" ] || { echo "index.html not found"; exit 1; }

API="https://api.github.com"
H1="Authorization: Bearer $GITHUB_TOKEN"
H2="Accept: application/vnd.github+json"

OWNER=$(curl -s -H "$H1" -H "$H2" "$API/user" | python3 -c 'import sys,json;print(json.load(sys.stdin)["login"])')
echo "owner: $OWNER"

# 1. create repo (ignore "already exists")
curl -s -o /dev/null -w "create repo: %{http_code}\n" \
  -X POST "$API/user/repos" -H "$H1" -H "$H2" \
  -d "{\"name\":\"$REPO\",\"description\":\"$DESC\",\"homepage\":\"https://$OWNER.github.io/$REPO/\",\"private\":false,\"auto_init\":true}"

# 2. push index.html
B64=$(base64 -w0 "$SRC")
curl -s -o /dev/null -w "put index.html: %{http_code}\n" \
  -X PUT "$API/repos/$OWNER/$REPO/contents/index.html" \
  -H "$H1" -H "$H2" \
  -d "{\"message\":\"evalguard landing page\",\"content\":\"$B64\"}"

# 3. enable GitHub Pages (build from root)
curl -s -o /dev/null -w "enable pages: %{http_code}\n" \
  -X POST "$API/repos/$OWNER/$REPO/pages" -H "$H1" -H "$H2" \
  -d '{"source":{"branch":"main","path":"/"}}' || true

echo
echo "done -> https://$OWNER.github.io/$REPO/"
echo "(Pages 首次生效约 1-3 分钟；若第 3 步返回 409 说明已开启，可忽略)"
