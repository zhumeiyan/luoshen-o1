#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
178b 记笔记（修正版）
修 178 的三个错：
  1) 测试集 OOV 未处理 -> 模型竟比 unigram 基线还差（8.58 vs 7.52）。加 <unk>。
  2) 无回退 -> K=3 在 2915 字训练语料上几乎全 miss。改为 K + backoff。
  3) 笔记字节口径不一致（原文抄本 vs ngram 表混算）。统一为"该形式真实占多少字节"。
"""
import os, json, math
from collections import defaultdict, Counter

D = "/data/workspace/luoshen-o1/experiments/exp179_note"
SRC = "/data/workspace/luoshen-o1/experiments/exp175_align/u_side.txt"
ALPHA = 0.1

lines = [l.strip() for l in open(SRC, encoding="utf-8") if l.strip()]
n_test = 8
train, test = lines[:-n_test], lines[-n_test:]
train_text = "".join(train)
test_text = "".join(test)

vocab = sorted(set(train_text))
V = len(vocab) + 1                      # +1 = <unk>
UNK = "<unk>"
idx = {c: i for i, c in enumerate(vocab)}
enc_tr = [idx.get(c, V - 1) for c in train_text]
enc_te = [idx.get(c, V - 1) for c in test_text]
oov = sum(1 for c in test_text if c not in idx)

msg_of = []
for i2, l in enumerate(train):
    msg_of += [i2] * len(l)
last = len(train) - 1

print("train_chars=%d test_chars=%d vocab=%d V=%d  test_OOV=%d(%.1f%%)"
      % (len(train_text), len(test_text), len(vocab), V, oov,
         100.0 * oov / len(test_text)))


def build(enc, weight_fn=None, keep_min=1, drop_counts=False, K=2):
    m = defaultdict(Counter)
    for i in range(len(enc) - K):
        w = 1.0 if weight_fn is None else weight_fn(i)
        m[tuple(enc[i:i + K])][enc[i + K]] += w
    out = {}
    for c, cnt in m.items():
        if sum(cnt.values()) < keep_min:
            continue
        out[c] = Counter({k: 1.0 for k in cnt}) if drop_counts else cnt
    return out


def ngrams(enc, K):
    """建 K 阶回退模型：K, K-1, ..., 1, unigram"""
    levels = []
    for k in range(K, 0, -1):
        levels.append(build(enc, K=k))
    uni = Counter(enc)
    levels.append({"__uni__": uni})
    return levels


def bits_per_char(levels, enc_te, K):
    uni = levels[-1]["__uni__"]
    tot_u = sum(uni.values())
    tot, n = 0.0, 0
    for i in range(len(enc_te) - 1):
        nx = enc_te[i + 1]
        p = None
        for li in range(K):
            k = K - li
            if k < 1:
                break
            ctx = tuple(enc_te[i - k + 1:i + 1])
            if len(ctx) < k:
                continue
            cnt = levels[li].get(ctx)
            if cnt:
                s = sum(cnt.values())
                p = (cnt.get(nx, 0.0) + ALPHA) / (s + ALPHA * V)
                break
        if p is None:
            p = (uni.get(nx, 0) + ALPHA) / (tot_u + ALPHA * V)
        tot -= math.log2(p)
        n += 1
    return tot / n


# ---------- 选最优 K（对应 176 号"眼深"） ----------
print("\n=== 0: 眼深（上下文 K）扫描 ===")
kscan = []
bestK, bestB = None, 1e9
for K in [1, 2, 3, 4]:
    lv = ngrams(enc_tr, K)
    b = bits_per_char(lv, enc_te, K)
    kscan.append({"K": K, "bits": round(b, 4)})
    if b < bestB:
        bestB, bestK = b, K
    print("  K=%d  bits=%.4f" % (K, b))
K = bestK
print("  -> 最优 K=%d" % K)

# ---------- 基线：不记笔记（只留字符频率，无顺序） ----------
uni = Counter(enc_tr)
tu = sum(uni.values())
tb, tn = 0.0, 0
for i in range(len(enc_te) - 1):
    nx = enc_te[i + 1]
    p = (uni.get(nx, 0) + ALPHA) / (tu + ALPHA * V)
    tb -= math.log2(p); tn += 1
BASE = tb / tn
print("\n无笔记基线（只记字符频率/无顺序）bits=%.4f" % BASE)

# ---------- A: 内化衰减 vs 外化笔记 ----------
print("\n=== A: 内化（记忆衰减） vs 外化（笔记不衰减） ===")
lv0 = ngrams(enc_tr, K)
NOTE_BITS = bits_per_char(lv0, enc_te, K)
curveA = []
for lam in [0.0, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]:
    wf = None if lam == 0 else (lambda L: (lambda i: math.exp(-L * (last - msg_of[i]))))(lam)
    lv = []
    for k in range(K, 0, -1):
        lv.append(build(enc_tr, weight_fn=wf, K=k))
    lv.append({"__uni__": Counter(enc_tr)})
    b = bits_per_char(lv, enc_te, K)
    ent = sum(len(v) for v in lv[0].values())
    curveA.append({"lambda": lam, "bits": round(b, 4), "entries": ent,
                   "delta_vs_note": round(b - NOTE_BITS, 4)})
    print("  lam=%-5s bits=%.4f entries=%-6d Δvs笔记=%+.4f" % (lam, b, ent, b - NOTE_BITS))

# ---------- A2: 容量受限 ----------
print("\n=== A2: 容量受限（内化只装得下 top-M 条） ===")
full0 = lv0[0]
flat = sorted(((w, c, nx) for c, cnt in full0.items() for nx, w in cnt.items()),
              key=lambda x: -x[0])
tot_entries = len(flat)
curveA2 = []
for frac in [0.02, 0.05, 0.1, 0.25, 0.5, 1.0]:
    M = max(1, int(tot_entries * frac))
    mm = defaultdict(Counter)
    for w, c, nx in flat[:M]:
        mm[c][nx] = w
    lv = [mm]
    for k in range(K - 1, 0, -1):
        lv.append(build(enc_tr, K=k))
    lv.append({"__uni__": Counter(enc_tr)})
    b = bits_per_char(lv, enc_te, K)
    curveA2.append({"frac": frac, "M": M, "bits": round(b, 4),
                    "delta_vs_note": round(b - NOTE_BITS, 4)})
    print("  M=%-6d (%.2f) bits=%.4f Δ=%+.4f" % (M, frac, b, b - NOTE_BITS))

# ---------- B: 笔记形式 ----------
print("\n=== B: 笔记形式（同样内容，不同载体） ===")
raw_bytes = len(train_text.encode("utf-8"))
forms = []

# 1 抄本：原文照抄（用时重读重建）——人类最古老的形式
forms.append(("抄本·原文照抄", None, raw_bytes))

# 2 摘抄：只抄复现≥2 的上下文（ngram 表，3B/符）
m2 = build(enc_tr, keep_min=2, K=K)
forms.append(("摘抄·只留复现≥2", m2, len(m2) * ((K + 1) * 3 + 4)))

# 3 编号：符号→整数，2B/符（数字/符号记事）
m3 = build(enc_tr, K=K)
forms.append(("符号·数字编号(2B/符)", m3, len(m3) * ((K + 1) * 2 + 4)))

# 4 编号+摘抄
m4 = build(enc_tr, keep_min=2, K=K)
forms.append(("符号·编号+摘抄", m4, len(m4) * ((K + 1) * 2 + 4)))

# 5 画：只存结构边，不存频次（=图/拓扑）
m5 = build(enc_tr, drop_counts=True, K=K)
forms.append(("画·结构图(只存边)", m5, len(m5) * ((K + 1) * 2)))

curveB = []
for name, m, nb in forms:
    if m is None:
        b = NOTE_BITS          # 抄本可完整重建
    else:
        lv = [m]
        for k in range(K - 1, 0, -1):
            lv.append(build(enc_tr, K=k))
        lv.append({"__uni__": Counter(enc_tr)})
        b = bits_per_char(lv, enc_te, K)
    saved = BASE - b
    curveB.append({"form": name, "bits": round(b, 4), "note_bytes": nb,
                   "note_kb": round(nb / 1024.0, 3),
                   "saved_vs_note_absent": round(saved, 4),
                   "bits_per_kb": round(saved / (nb / 1024.0), 4)})
    print("  %-22s bits=%.4f 笔记=%8d B(%6.2f KB) 省%+.4f -> %+.4f bits/KB"
          % (name, b, nb, nb / 1024.0, saved, saved / (nb / 1024.0)))

res = {"meta": {"K": K, "V": V, "vocab": len(vocab),
                "train_chars": len(train_text), "test_chars": len(test_text),
                "test_OOV": oov, "raw_bytes": raw_bytes},
       "kscan": kscan, "baseline_no_note": round(BASE, 4),
       "note_bits": round(NOTE_BITS, 4),
       "A_decay": curveA, "A2_capacity": curveA2,
       "B_forms": sorted(curveB, key=lambda x: -x["bits_per_kb"])}
json.dump(res, open(os.path.join(D, "result179b.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote result179b.json")
