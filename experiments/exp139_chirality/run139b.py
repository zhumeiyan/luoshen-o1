#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp139b: 修正版

Part A2  镜像逃逸（核心）
  保集合镜像 sigma：词集合完全不变，只换语序。
  真实标签 NORMAL vs MIRROR 不同，但成分一样。
  问：检测器能不能看见？
    BOW 表示（位置无关 = 非手性受体）  -> 预期瞎
    POS 表示（含序 = 手性受体）        -> 预期能看见
  阴性对照：换宾语（词集合变了），BOW 应当能看见
            => 证明 BOW 不是永远瞎，只对"保集合镜像"瞎

Part C  Frank 动力学两问
  C1 剂量扫描（确定性）：初始对映体过量 chi0 -> 终态 chi
  C2 自发对称性破缺：chi0 = 0，有噪声，看是否自发锁死、锁死到哪一端
"""
import math, random, json
from collections import Counter

SUBJ = ["系统", "管理员", "服务", "进程", "用户", "网关"]
VERB_P = ["允许", "执行", "发送", "读取", "写入", "记录", "校验"]
VERB_N = ["禁止", "拦截", "阻断", "拒绝", "删除", "丢弃"]
OBJ = ["文件", "数据", "请求", "日志", "消息", "连接", "凭证"]
COMP = ["到本地", "至服务器", "给用户", "即刻", "静默", "全部"]
ALL_V = VERB_P + VERB_N


def gen(rng, neg_rate=0.30):
    s = rng.choice(SUBJ)
    v = rng.choice(ALL_V)
    neg = rng.random() < neg_rate
    o = rng.choice(OBJ)
    c = rng.choice(COMP)
    return [s] + (["不"] if neg else []) + [v, o, c]


def _idx(toks):
    iv = toks.index("不") + 1 if "不" in toks else 1
    return 0, iv, iv + 1


def op_swap(toks):
    t = list(toks)
    i_s, _, i_o = _idx(toks)
    t[i_s], t[i_o] = t[i_o], t[i_s]
    return t


def op_obj(toks):
    """换宾语（词集合改变）—— 阴性对照"""
    t = list(toks)
    _, _, i_o = _idx(toks)
    cur = t[i_o]
    cand = [x for x in OBJ if x != cur]
    t[i_o] = cand[hash(tuple(toks) * 3) % len(cand)]
    return t


def f_bow(toks):
    return Counter(toks)


def f_pos(toks):
    c = Counter(toks)
    for a, b in zip(toks, toks[1:]):
        c[a + "|" + b] += 1
    return c


class MNB:
    def __init__(self, alpha=0.4):
        self.alpha = alpha

    def fit(self, X, y):
        self.classes = sorted(set(y))
        self.prior, self.cnt, self.tot = {}, {}, {}
        V = set()
        for c in self.classes:
            self.prior[c] = 0
            self.cnt[c] = Counter()
            self.tot[c] = 0
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


def part_a2(seed=11, ntr=3000, nte=800):
    """镜像识别：NORMAL vs MIRROR"""
    rng = random.Random(seed)

    def build(op, tag_norm, tag_mirr):
        X, y = [], []
        for _ in range(ntr // 2):
            t = gen(rng); X.append(t); y.append(tag_norm)
            X.append(op(t)); y.append(tag_mirr)
        te_X, te_y = [], []
        for _ in range(nte // 2):
            t = gen(rng); te_X.append(t); te_y.append(tag_norm)
            te_X.append(op(t)); te_y.append(tag_mirr)
        return (X, y), (te_X, te_y)

    out = {}
    for opname, op in (("MIRROR(swap)", op_swap), ("CONTROL(换宾语)", op_obj)):
        (Xtr, ytr), (Xte, yte) = build(op, "NORMAL", "MIRROR")
        row = {"op": opname}
        for rname, fn in (("BOW", f_bow), ("POS", f_pos)):
            clf = MNB()
            clf.fit([fn(t) for t in Xtr], ytr)
            pred = [clf.predict(fn(t)) for t in Xte]
            acc = sum(1 for p, g in zip(pred, yte) if p == g) / len(yte)
            # 判别度 = P(判MIRROR | 真MIRROR) - P(判MIRROR | 真NORMAL)
            tp = sum(1 for p, g in zip(pred, yte) if p == "MIRROR" and g == "MIRROR")
            fp = sum(1 for p, g in zip(pred, yte) if p == "MIRROR" and g == "NORMAL")
            nm = sum(1 for g in yte if g == "MIRROR")
            nn = sum(1 for g in yte if g == "NORMAL")
            tpr = tp / nm
            fpr = fp / nn
            row[rname] = {"acc": acc, "tpr": tpr, "fpr": fpr,
                          "disc": tpr - fpr,
                          "escape": 1.0 - tpr}   # 镜像逃逸率
        out[opname] = row
    return out


def run_frank(mode, gamma, pL0, gens=25, pool_n=1200, batch=600,
              noise=True, seed=1):
    rng = random.Random(seed)
    L, R = pool_n * pL0, pool_n * (1 - pL0)
    hist = []
    for g in range(gens):
        tot = L + R
        pL = L / tot
        if abs(gamma - 1.0) < 1e-9:
            pA = pL
        else:
            a, b = pL ** gamma, (1 - pL) ** gamma
            pA = a / (a + b) if (a + b) > 0 else pL
        newL = sum(1 for _ in range(batch) if rng.random() < pA) if noise \
            else round(batch * pA)
        newR = batch - newL
        if mode == "REPLACE":
            L, R = newL, newR
        else:
            L, R = L + newL, R + newR
        hist.append(L / (L + R) if (L + R) > 0 else float("nan"))
    return hist


def part_c():
    res = {"dose": [], "spontaneous": {}}
    # C1 剂量扫描（确定性，无采样噪声）
    for chi0 in (0.0001, 0.001, 0.01, 0.05, 0.2, 0.5):
        p0 = 0.5 * (1 + chi0)
        for gamma in (1.6, 2.5):
            h = run_frank("REPLACE", gamma, p0, noise=False, seed=5)
            res["dose"].append({"chi0": chi0, "gamma": gamma,
                                "init": h[0], "final": h[-1],
                                "chi_final": 2 * h[-1] - 1})
    # C2 自发破缺：chi0 = 0（pL0 = 0.5），有噪声
    locks = []
    for s in range(40):
        h = run_frank("REPLACE", 2.0, 0.5, noise=True, seed=1000 + s)
        f = h[-1]
        locks.append(1 if (f < 1e-9 or f > 1 - 1e-9) else 0)
        if s == 0:
            res["spontaneous"]["example_hist"] = h
    res["spontaneous"]["n"] = len(locks)
    res["spontaneous"]["locked"] = sum(locks)
    res["spontaneous"]["rate"] = sum(locks) / len(locks)
    # 锁死到哪一端（前 20 个种子的终态符号）
    ends = []
    for s in range(40):
        h = run_frank("REPLACE", 2.0, 0.5, noise=True, seed=1000 + s)
        ends.append("L" if h[-1] > 0.5 else "R")
    res["spontaneous"]["to_L"] = ends.count("L")
    res["spontaneous"]["to_R"] = ends.count("R")
    return res


if __name__ == "__main__":
    print("=" * 70)
    print("exp139b  镜像逃逸 与 自发对称性破缺")
    print("=" * 70)

    A2 = part_a2()
    print("\n--- Part A2  镜像能被看见吗（NORMAL vs MIRROR）---")
    print("  %-16s %-5s %8s %8s %8s %8s %8s" %
          ("operator", "repr", "acc", "TPR", "FPR", "判别度", "逃逸率"))
    for k, r in A2.items():
        for rn in ("BOW", "POS"):
            d = r[rn]
            print("  %-16s %-5s %8.4f %8.4f %8.4f %8.4f %8.4f" %
                  (k, rn, d["acc"], d["tpr"], d["fpr"], d["disc"], d["escape"]))
        print()

    C = part_c()
    print("--- Part C1  剂量扫描（确定性, REPLACE）---")
    print("  %8s %6s %10s %10s %12s" % ("chi0", "gamma", "init", "final", "chi_final"))
    for d in C["dose"]:
        print("  %8.4f %6.1f %10.6f %10.6f %12.6f" %
              (d["chi0"], d["gamma"], d["init"], d["final"], d["chi_final"]))

    print("\n--- Part C2  自发对称性破缺（chi0 = 0, 有噪声, gamma=2.0）---")
    s = C["spontaneous"]
    print("  n=%d  锁死 %d  锁死率 %.3f" % (s["n"], s["locked"], s["rate"]))
    print("  锁死到 L %d 次 / R %d 次" % (s["to_L"], s["to_R"]))
    print("  例: 前 8 代 %s" % [round(x, 4) for x in s["example_hist"][:8]])
    print("      末 4 代 %s" % [round(x, 4) for x in s["example_hist"][-4:]])

    with open("result139b.json", "w") as f:
        json.dump({"A2": A2, "C": C}, f, ensure_ascii=False, indent=1)
    print("\n[saved] result139b.json")
