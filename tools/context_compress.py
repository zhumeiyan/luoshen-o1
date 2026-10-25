#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context_compress —— 上下文分层与压缩
====================================
对标补位：3 记忆/上下文管理（压缩与裁剪）

对标依据（全球顶级智能体能力清单.md 第3章）：
  Claude Code 把记忆拆成 7 种机制，各自定义「何时加载 / 压缩后是否保留 / 代价多大」；
  Cursor 靠裁剪系统提示(66%)、工具动态加载(内置工具静态上下文降60%)、
  改善缓存复用(冷未命中降20%) 三招降本且质量不降。

本模块实现那张"压缩命运表"的最小可运行版：

  层           何时加载        压缩后命运            代价
  ─────────────────────────────────────────────────────
  system      每次            原样保留（不可压）     固定
  pinned      用户显式钉住     全部保留               固定
  recent      最近 N 轮        原样保留               按轮计
  tool_out    调用后立即       ★ 超阈值截断，留头留尾  大头，压这里最划算
  history     早期对话         摘要化（按条目摘）      中
  dropped     已淘汰           丢弃                   0

核心判据：压缩必须有【可验证的账】——
  压了多少、留了什么、丢了什么，三者都要能列出来。
  只报"压缩率 70%"而不说丢了什么，等于没说。
"""
import json, re, hashlib

# 每层的压缩命运
POLICY = {
    "system":   {"keep": "all",    "max_chars": None},
    "pinned":   {"keep": "all",    "max_chars": None},
    "recent":   {"keep": "all",    "max_chars": None},
    "tool_out": {"keep": "head_tail", "max_chars": 800},
    "history":  {"keep": "digest", "max_chars": 200},
}
# head_tail 保留的头尾比例
HEAD_RATIO = 0.6

def _truncate_head_tail(s, max_chars):
    """超长内容：留头留尾，中间标记丢弃量。不静默删。"""
    if max_chars is None or len(s) <= max_chars: return s, 0
    h = int(max_chars * HEAD_RATIO); t = max_chars - h - 60
    cut = len(s) - max_chars
    marker = f"\n…[压缩：此处丢弃 {cut} 字符]…\n"
    return s[:h] + marker + (s[-t:] if t > 0 else ""), cut

def _digest(s, max_chars):
    """历史条目摘要：保留首句 + 数字结论，其余丢。"""
    if max_chars is None or len(s) <= max_chars: return s, 0
    # 抓有数字的片段——结论通常带数字
    nums = re.findall(r"[^\s。；\n]{0,18}\d[\d.]*[^\s。；\n]{0,18}", s)
    first = s[:max_chars//2].split("\n")[0]
    tail = (" | 关键数字: " + "; ".join(nums[:6])) if nums else ""
    out = (first + tail)[:max_chars]
    return out, len(s) - len(out)

def compress(items, budget_chars=None):
    """
    items: [{"layer": ..., "text": ...}, ...]
    返回带账目的压缩结果：压了多少、留了什么、丢了什么。
    """
    kept, ledger = [], []
    for i, it in enumerate(items):
        layer = it.get("layer", "history")
        # ★ 字段名完全写错（比如 body / content 以外的任何名字）会被静默当成空串，
        #   整段内容无声消失 —— 这是最危险的一种失败：不报错、不留痕。
        #   所以这里显式拒绝。content 作为别名仍接受（宽容），
        #   但两个都没有 → 抛错，绝不静默归零。
        if "text" not in it and "content" not in it:
            raise KeyError(
                f"items[{i}] 缺 text 字段（层={layer}）。"
                f"现有键={sorted(it.keys())}。"
                f"传错字段名会让内容静默消失，因此这里显式报错而不是默认空串。"
            )
        text = it.get("text", it.get("content", ""))
        pol   = POLICY.get(layer, POLICY["history"])
        before = len(text)

        if pol["keep"] == "all":
            out, cut = text, 0
        elif pol["keep"] == "head_tail":
            out, cut = _truncate_head_tail(text, pol["max_chars"])
        elif pol["keep"] == "digest":
            out, cut = _digest(text, pol["max_chars"])
        else:
            out, cut = "", before

        kept.append({"layer": layer, "text": out,
                     "sha": hashlib.sha256(out.encode()).hexdigest()[:8]})
        ledger.append({"i": i, "layer": layer, "before": before,
                       "after": len(out), "cut": cut,
                       "fate": pol["keep"]})

    total_before = sum(l["before"] for l in ledger)
    total_after  = sum(l["after"]  for l in ledger)
    # 超预算：从 history 层再砍（tool_out 已经压过）
    if budget_chars and total_after > budget_chars:
        over = total_after - budget_chars
        for k in reversed(range(len(kept))):
            if over <= 0: break
            if kept[k]["layer"] != "history": continue
            room = len(kept[k]["text"])
            drop = min(room, over)
            kept[k]["text"] = kept[k]["text"][:room - drop]
            ledger[k]["after"] -= drop; ledger[k]["cut"] += drop
            over -= drop
        total_after = sum(l["after"] for l in ledger)

    return {
        "kept": kept,
        "ledger": ledger,
        "before": total_before,
        "after": total_after,
        "ratio": round(1 - total_after / total_before, 4) if total_before else 0,
        # ★ 账目：丢了什么必须能列出来，不能只报压缩率
        "dropped": [{"i": l["i"], "layer": l["layer"], "cut": l["cut"]}
                    for l in ledger if l["cut"] > 0],
    }

if __name__ == "__main__":
    demo = [
        {"layer": "system",   "text": "你是洛神。判据优先。"},
        {"layer": "pinned",   "text": "用户说：不许编造。"},
        {"layer": "tool_out", "text": "命令输出……" + "x"*3000},
        {"layer": "history",  "text": "上一轮发现 grep 命中 0 条，MCP 未实现。压缩率 0.31。"},
        {"layer": "recent",   "text": "当前问题：补四项能力。"},
    ]
    r = compress(demo, budget_chars=2000)
    print(f"压缩前 {r['before']} 字符 → 压缩后 {r['after']} 字符")
    print(f"压缩率 {r['ratio']*100:.1f}%")
    print("\n逐层账目：")
    for l in r["ledger"]:
        print(f"  [{l['layer']:<9}] {l['before']:>5} → {l['after']:>5}  丢 {l['cut']:>5}  ({l['fate']})")
    print("\n丢弃清单：", r["dropped"])
