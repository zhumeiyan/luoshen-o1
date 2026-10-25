#!/usr/bin/env bash
# ============================================================
# 洛神 O1 · 一键推送到公开仓库（代码仓库链接）
# 用法：
#   1) 先在 Gitee（或 GitHub）网页上新建一个【空仓库】，名字建议 luoshen-o1
#      ⚠️ 不要勾选 "初始化 README / .gitignore / LICENSE"，必须是空仓库
#   2) 回到这里执行：
#        bash deliver/push_repo.sh gitee  <你的用户名>
#      或
#        bash deliver/push_repo.sh github <你的用户名>
#   3) 弹窗要密码时：
#        Gitee  → 用户名 + 私人令牌(私人令牌在 Gitee 设置里生成)
#        GitHub → 用户名 + Personal Access Token（不能用登录密码）
# ============================================================
set -e
PLAT="${1:-gitee}"
USER="${2:-}"
if [ -z "$USER" ]; then
  echo "用法: bash deliver/push_repo.sh [gitee|github] <你的用户名>"; exit 1
fi
BR=$(git branch --show-current)
if [ "$PLAT" = "gitee" ]; then
  URL="https://gitee.com/${USER}/luoshen-o1.git"
else
  URL="https://github.com/${USER}/luoshen-o1.git"
fi
echo "分支: $BR"
echo "目标: $URL"
git remote remove origin 2>/dev/null || true
git remote add origin "$URL"
git push -u origin "$BR"
echo ""
echo "✅ 推送完成。代码仓库链接（填进提交表）:"
echo "   ${URL%.git}"
