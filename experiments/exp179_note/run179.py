#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
178 记笔记：外化存储 vs 内化记忆
语料 = 本对话用户侧真实消息（47 条）

实验 A：内化（记忆随年龄衰减 / 容量有限） vs 外化（笔记不衰减）
实验 B：笔记形式的信息密度（书本=全文 / 符号=编号 / 数字=编号 / 画=结构图）
"""
import os, json, math
from collections import defaultdict, Counter

D = "/data/workspace/luoshen-o1/experiments/exp179_note"
SRC = "/data/workspace/luoshen-o1/experiments/exp175_align/u_side.txt"
K = 3          # 上下文深度（176 号实测最优眼深 = 2，此处用 K=3 做字符 n-gram）
ALPHA = 0.1    # 加性平滑

lines = [l.strip() for l in open(SRC, encoding="utf-8") if l.strip()]
n_test = 10
train, test = lines[:-n_test], lines[-n_test:]
train_text = "".join(train)
test_text = "".join(test)

# 每个训练字符属于第几条消息 -> 年龄
msg_of = []
for idx, l in enumerate(train):
    msg_of += [idx] * len(l)
last = len(train) - 1

V = len(set(train_text) | set(test_text))

print("messages=%d  train_chars=%d  test_chars=%d  V=%d"
      % (len(lines), len(train_text), len(test_text), V))


def build(text, weight_fn=None, keep_min=1, drop_counts=False):
    """weight_fn(i) -> 该位置权重；keep_min: 只保留总权重>=keep_min 的上下文"""
    m = defaultdict(Counter)
    for i in range(len(text) - K):
        ctx = text[i:i + K]
        nxt = text[i + K]
        w = 1.0 if weight_fn is None else weight_fn(i)
        m[ctx][nxt] += w
    out = {}
    for c, cnt in m.items():
        tot = sum(cnt.values())
        if tot < keep_min:
            continue
        if drop_counts:
            # 只存边，不存频次 -> 均匀
            out[c] = Counter({k: 1.0 for k in cnt})
        else:
            out[c] = cnt
    return out


def bits_per_char(model, text):
    tot, n = 0.0, 0
    for i in range(len(text) - K):
        ctx = text[i:i + K]
        nxt = text[i + K]
        cnt = model.get(ctx)
        if cnt is None:
            p = 1.0 / V
        else:
            s = sum(cnt.values())
            p = (cnt.get(nxt, 0.0) + ALPHA) / (s + ALPHA * V)
        tot -= math.log2(p)
        n += 1
    return tot / n if n else float("nan")


def nbytes(model, bytes_per_sym=3, sym_per_entry=4, count_bytes=4, drop_counts=False):
    """笔记占多少字节：每条 (ctx+next) = sym_per_entry 个符号"""
    entries = sum(len(v) for v in model.values())
    per = sym_per_entry * bytes_per_sym + (0 if drop_counts else count_bytes)
    return entries * per, entries


res = {}

# ---------- 实验 A：内化衰减 vs 外化笔记 ----------
print("\n=== A: 内化（衰减） vs 外化（笔记） ===")
base_external = None
curveA = []
for lam in [0.0, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]:
    if lam == 0.0:
        wf = None
    else:
        wf = (lambda L: (lambda i: math.exp(-L * (last - msg_of[i]))))(lam)
    m = build(train_text, weight_fn=wf)
    b = bits_per_char(m, test_text)
    nb, ent = nbytes(m)
    if lam == 0.0:
        base_external = b
    curveA.append({"lambda": lam, "bits": round(b, 4),
                   "entries": ent, "bytes": nb,
                   "delta_vs_note": round(b - base_external, 4)})
    print("  lam=%-5s bits=%.4f  entries=%-6d  Δvs笔记=%+.4f"
          % (lam, b, ent, b - base_external))

res["A_decay"] = curveA

# ---------- 实验 A2：容量受限（只保留 top-M 条） ----------
print("\n=== A2: 容量受限（内化只能装下 top-M 条目） ===")
full = build(train_text)
flat = []
for c, cnt in full.items():
    for nx, w in cnt.items():
        flat.append((w, c, nx))
flat.sort(key=lambda x: -x[0])
tot_entries = len(flat)
curveA2 = []
for M in [100, 500, 2000, 5000, 20000, tot_entries]:
    mm = defaultdict(Counter)
    for w, c, nx in flat[:M]:
        mm[c][nx] = w
    b = bits_per_char(mm, test_text)
    nb, ent = nbytes(mm)
    curveA2.append({"M": M, "frac": round(M / tot_entries, 4),
                    "bits": round(b, 4), "bytes": nb,
                    "delta_vs_full": round(b - base_external, 4)})
    print("  M=%-7d (%.3f of full)  bits=%.4f  Δ=%+.4f"
          % (M, M / tot_entries, b, b - base_external))
res["A2_capacity"] = curveA2

# ---------- 实验 B：笔记形式 ----------
print("\n=== B: 笔记形式 = 同样内容，不同载体 ===")
forms = {}

# 1 书本：原文全文（逐字抄）
m_full = build(train_text)
forms["书本·原文全文"] = {"model": m_full, "bytes_per_sym": 3, "drop": False,
                        "note_bytes_override": len(train_text.encode("utf-8"))}

# 2 去重本：只抄出现 >=2 次的上下文
m_p2 = build(train_text, keep_min=2)
forms["去重本·只抄复现≥2"] = {"model": m_p2, "bytes_per_sym": 3, "drop": False}

# 3 稀疏本：只抄 >=3
m_p3 = build(train_text, keep_min=3)
forms["稀疏本·只抄复现≥3"] = {"model": m_p3, "bytes_per_sym": 3, "drop": False}

# 4 符号/数字：符号表编号，2 字节/符号（汉字 UTF-8 是 3 字节）
m_num = build(train_text)
forms["符号·数字编号(2B/符)"] = {"model": m_num, "bytes_per_sym": 2, "drop": False}

# 5 数字极致：编号 + 去重
m_num2 = build(train_text, keep_min=2)
forms["符号·编号+去重"] = {"model": m_num2, "bytes_per_sym": 2, "drop": False}

# 6 画：只存结构边，不存频次
m_graph = build(train_text, drop_counts=True)
forms["画·结构图(只存边)"] = {"model": m_graph, "bytes_per_sym": 3, "drop": True}

# 7 画+编号
m_graph2 = build(train_text, drop_counts=True)
forms["画·结构图+编号"] = {"model": m_graph2, "bytes_per_sym": 2, "drop": True}

curveB = []
for name, cfg in forms.items():
    m = cfg["model"]
    b = bits_per_char(m, test_text)
    nb, ent = nbytes(m, bytes_per_sym=cfg["bytes_per_sym"], drop_counts=cfg["drop"])
    if "note_bytes_override" in cfg:
        nb = cfg["note_bytes_override"]
    gain = base_external - b   # 相对"无笔记基线"省下的 bits（负=更差）
    # 无笔记基线 = 只用测试集字符频率（完全没记）
    curveB.append({"form": name, "bits": round(b, 4), "entries": ent,
                   "note_bytes": nb, "gain_vs_full_note": round(gain, 4)})
    print("  %-22s bits=%.4f  entries=%-6d 笔记字节=%-8d 相对全文笔记Δ=%+.4f"
          % (name, b, ent, nb, gain))
res["B_forms"] = curveB

# ---------- 无笔记基线 ----------
uni = Counter(train_text)
tb, tn = 0.0, 0
for ch in test_text:
    p = (uni.get(ch, 0) + ALPHA) / (sum(uni.values()) + ALPHA * V)
    tb -= math.log2(p); tn += 1
no_note_bits = tb / tn
print("\n无笔记基线（只记字符频率，不记顺序）bits=%.4f" % no_note_bits)
res["no_note_baseline"] = round(no_note_bits, 4)
res["meta"] = {"K": K, "V": V, "train_chars": len(train_text),
               "test_chars": len(test_text), "n_msgs": len(lines),
               "full_entries": tot_entries}

# ---------- 信息密度：每 KB 笔记换回多少 bits ----------
print("\n=== 效率：每 KB 笔记省下多少 bits ===")
eff = []
for e in curveB:
    if e["note_bytes"] <= 0:
        continue
    saved = no_note_bits - e["bits"]
    per_kb = saved / (e["note_bytes"] / 1024.0)
    eff.append({"form": e["form"], "note_kb": round(e["note_bytes"] / 1024.0, 2),
                "saved_bits": round(saved, 4), "bits_per_kb": round(per_kb, 4)})
    print("  %-22s 笔记%7.2f KB  省 %6.4f bits  -> %8.4f bits/KB"
          % (e["form"], e["note_bytes"] / 1024.0, saved, per_kb))
res["efficiency"] = sorted(eff, key=lambda x: -x["bits_per_kb"])

json.dump(res, open(os.path.join(D, "result179.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote result179.json")
