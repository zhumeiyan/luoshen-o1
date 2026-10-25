#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
193 号：种子是统计的，还是朊病毒式的？—— 抗稀释测试

判据：
  统计种子（线性）：被反向数据稀释时，贡献按混合比衰减，最终趋于 0，无阈值。
  朊病毒种子（自催化）：接触即诱导折叠，稀释不掉；衰减远慢于混合比预测，
  且应存在临界核（阈值）。

做法：
  S  = 用户语料前半（结构化种子）
  S' = 同字符打乱（非结构化对照：同信息量、无模板）
  C  = 判据核（稀释剂 / 反向数据）
  训练 S + λ|S|·C，在用户语料后半 U_B 上测。
  Δ(λ) = 训 S+C 的表现 − 只训 C 的表现。
  看 Δ(λ)/Δ(0) 的衰减形状：结构化 vs 打乱，谁衰减更慢？
  结构化显著更慢 → 模板化（朊病毒式）；同形 → 纯统计（线性）。
"""
import os, math, json, random, statistics

BASE = "/data/workspace/luoshen-o1"
OUT = f"{BASE}/experiments/exp193_prion"
os.makedirs(OUT, exist_ok=True)

U = open(f"{BASE}/experiments/exp180_record/u_side_full.txt", encoding="utf-8").read().strip()
J = open(f"{BASE}/evidence/失败模式库/判据核.md", encoding="utf-8").read()

rng = random.Random(42)
K = 3
SM = 0.1

half = len(U) // 2
UA, UB = U[:half], U[half:]


def train(text):
    d = {}
    for i in range(len(text) - K):
        ctx = text[i:i + K - 1]
        ch = text[i + K - 1]
        d.setdefault(ctx, {})
        d[ctx][ch] = d[ctx].get(ch, 0) + 1
    vocab = set(text)
    model = {}
    for ctx, cd in d.items():
        tot = sum(cd.values()) + SM * len(vocab)
        m = {c: (v + SM) / tot for c, v in cd.items()}
        m["__def__"] = SM / tot
        model[ctx] = m
    return model, vocab


def evaluate(model, vocab, text):
    tot = 0.0
    correct = 0
    n = 0
    for i in range(len(text) - K):
        ctx = text[i:i + K - 1]
        ch = text[i + K - 1]
        n += 1
        m = model.get(ctx)
        if m:
            p = m.get(ch, m["__def__"])
            best = max((c for c in m if c != "__def__"), key=lambda c: m[c])
            if best == ch:
                correct += 1
        else:
            p = 1.0 / max(len(vocab), 2)
        tot -= math.log2(p)
    if n == 0:
        return float("nan"), 0.0
    return tot / n, correct / n


noise = list(UA)
rng.shuffle(noise)
S_NOISE = "".join(noise)

SEEDS = {"structured": UA, "shuffled": S_NOISE}
LAMS = [0, 0.5, 1, 2, 5, 10, 20, 50]

rows = []
for tag, S in SEEDS.items():
    for lam in LAMS:
        size = int(lam * len(S))
        if size > 0:
            start = rng.randint(0, max(0, len(J) - size - 1))
            C = J[start:start + size]
        else:
            C = ""
        if C:
            mb, vb = train(C)
            b0, a0 = evaluate(mb, vb, UB)
        else:
            b0, a0 = math.log2(max(len(set(UB)), 2)), 0.0
        ms, vs = train(S + C)
        b1, a1 = evaluate(ms, vs, UB)
        rows.append({
            "seed": tag, "lam": lam, "C_chars": size,
            "bits_C": b0, "bits_SplusC": b1,
            "acc_C": a0, "acc_SplusC": a1,
            "gain_bits": (b0 - b1) if C else None,
            "gain_acc": a1 - a0,
        })

norm = {}
for tag in SEEDS:
    base = next(r for r in rows if r["seed"] == tag and r["lam"] == 0)
    g0 = base["gain_acc"]
    norm[tag] = []
    for r in rows:
        if r["seed"] != tag:
            continue
        norm[tag].append({
            "lam": r["lam"],
            "gain_acc": r["gain_acc"],
            "rel": (r["gain_acc"] / g0) if g0 else None,
        })

fit = {}
for tag in SEEDS:
    pts = [(math.log10(1 + d["lam"]), math.log10(d["rel"]))
           for d in norm[tag] if d["rel"] and d["rel"] > 0 and d["lam"] > 0]
    if len(pts) >= 2:
        mx = statistics.mean(p[0] for p in pts)
        my = statistics.mean(p[1] for p in pts)
        num = sum((x - mx) * (y - my) for x, y in pts)
        den = sum((x - mx) ** 2 for x, y in pts)
        fit[tag] = {"slope": (num / den) if den else None, "n_points": len(pts)}
    else:
        fit[tag] = {"slope": None, "n_points": len(pts)}

out = {
    "K": K, "smoothing": SM,
    "UA_chars": len(UA), "UB_chars": len(UB), "J_chars": len(J),
    "rows": rows, "normalized": norm, "decay_fit": fit,
}
with open(f"{OUT}/result193.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"UA={len(UA)} UB={len(UB)} J={len(J)}")
for r in rows:
    print(f"{r['seed']:10s} lam={r['lam']:<5} C={r['C_chars']:<7} "
          f"acc_C={r['acc_C']:.4f} acc_S+C={r['acc_SplusC']:.4f} "
          f"gain={r['gain_acc']:+.4f}")
print("decay fit:", json.dumps(fit, ensure_ascii=False))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for tag, style, col in [("structured", "o-", "tab:red"), ("shuffled", "s--", "tab:blue")]:
        xs = [d["lam"] for d in norm[tag]]
        ys = [d["rel"] for d in norm[tag]]
        ax[0].plot([max(x, 0.4) for x in xs], ys, style, color=col, label=tag)
        ax[1].plot([max(x, 0.4) for x in xs], [d["gain_acc"] for d in norm[tag]],
                   style, color=col, label=tag)
    ax[0].set_xscale("log")
    ax[0].set_xlabel("稀释倍数 λ")
    ax[0].set_ylabel("相对增益 Δ(λ)/Δ(0)")
    ax[0].set_title("种子在稀释下的存活率")
    ax[0].legend()
    ax[0].grid(alpha=0.3)
    ax[1].set_xscale("log")
    ax[1].set_xlabel("稀释倍数 λ")
    ax[1].set_ylabel("绝对增益 Δ acc")
    ax[1].set_title("绝对贡献")
    ax[1].legend()
    ax[1].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUT}/render193.png", dpi=110)
    print("fig ok")
except Exception as e:
    print("fig failed:", e)
