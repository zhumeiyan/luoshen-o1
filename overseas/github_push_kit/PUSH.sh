#!/usr/bin/env bash
# 在你自己的网络下运行（本沙盒 api.github.com 可达，但没有你的 token）。
# 用法：  GITHUB_TOKEN=ghp_xxx ./PUSH.sh
set -e
: "${GITHUB_TOKEN:?需要 GITHUB_TOKEN}"
REPO=${REPO:-evalguard}
USER=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | python3 -c "import sys,json;print(json.load(sys.stdin)['login'])")
echo "user: $USER"
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
     -d "{\"name\":\"$REPO\",\"description\":\"Static linter for LLM/Agent evaluation scripts. 26 rules traced to a 368-entry empirical failure-mode canon.\",\"license_template\":\"mit\"}" \
     https://api.github.com/user/repos >/dev/null
cd evalguard
git init -q 2>/dev/null || true
git add -A && git -c user.name="$USER" -c user.email="$USER@users.noreply.github.com" commit -qm "evalguard v0.3.0"
git remote remove origin 2>/dev/null || true
git remote add origin "https://$GITHUB_TOKEN@github.com/$USER/$REPO.git"
git branch -M main
git push -u -q origin main
echo "pushed: https://github.com/$USER/$REPO"
