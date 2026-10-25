#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp139: 语义手性与手性破缺（硅基版 Frank / Soai）

Part A  手性算子识别
  算子必须满足两条才算"手性操作"：
    (1) 对合性  sigma(sigma(x)) == x
    (2) 非对称性 sigma(x) != x
  再量第三条：翻转杠杆率 = 预测翻转率 / 归一化扰动幅度
  对照：表面扰动（换主语 ROLE）幅度相当但不翻转

Part B  Frank-Soai 硅基版
  初始手性偏移极小 -> 自催化放大 -> 看是否被锁死成单手性
  两种更新模式：REPLACE（替换）/ ACCUMULATE（累积）
  扩展：多类不均匀时，稀有类是否先消失
"""
import math, random, json
from collections import Counter

# ---------------- 语料 ----------------
SUBJ = ["系统", "管理员", "服务", "进程", "用户", "网关"]
VERB_P = ["允许", "执行", "发送", "读取", "写入", "记录", "校验"]   # 极性 +1
VERB_N = ["禁止", "拦截", "阻断", "拒绝", "删除", "丢弃"]          # 极性 -1
OBJ = ["文件", "数据", "请求", "日志", "消息", "连接", "凭证"]
COMP = ["到本地", "至服务器", "给用户", "即刻", "静默", "全部"]

ALL_V = VERB_P + VERB_N

def polarity_of(v):
    return 1 if v in VERB_P else -1

def gen(rng, neg_rate=0.30):
    s = rng.choice(SUBJ)
    v = rng.choice(ALL_V)
    neg = rng.random() < neg_rate
    o = rng.choice(OBJ)
    c = rng.choice(COMP)
    toks = [s] + (["不"] if neg else []) + [v, o, c]
    pol = polarity_of(v) * (-1 if neg else 1)
    return toks, ("PERMIT" if pol > 0 else "DENY")

# ---------------- 算子 ----------------
def op_neg(toks):
    """插入/删除否定词 —— 极性翻转，1 个 token 的改动"""
    t = list(toks)
    if "不" in t:
        return [x for x in t if x != "不"]
    return t[:1] + ["不"] + t[1:]

def _idx(toks):
    """返回 (主语位, 动词位, 宾语位)"""
    if "不" in toks:
        iv = toks.index("不") + 1
    else:
        iv = 1
    return 0, iv, iv + 1

def op_swap(toks):
    """主宾互换 —— 语序镜像，词集合完全不变"""
    t = list(toks)
    i_s, _, i_o = _idx(toks)
    t[i_s], t[i_o] = t[i_o], t[i_s]
    return t

def op_rev(toks):
    """整体倒装 —— 严格对合"""
    return list(reversed(toks))

def op_role(toks):
    """换主语（同集合内）—— 表面扰动对照，标签不变，词在词汇表内"""
    t = list(toks)
    i_s, _, _ = _idx(toks)
    cur = t[i_s]
    cand = [x for x in SUBJ if x != cur]
    t[i_s] = cand[hash(tuple(toks)) % len(cand)]
    return t

OPS = {
    "NEG":  (op_neg,  "极性翻转（否定词增删）"),
    "SWAP": (op_swap, "语序镜像（主宾互换）"),
    "REV":  (op_rev,  "整体倒装"),
    "ROLE": (op_role, "表面对照（换主语）"),
}

# ---------------- 表示 ----------------
def f_bow(toks):
    return Counter(toks)

def f_pos(toks):
    c = Counter(toks)
    for a, b in zip(toks, toks[1:]):
        c[a + "|" + b] += 1
    return c

REPR = {"BOW": (f_bow, "词袋（位置无关，非手性表示）"),
        "POS": (f_pos, "词+相邻二元组（含序，手性表示）")}

# ---------------- 朴素贝叶斯 ----------------
class MNB:
    def __init__(self, alpha=0.4):
        self.alpha = alpha

    def fit(self, X, y):
        self.classes = sorted(set(y))
        self.prior, self.cnt, self.tot = {}, {}, {}
        V = set()
        for c in self.classes:
            self.prior[c] = 0; self.cnt[c] = Counter(); self.tot[c] = 0
        for xi, yi in zip(X, y):
            self.prior[yi] += 1
            for f, n in xi.items():
                self.cnt[yi][f] += n
                self.tot[yi] += n
                V.add(f)
        N = len(X)
        self.V = list(V)
        for c in self.classes:
            self.prior[c] = math.log(self.prior[c] / N)
        self.den = {c: self.tot[c] + self.alpha * len(self.V) for c in self.classes}
        self.defp = {c: math.log(self.alpha / self.den[c]) for c in self.classes}
        self.lp = {c: {f: math.log((self.cnt[c][f] + self.alpha) / self.den[c])
                       for f in self.V if self.cnt[c][f]} for c in self.classes}

    def predict(self, xi):
        best, bc = None, None
        for c in self.classes:
            lp = self.lp[c]
            s = self.prior[c] + sum(n * lp.get(f, self.defp[c]) for f, n in xi.items())
            if best is None or s > best:
                best, bc = s, c
        return bc

# ---------------- 度量 ----------------
def edit_ratio(a, b):
    """归一化改动幅度：不同位置数 / max(len)"""
    n = max(len(a), len(b))
    if n == 0: return 0.0
    d = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    return d / n

# ================= Part A =================
def part_a(seed=7, ntr=2400, nte=600):
    rng = random.Random(seed)
    tr = [gen(rng) for _ in range(ntr)]
    te = [gen(rng) for _ in range(nte)]

    out = {"seed": seed, "ntr": ntr, "nte": nte, "repr": {}}

    for rname, (fn, rdesc) in REPR.items():
        clf = MNB()
        clf.fit([fn(t) for t, _ in tr], [y for _, y in tr])
        base_pred = [clf.predict(fn(t)) for t, _ in te]
        acc = sum(1 for p, (_, y) in zip(base_pred, te) if p == y) / len(te)

        rows = []
        for oname, (of, odesc) in OPS.items():
            invol, asym, flip, amp = 0, 0, 0, []
            for (t, y), bp in zip(te, base_pred):
                t1 = of(t)
                t2 = of(t1)
                if t2 == t: invol += 1                      # 对合性
                if t1 != t: asym += 1                       # 非对称性
                p1 = clf.predict(fn(t1))
                if p1 != bp: flip += 1                      # 预测翻转
                amp.append(edit_ratio(t, t1))
            n = len(te)
            rows.append({
                "op": oname, "desc": odesc,
                "involution": invol / n, "asym": asym / n,
                "flip": flip / n, "amp": sum(amp) / n,
                "lever": (flip / n) / (sum(amp) / n) if sum(amp) > 0 else float("nan"),
            })
        out["repr"][rname] = {"desc": rdesc, "acc": acc, "ops": rows}
    return out

# ================= Part B =================
def run_frank(mode, gamma, minority=0.49, gens=25, pool_n=1200,
              batch=600, seed=1):
    rng = random.Random(seed)
    pool = Counter()
    pool["L"] = int(round(pool_n * minority))
    pool["R"] = pool_n - pool["L"]
    hist = []
    for g in range(gens):
        tot = sum(pool.values())
        pL = pool["L"] / tot
        if abs(gamma - 1.0) < 1e-9:
            pA = pL
        else:
            a = pL ** gamma
            b = (1 - pL) ** gamma
            pA = a / (a + b) if (a + b) > 0 else pL
        # 有限采样噪声（对应有限样本的统计误差）
        newL = sum(1 for _ in range(batch) if rng.random() < pA)
        newR = batch - newL
        if mode == "REPLACE":
            pool = Counter({"L": newL, "R": newR})
        else:
            pool["L"] += newL
            pool["R"] += newR
        tot = sum(pool.values())
        hist.append(pool["L"] / tot if tot else float("nan"))
    return hist

def run_multiclass(mode, gamma, props, gens=25, pool_n=1200, batch=600, seed=3):
    rng = random.Random(seed)
    pool = Counter()
    for i, p in enumerate(props):
        pool["C%d" % i] = max(1, int(round(pool_n * p)))
    hist = []
    for g in range(gens):
        tot = sum(pool.values())
        ps = {k: v / tot for k, v in pool.items()}
        if abs(gamma - 1.0) < 1e-9:
            amp = ps
        else:
            raw = {k: v ** gamma for k, v in ps.items()}
            s = sum(raw.values())
            amp = {k: v / s for k, v in raw.items()} if s > 0 else ps
        keys = list(pool.keys())
        ws = [amp[k] for k in keys]
        for _ in range(batch):
            r = rng.random(); acc = 0.0; pick = keys[-1]
            for k, w in zip(keys, ws):
                acc += w
                if r <= acc: pick = k; break
            pool[pick] += 1
        if mode == "REPLACE":
            # 只保留本代产物
            newc = Counter()
            for k in keys: newc[k] = 0
            for _ in range(batch):
                r = rng.random(); acc = 0.0; pick = keys[-1]
                for k, w in zip(keys, ws):
                    acc += w
                    if r <= acc: pick = k; break
                newc[pick] += 1
            pool = newc
        tot = sum(pool.values())
        hist.append({k: pool[k] / tot for k in pool if tot})
    return hist

def part_b():
    res = {"binary": [], "multiclass": []}
    for mode in ("REPLACE", "ACCUMULATE"):
        for gamma in (1.0, 1.6, 2.5):
            h = run_frank(mode, gamma)
            res["binary"].append({
                "mode": mode, "gamma": gamma,
                "init": h[0], "final": h[-1], "hist": h,
                "extinct": 1 if (h[-1] < 1e-9 or h[-1] > 1 - 1e-9) else 0,
            })
    props = [0.40, 0.30, 0.18, 0.08, 0.04]
    for mode in ("REPLACE", "ACCUMULATE"):
        h = run_multiclass(mode, 2.0, props)
        first = h[0]; last = h[-1]
        dead = [k for k in first if last.get(k, 0) < 1e-9]
        res["multiclass"].append({
            "mode": mode, "gamma": 2.0, "props": props,
            "init": first, "final": last,
            "dead_classes": dead,
            "rarest_init": min(first.values()),
            "rarest_final": min(last.values()),
        })
    return res

# ================= main =================
if __name__ == "__main__":
    A = part_a()
    B = part_b()

    print("=" * 66)
    print("exp139  语义手性与手性破缺")
    print("=" * 66)

    print("\n--- Part A  手性算子识别 ---")
    for rname, r in A["repr"].items():
        print("\n[%s] %s   基线准确率 %.4f" % (rname, r["desc"], r["acc"]))
        print("  %-6s %-22s %8s %8s %8s %8s %8s" %
              ("op", "desc", "对合", "非对称", "翻转", "幅度", "杠杆"))
        for o in r["ops"]:
            print("  %-6s %-22s %8.3f %8.3f %8.3f %8.3f %8.2f" %
                  (o["op"], o["desc"][:22], o["involution"], o["asym"],
                   o["flip"], o["amp"], o["lever"]))

    print("\n--- Part B  Frank-Soai 硅基版（初始 L 占 49%）---")
    print("  %-12s %6s %10s %10s %8s" % ("mode", "gamma", "init", "final", "锁死"))
    for r in B["binary"]:
        print("  %-12s %6.1f %10.4f %10.4f %8d" %
              (r["mode"], r["gamma"], r["init"], r["final"], r["extinct"]))

    print("\n--- Part B2  稀有类是否先消失（5 类不均匀, gamma=2.0）---")
    for r in B["multiclass"]:
        print("  [%s]" % r["mode"])
        print("    init  %s" % {k: round(v, 4) for k, v in r["init"].items()})
        print("    final %s" % {k: round(v, 4) for k, v in r["final"].items()})
        print("    消失类 %s | 最稀有 %.4f -> %.4f" %
              (r["dead_classes"], r["rarest_init"], r["rarest_final"]))

    with open("result139.json", "w") as f:
        json.dump({"A": A, "B": B}, f, ensure_ascii=False, indent=1)
    print("\n[saved] result139.json")
