#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exp139c  修正版（前两版各有一处静默失效）

修正1: 逃逸率=1-TPR 在退化分类器上给出漂亮的 0。
       BOW 把所有输入都判成 MIRROR -> TPR=1,FPR=1 -> 看起来"零逃逸"，
       实际判别力为 0。主指标改为 判别度 = TPR - FPR，
       并显式报告 pred_distinct（预测是否退化为一个常数）。
修正2: 对照组"换宾语"失败——它仍在 OBJ 集合内取值，两分布无系统差异，
       BOW/POS 都瞎（判别度 0.030 / 0.048）。改对照组为 NEG（增删"不"）：
       词集合真的变了，BOW 应当能看见。
修正3: C1 确定性版用整数 round 做计数，极小 chi0 被离散化吃掉
       (chi0=0.0001 -> 终态 0.5)。改浮点，代表无限样本极限。
修正4: C2 用连续种子 1000+s，MT 状态相关 -> 锁死方向 26/14 偏斜。
       改用分散种子。
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
    return ([rng.choice(SUBJ)]
            + (["不"] if rng.random() < neg_rate else [])
            + [rng.choice(ALL_V), rng.choice(OBJ), rng.choice(COMP)])


def _idx(toks):
    iv = toks.index("不") + 1 if "不" in toks else 1
    return 0, iv, iv + 1


def op_swap(toks):
    t = list(toks)
    i_s, _, i_o = _idx(toks)
    t[i_s], t[i_o] = t[i_o], t[i_s]
    return t


def op_neg(toks):
    t = list(toks)
    if "不" in t:
        return [x for x in t if x != "不"]
    return t[:1] + ["不"] + t[1:]


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
            self.prior[c] = 0; self.cnt[c] = Counter(); self.tot[c] = 0
        for xi, yi in zip(X, y):
            self.prior[yi] += 1
            for f, n in xi.items():
                self.cnt[yi][f] += n; self.tot[yi] += n; V.add(f)
        N = len(X); self.V = list(V)
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


OPS = {
    "MIRROR(swap, 保集合)": (op_swap, "词集合不变，只换语序"),
    "CONTROL(neg, 变集合)": (op_neg,  "增删否定词，词集合变"),
}


