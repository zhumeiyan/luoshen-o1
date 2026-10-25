"""
116 · a≠b ↔ a=b 是逻辑：四种形式化逐条测
不说它"深刻"，先看它在哪种逻辑里能真、且能假（可证伪）。
"""
import itertools, json
import numpy as np

R = {}

def falsifiable(truths):
    """一条解释只有在真/假都出现时才可证伪；只出真或只出假 = 饱和 = 死的命题"""
    t = int(sum(bool(x) for x in truths)); f = len(truths) - t
    return dict(n_true=t, n_false=f, saturable=(t > 0 and f > 0))

# ---------- Part 1 · 经典二值：公式是不是永假式 ----------
rows = []
for a, b in itertools.product((0, 1), repeat=2):
    P = int(a != b)          # a≠b
    Q = int(a == b)          # a=b
    rows.append(dict(a=a, b=b, neq=P, eq=Q, formula=int(P == Q)))
n_true = sum(r["formula"] for r in rows)
R["classical"] = dict(rows=rows, verdict="永假式（P↔¬P）" if n_true == 0 else "可真",
                      **falsifiable([bool(r["formula"]) for r in rows]))

# ---------- Part 2 · 四种解释，各自能否【同时产生真和假】 ----------
# 判据：一条解释只有在真/假都出现时才可证伪；只出真或只出假 = 饱和 = 死的命题

def falsifiable(truths):
    t = sum(truths); f = len(truths) - t
    return dict(n_true=t, n_false=f, saturable=(t > 0 and f > 0))

# ② 时序/模态：单时刻仍假，但在窗口内 ∃(a≠b) ∧ ∃(a=b)
temporal = {}
b_fixed = 1
for T in [1, 2, 4, 8, 16, 32, 10**9]:   # T=10**9 视为恒定
    a_seq = [b_fixed if (t // max(T, 1)) % 2 == 0 else 1 - b_fixed
             for t in range(64)]
    if T >= 10**9:
        a_seq = [b_fixed] * 64
    neq_ever = any(a != b_fixed for a in a_seq)
    eq_ever = any(a == b_fixed for a in a_seq)
    temporal[T] = dict(neq_ever=bool(neq_ever), eq_ever=bool(eq_ever),
                       formula=bool(neq_ever and eq_ever))
R["temporal"] = dict(scan=temporal,
                     **falsifiable([v["formula"] for v in temporal.values()]))

# ③ 次协调 LP（三值）：值 = 真值集合 ⊆ {T,F}
T, F, B = frozenset({"T"}), frozenset({"F"}), frozenset({"T", "F"})
def neg(x): return frozenset({"F" if v == "T" else "T" for v in x})
def meet(x, y):  # ∧
    out = set()
    if "T" in x and "T" in y: out.add("T")
    if "F" in x or "F" in y: out.add("F")
    return frozenset(out)
def join(x, y):  # ∨
    out = set()
    if "T" in x or "T" in y: out.add("T")
    if "F" in x and "F" in y: out.add("F")
    return frozenset(out)
def imp(x, y): return join(neg(x), y)
def iff(x, y): return meet(imp(x, y), imp(y, x))
def eq3(a, b):
    if a == b: return a
    if a == B or b == B: return B
    return F
NAMES = {T: "T", F: "F", B: "B"}
lp_rows = []
for a, b in itertools.product((T, F, B), repeat=2):
    e = eq3(a, b)
    form = iff(neg(e), e)
    lp_rows.append(dict(a=NAMES[a], b=NAMES[b], eq=NAMES[e],
                        formula=NAMES[form], designated=("T" in form)))
R["paraconsistent_LP"] = dict(
    rows=lp_rows, **falsifiable([r["designated"] for r in lp_rows]))

# ④ 相对同一：= 解释为"在某粒度 k 下投影同像"
rng = np.random.default_rng(0)
a_vec = rng.normal(0, 1, 64)
b_vec = a_vec + rng.normal(0, 0.25, 64)      # 细粒度不等
rel = {}
# 归一化到 [0,1] 后按 k 个桶粗粒化；k=桶数（k 小=粗）
# 必须用【同一个变换】归一化两者：分别归一化会把两个不同向量拉到同一区间，
# 人为抬高同像率（又一个会静默造假的 bug）
lo, hi = a_vec.min(), np.ptp(a_vec)
an = (a_vec - lo) / (hi + 1e-12)
bn = (b_vec - lo) / (hi + 1e-12)
for k in [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 128]:
    qa = np.floor(an * k).astype(int)
    qb = np.floor(bn * k).astype(int)
    same_rate = float(np.mean(qa == qb))
    neq_fine = not np.allclose(a_vec, b_vec)
    # 判据用同像率（连续量），不用"全部相同"（后者会饱和在假——本轮自曝）
    eq_coarse = bool(same_rate > 0.5)
    rel[k] = dict(same_rate=round(same_rate, 4), neq_fine=bool(neq_fine),
                  eq_coarse=eq_coarse, formula=bool(neq_fine and eq_coarse))
R["relative_identity"] = dict(scan=rel,
                              **falsifiable([v["formula"] for v in rel.values()]))

R["falsifiability_table"] = {
    name: dict(n_true=R[name]["n_true"], n_false=R[name]["n_false"],
               saturable=R[name]["saturable"])
    for name in ["classical", "temporal", "paraconsistent_LP", "relative_identity"]
}

# ---------- Part 3 · 动力学解释：a≠b 产生恢复力，a=b 是不动点 ----------
def dyn(k, steps=200, sigma=0.0, seed=0, b=0.5, a0=0.0):
    rg = np.random.default_rng(seed)
    a = a0; traj = [a]; flips = 0; prev_sign = None
    for t in range(steps):
        a = a + k * (b - a) + sigma * rg.normal()
        traj.append(a)
        sgn = np.sign(b - a)
        if prev_sign is not None and sgn != prev_sign and sgn != 0:
            flips += 1
        prev_sign = sgn
    traj = np.asarray(traj)
    return dict(k=k, final_gap=float(abs(traj[-1] - b)),
                converged=bool(abs(traj[-1] - b) < 1e-3),
                flips=int(flips), max_abs=float(np.max(np.abs(traj))))

dyn_scan = [dyn(k) for k in [0.0, 0.05, 0.1, 0.3, 0.5, 1.0, 1.5, 1.8, 2.0, 2.5]]
R["dynamics"] = dict(scan=dyn_scan,
                     k0_stuck=bool(dyn_scan[0]["final_gap"] > 1e-3),
                     k1_onestep=bool(dyn_scan[5]["final_gap"] < 1e-9),
                     divergent=[d["k"] for d in dyn_scan if d["max_abs"] > 1e3])

print(json.dumps(R, ensure_ascii=False, indent=1))
with open("res116_logic.json", "w") as f:
    json.dump(R, f, ensure_ascii=False, indent=1)
