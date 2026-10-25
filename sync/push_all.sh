#!/usr/bin/env bash
# push_all.sh — 一键把待同步内容推到 GitHub / Gitee
#
# 为什么需要这个脚本：
#   本沙盒出口被 Gitee 全站 403（IP 策略拒绝），GitHub 写入 401。
#   所以内容在这里全部准备好，由有网的一方执行本脚本即可。
#
# 用法：
#   export GH_TOKEN=ghp_xxxx        # GitHub Personal Access Token (repo 权限)
#   export GITEE_TOKEN=xxxx         # Gitee 私人令牌 (projects 权限)
#   bash push_all.sh
#
# 只推一边：
#   bash push_all.sh github
#   bash push_all.sh gitee

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-all}"

log(){ printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
die(){ printf '\033[31mFAIL\033[0m %s\n' "$*" >&2; exit 1; }

# ---------- 用 REST API 推单个文件（无需本地 git 远端） ----------
put_file(){
  local host="$1" api="$2" token="$3" owner="$4" repo="$5" path="$6" msg="$7"
  local b64 url sha
  b64=$(base64 -w0 "$path")
  url="https://$api/repos/$owner/$repo/contents/$path"

  # 已存在则带 sha（更新），否则新建
  sha=$(curl -sS -H "Authorization: token $token" -H "User-Agent: push_all" \
        "$url" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("sha",""))' 2>/dev/null || echo "")

  if [ -n "$sha" ]; then
    curl -sS -X PUT "$url" \
      -H "Authorization: token $token" -H "User-Agent: push_all" \
      -H "Content-Type: application/json" \
      -d "$(python3 -c "
import json,sys
print(json.dumps({'message':sys.argv[1],'content':sys.argv[2],'sha':sys.argv[3]}))
" "$msg" "$b64" "$sha")" >/dev/null
  else
    curl -sS -X PUT "$url" \
      -H "Authorization: token $token" -H "User-Agent: push_all" \
      -H "Content-Type: application/json" \
      -d "$(python3 -c "
import json,sys
print(json.dumps({'message':sys.argv[1],'content':sys.argv[2]}))
" "$msg" "$b64")" >/dev/null
  fi
  printf '  pushed %s\n' "$path"
}

push_github(){
  log "GitHub"
  [ -n "${GH_TOKEN:-}" ] || die "缺 GH_TOKEN"
  # 两个空仓库补 README（指向 Gitee 真货）
  ( cd "$HERE/gh-console" && put_file github.com api.github.com "$GH_TOKEN" zhumeiyan luoshen-console README.md "docs: 标注本仓库为空镜像，真货在 Gitee" )
  ( cd "$HERE/gh-life"    && put_file github.com api.github.com "$GH_TOKEN" zhumeiyan luoshen-life    README.md "docs: 标注本仓库为空镜像，真货在 Gitee" )
}

push_gitee(){
  log "Gitee"
  [ -n "${GITEE_TOKEN:-}" ] || die "缺 GITEE_TOKEN"
  ( cd "$HERE/gitee-mirror" && \
    find . -type f -not -path './.git/*' | while read -r f; do
      put_file gitee.com gitee.com/api/v5 "$GITEE_TOKEN" zhu-meiyan1 luoshen-ai-o1 "${f#./}" "sync from luoshen-o1"
    done )
}

case "$TARGET" in
  github) push_github ;;
  gitee)  push_gitee  ;;
  all)    push_github; push_gitee ;;
  *)      die "未知目标: $TARGET" ;;
esac

log "完成"