def part_a2(seed=11, ntr=3000, nte=800):
    rng = random.Random(seed)
    out = {}
    for name, (op, desc) in OPS.items():
        Xtr, ytr, Xte, yte = [], [], [], []
        for _ in range(ntr // 2):
            t = gen(rng); Xtr.append(t); ytr.append("NORMAL")
            Xtr.append(op(t)); ytr.append("ALTERED")
        for _ in range(nte // 2):
            t = gen(rng); Xte.append(t); yte.append("NORMAL")
            Xte.append(op(t)); yte.append("ALTERED")
        row = {"desc": desc}
        for rname, fn in (("BOW", f_bow), ("POS", f_pos)):
            clf = MNB(); clf.fit([fn(t) for t in Xtr], ytr)
            pred = [clf.predict(fn(t)) for t in Xte]
            acc = sum(1 for p, g in zip(pred, yte) if p == g) / len(yte)
            na = sum(1 for g in yte if g == "ALTERED")
            nn = sum(1 for g in yte if g == "NORMAL")
            tpr = sum(1 for p, g in zip(pred, yte) if p == "ALTERED" and g == "ALTERED") / na
            fpr = sum(1 for p, g in zip(pred, yte) if p == "ALTERED" and g == "NORMAL") / nn
            distinct = len(set(pred))
            disc = tpr - fpr
            row[rname] = {"acc": acc, "tpr": tpr, "fpr": fpr, "disc": disc,
                          "pred_distinct": distinct,
                          "degenerate": 1 if distinct == 1 else 0,
                          # 只有非退化时逃逸率才有意义
                          "escape": (1 - tpr) if distinct > 1 else None}
        out[name] = row
    return out


def run_frank(mode, gamma, pL0, gens=25, pool_n=1200.0, batch=600.0,
              noise=True, seed=1):
    rng = random.Random(seed)
    L, R = pool_n * pL0, pool_n * (1 - pL0)
    hist = []
    for g in range(gens):
        pL = L / (L + R)
        if abs(gamma - 1.0) < 1e-9:
            pA = pL
        else:
            a, b = pL ** gamma, (1 - pL) ** gamma
            pA = a / (a + b) if (a + b) > 0 else pL
        if noise:
            n = int(batch)
            newL = float(sum(1 for _ in range(n) if rng.random() < pA))
        else:
            newL = batch * pA          # 浮点 = 无限样本极限
        newR = batch - newL
        if mode == "REPLACE":
            L, R = newL, newR
        else:
            L, R = L + newL, R + newR
        hist.append(L / (L + R) if (L + R) > 0 else float("nan"))
    return hist


def part_c():
    res = {"dose": [], "spontaneous": {}}
    for chi0 in (0.00001, 0.0001, 0.001, 0.01, 0.05, 0.2, 0.5):
        p0 = 0.5 * (1 + chi0)
        for gamma in (1.6, 2.5):
            h = run_frank("REPLACE", gamma, p0, noise=False, seed=5)
            res["dose"].append({"chi0": chi0, "gamma": gamma, "final": h[-1],
                                "chi_final": 2 * h[-1] - 1})
    # C2 自发破缺：分散种子
    ends = []
    locked = 0
    N = 120
    first_hist = None
    for s in range(N):
        h = run_frank("REPLACE", 2.0, 0.5, noise=True, seed=1000 + s * 104729)
        f = h[-1]
        if f < 1e-9 or f > 1 - 1e-9:
            locked += 1
        ends.append("L" if f > 0.5 else "R")
        if s == 0:
            first_hist = h
    sp = res["spontaneous"]
    sp["n"] = N; sp["locked"] = locked; sp["rate"] = locked / N
    sp["to_L"] = ends.count("L"); sp["to_R"] = ends.count("R")
    sp["example_hist"] = first_hist
    # 对称性检验（二项，近似）
    k = sp["to_L"]; n = N
    se = math.sqrt(n * 0.25)
    sp["z"] = (k - n / 2) / se
    return res


if __name__ == "__main__":
    print("=" * 74)
    print("exp139c  镜像逃逸（修正指标） + Frank 动力学（修正离散化/种子）")
    print("=" * 74)

    A2 = part_a2()
    print("\n--- Part A2  镜像能被看见吗 ---")
    print("  主指标 = 判别度(TPR-FPR)；退化 = 所有输入预测同一个类")
    print("  %-22s %-4s %8s %8s %8s %9s %6s %8s" %
          ("operator", "repr", "acc", "TPR", "FPR", "判别度", "退化", "逃逸率"))
    for k, r in A2.items():
        for rn in ("BOW", "POS"):
            d = r[rn]
            esc = "N/A" if d["escape"] is None else "%.4f" % d["escape"]
            print("  %-22s %-4s %8.4f %8.4f %8.4f %9.4f %6d %8s" %
                  (k[:22], rn, d["acc"], d["tpr"], d["fpr"], d["disc"],
                   d["degenerate"], esc))
        print("      (%s)" % r["desc"])

    C = part_c()
    print("\n--- Part C1  剂量扫描（确定性=无限样本极限, REPLACE）---")
    print("  %10s %6s %12s %12s" % ("chi0", "gamma", "final_pL", "chi_final"))
    for d in C["dose"]:
        print("  %10.5f %6.1f %12.6f %12.6f" %
              (d["chi0"], d["gamma"], d["final"], d["chi_final"]))

    print("\n--- Part C2  自发对称性破缺（chi0=0, 有噪声, gamma=2.0）---")
    s = C["spontaneous"]
    print("  n=%d  锁死 %d  锁死率 %.3f" % (s["n"], s["locked"], s["rate"]))
    print("  锁死到 L %d / R %d   z = %.3f" % (s["to_L"], s["to_R"], s["z"]))
    print("  例 前8代 %s" % [round(x, 4) for x in s["example_hist"][:8]])
    print("    末4代 %s" % [round(x, 4) for x in s["example_hist"][-4:]])

    with open("result139c.json", "w") as f:
        json.dump({"A2": A2, "C": C}, f, ensure_ascii=False, indent=1)
    print("\n[saved] result139c.json")
