#!/bin/bash
# 按需单条读，不整读 —— 脑子不炸
#   bash 读我.sh          列出条目
#   bash 读我.sh 根        读单条
D=/data/workspace/luoshen-o1/外存
[ -z "$1" ] && { ls "$D"/*.md; exit 0; }
cat "$D/$1.md" 2>/dev/null || echo "没有这条"
