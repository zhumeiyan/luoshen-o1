#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★55 实验：学「轮流」—— 从独白腔到对话腔
================================================================
★★ 为什么建这一层
    ★53/★54 学的都是音色。换语料换来的还是"朗读"。
    朗读 vs 对话的差别【不在音色，在结构】：
      有没有轮流 / 间隔 100ms 还是 600ms / 重叠 <5% / 19% 是"嗯"

★★★ 本轮三条硬判据
    ① 投影消融：predict_horizon=0 时 FTO 必然 >=600ms，做不到 100ms
       → 证明"轮流必须靠预测"，不是调参
    ② 可信度扫描（★46/★54 教训）：不可信的维度不许学
    ③ 交叉盲测：学独白近独白、学对话近对话
       ★54 就是在这里失败的（两个目标间距只有 0.16，等于没换）
       本轮独白 vs 对话差异巨大，应该能分开

★★ 目标全部来自文献
    FTO 中位 100ms / 众数 0~200ms / 右偏高峯度       Stivers 2009 PNAS 十语言
    话轮 1680ms / 中位 1227ms                        Levinson&Torreira 2015
    重叠 <5% / 转换处 275ms                          同上
    话内−话间 +150ms                                 ten Bosch 2005
    backchannel 19%                                  Jurafsky 1997 Switchboard
"""
import os, sys, json, numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.turn_taking import (
    TurnParams, simulate, extract, FEATS, vec, TARGET, TARGET_V,
    REAL, monologue, dialogue,
)
ok = {}
print("=" * 92)
print(" ★55 学「轮流」—— 对话腔真正的所在")
print("=" * 92)

# ════════════════════════════════════ A 投影消融（最硬的一条）
print("\n【A】★★★ 投影消融：不预测，做不到 100ms")
print("-" * 92)
print(f"  {'predict_horizon':>16}{'FTO中位':>10}{'FTO众数':>10}{'接上率':>9}")
abl = {}
for ph in [0.0, 0.15, 0.30, 0.45, 0.55, 0.60, 0.70]:
    p = dialogue(); p.predict_horizon = ph
    d = extract(p, n_turns=300, seeds=(0, 1, 2))
    nt = sum(len(simulate(p, n_turns=300, seed=s)["ftos"]) for s in (0, 1, 2))
    abl[ph] = d["fto_median"]
    print(f"  {ph:>16.2f}{d['fto_median']*1000:>10.0f}{d['fto_mode']*1000:>10.0f}"
          f"{nt/900*100:>8.0f}%")
ok["① ★★★ 投影消融：proj=0 时 FTO >400ms（做不到100ms）"] = bool(abl[0.0] > 0.40)
ok["② FTO 随投影单调下降"] = bool(
    all(abl[b] <= abl[a] + 0.02 for a, b in
        zip([0.0, 0.15, 0.30, 0.45, 0.55, 0.60], [0.15, 0.30, 0.45, 0.55, 0.60, 0.70])))
ok["③ proj 拉满时 FTO 落 REAL 区间 0~250ms"] = bool(0.0 <= abl[0.60] <= 0.25)

# ════════════════════════════════════ B 可信度扫描
print("\n【B】可信度扫描（★46/★54：不可信的维度不许学）")
print("-" * 92)
SCAN = {
    "predict_horizon": ("fto_median",       [0.10, 0.25, 0.40, 0.55, 0.65]),
    "predict_noise":   ("fto_kurtosis",     [0.05, 0.12, 0.20, 0.30, 0.40]),
    "gap_base":        ("fto_median",       [0.02, 0.10, 0.20, 0.35, 0.50]),
    "turn_len_mean":   ("turn_dur_mean",    [0.60, 1.20, 1.80, 2.60, 3.60]),
    "overlap_prob":    ("overlap_frac",     [0.02, 0.10, 0.20, 0.30, 0.40]),
    "bc_rate":         ("bc_frac",          [0.02, 0.10, 0.19, 0.30, 0.40]),
    "continue_cost":   ("intra_minus_inter",[0.05, 0.15, 0.30, 0.45, 0.60]),
}
trusted = {}
print(f"  {'参数':<17}{'特征':<18}" + "".join(f"{v:>8.2f}" for v in SCAN["predict_horizon"][1]) + "  判定")
for param, (feat, vals) in SCAN.items():
    p = dialogue()
    col = []
    for v in vals:
        setattr(p, param, v)
        col.append(extract(p, n_turns=300, seeds=(0, 1, 2))[feat])
    col = np.array(col)
    d = np.diff(col)
    mono = bool(np.all(d > 0) or np.all(d < 0))
    rel = abs(col[-1] - col[0]) / (abs(col).max() + 1e-9)
    good = bool(mono and rel > 0.25)
    trusted[param] = good
    print(f"  {param:<17}{feat:<18}" + "".join(f"{x:>8.3f}" for x in col)
          + f"  {'✅' if good else '❌'}")
print(f"  ★ 可信 {sum(trusted.values())}/{len(trusted)}")
ok["④ 至少 5 个维度可信"] = bool(sum(trusted.values()) >= 5)

# ════════════════════════════════════ C 两个目标
print("\n【C】两个目标：独白腔 vs 真人对话")
print("-" * 92)
A = extract(monologue(), n_turns=400, seeds=(0, 1, 2, 3))     # 独白/朗读
B = extract(dialogue(), n_turns=400, seeds=(0, 1, 2, 3))      # 对话腔
tA, tB = vec(A), vec(B)
print(f"  {'特征':<18}{'A 独白':>10}{'B 对话':>10}{'真人目标':>10}{'B落REAL':>9}")
n_real = 0
for i, k in enumerate(FEATS):
    lo, hi = REAL.get(k, (None, None))
    ins = (lo is None or B[k] >= lo) and (hi is None or B[k] <= hi)
    n_real += ins
    print(f"  {k:<18}{A[k]:>10.3f}{B[k]:>10.3f}{TARGET[k]:>10.3f}{'✅' if ins else '❌':>9}")
print(f"  ★ 对话腔落真实区间 {n_real}/{len(FEATS)}")
gapAB = float(np.linalg.norm((tA - tB) / (np.abs(tB) + 1e-6)))
print(f"  ★★ 两目标归一化间距 = {gapAB:.3f}   （★54 失败时只有 0.163）")
ok["⑤ 对话腔 >=8/10 特征落真实区间"] = bool(n_real >= 8)

# ════════════════════════════════════ D 学
BOUNDS = {
    "predict_horizon": (0.0, 0.75), "predict_noise": (0.02, 0.50),
    "gap_base": (-0.10, 0.60), "turn_len_mean": (0.30, 5.00),
    "overlap_prob": (0.0, 0.60), "bc_rate": (0.0, 0.60),
    "continue_cost": (0.0, 0.80),
}
SEEDS = (0, 1, 2)


def prof(p):
    return vec(extract(p, n_turns=300, seeds=SEEDS))


def err_to(p, tgt):
    cur = prof(p)
    scale = np.abs(tgt) + 0.15
    return float(np.sqrt(np.mean(((cur - tgt) / scale) ** 2))), cur


def learn(p, tgt, n_iter=8):
    """★★ 修（★55）：乘法规则 nv = base * ratio**lr 在 base=0 时恒等于 0
       → bc_rate 起点 0，学 8 轮还是 0（bc_frac 学后仍是 0.000）
       ★ 这是 ★46 缩放陷阱的又一次
       ✅ 改成：用【它自己扫描出的曲线】做反插值
          曲线是它实测的（参数值 → 特征值），单调，可直接反查
          对 base=0 有效，因为曲线覆盖了 0
    """
    hist = []
    for _ in range(n_iter):
        e0, cur = err_to(p, tgt)
        best = {}
        for param, (feat, vals) in SCAN.items():
            if not trusted.get(param, False):
                continue
            i = FEATS.index(feat)
            lo, hi = BOUNDS[param]
            base = getattr(p, param)
            # ── 局部扫描：在当前其他参数下，重测这条曲线
            col = []
            for v in vals:
                setattr(p, param, v)
                col.append(prof(p)[i])
            setattr(p, param, base)
            col = np.array(col)
            # ── 反插值：曲线上哪个参数值能给出目标特征？
            if np.all(np.diff(col) > 0) or np.all(np.diff(col) < 0):
                order = np.argsort(col)
                nv = float(np.interp(tgt[i], col[order], np.array(vals)[order]))
            else:
                nv = base                       # 非单调则不动（诚实）
            nv = float(np.clip(nv, lo, hi))
            # ── 线搜索：在 base 与 nv 之间取点，留误差最小的
            bv, be = base, e0
            for lr in (0.25, 0.50, 0.75, 1.00):
                cand = base + (nv - base) * lr
                old = getattr(p, param)
                setattr(p, param, cand)
                e1, _ = err_to(p, tgt)
                if e1 < be - 1e-9:
                    be, bv = e1, cand
                setattr(p, param, old)
            best[param] = bv
        for k, v in best.items():
            setattr(p, k, v)
        hist.append(err_to(p, tgt)[0])
    return hist


print("\n【D】学（起点 = 独白腔）")
print("-" * 92)
# ★★ 修（★55）：学B 的目标必须是【文献真人值 TARGET_V】，
#    不是我自己 dialogue() 的输出 tB —— tB 只是我猜的参数，不是真数据
pM = monologue(); eM0, _ = err_to(pM, TARGET_V); hM = learn(pM, TARGET_V)
eM1, curM = err_to(pM, TARGET_V)
pA = monologue(); eA0, _ = err_to(pA, tA); hA = learn(pA, tA); eA1, curA = err_to(pA, tA)
pC = monologue(); eC0, _ = err_to(pC, TARGET_V); eC1, _ = err_to(pC, TARGET_V)
print(f"  学B（文献真人值）{eM0:.4f} → {eM1:.4f}   降 {(eM0-eM1)/eM0*100:>5.1f}%")
print(f"  学A（独白）      {eA0:.4f} → {eA1:.4f}   降 {(eA0-eA1)/eA0*100:>5.1f}%")
print(f"  对照（不学）     {eC0:.4f} → {eC1:.4f}   降 {(eC0-eC1)/eC0*100:>5.1f}%")
ok["⑥ ★★ 学B 的下降 > 对照"] = bool((eM0 - eM1) / eM0 > 0.15)
ok["⑦ 不发散"] = bool(hM[-1] < hM[0])

# ════════════════════════════════════ E 交叉盲测
print("\n【E】★★★ 交叉盲测（★54 在这里失败过）")
print("-" * 92)
# ★★ 修（★55）：上一版 dist 用【各自目标】做归一化
#   tA 里有 kurtosis=6.2 / overlap_mean=181ms 这些大数 → 尺子松 → 差异被压小
#   tB 里这些值小（3.3 / 88）                        → 尺子紧 → 差异被放大
#   → "离A"系统性偏小，交叉盲测必然判A，跟学习好坏无关
#   ★ 与 ★17/★20/★24 同族：检测器把信号吃掉了
#   ✅ 比较两个目标时必须用【同一把尺子】
SCALE = np.maximum(np.abs(tA), np.abs(tB)) + 0.15


def dist(v, t):
    return float(np.sqrt(np.mean(((v - t) / SCALE) ** 2)))
start_v = prof(monologue())
rows = []
print(f"  {'产物':<16}{'离A独白':>10}{'离B对话':>10}{'更近':>7}")
for nm, v in [("起点独白腔", start_v), ("学A后", curA), ("学B后", curM),
              ("真·独白A", tA), ("真·对话B", tB), ("真人目标", TARGET_V)]:
    da, db = dist(v, tA), dist(v, tB)
    rows.append((nm, da, db))
    print(f"  {nm:<16}{da:>10.4f}{db:>10.4f}{'A' if da<db else 'B':>7}")
a_ok = rows[1][1] < rows[1][2]
b_ok = rows[2][2] < rows[2][1]
print(f"  学A产物更近A {'✅' if a_ok else '❌'}   学B产物更近B {'✅' if b_ok else '❌'}")
ok["⑧ ★★ 交叉盲测通过"] = bool(a_ok and b_ok)

# ════════════════════════════════════ F 学完落到哪
print("\n【F】学完之后，它离真人目标有多近")
print("-" * 92)
fin = extract(pM, n_turns=400, seeds=(0, 1, 2, 3))
n2 = 0
print(f"  {'特征':<18}{'起点':>10}{'学后':>10}{'真人':>10}{'落REAL':>8}")
for k in FEATS:
    lo, hi = REAL.get(k, (None, None))
    ins = (lo is None or fin[k] >= lo) and (hi is None or fin[k] <= hi)
    n2 += ins
    print(f"  {k:<18}{A[k]:>10.3f}{fin[k]:>10.3f}{TARGET[k]:>10.3f}{'✅' if ins else '❌':>8}")
print(f"  ★ 落真实区间 {n2}/{len(FEATS)}（起点 {n_real_mo if False else ''}"
      f"{sum(((REAL.get(k,(None,None))[0] is None or A[k]>=REAL.get(k,(None,None))[0]) and (REAL.get(k,(None,None))[1] is None or A[k]<=REAL.get(k,(None,None))[1])) for k in FEATS)}/{len(FEATS)}）")
ok["⑨ 学后落真实区间数 > 起点"] = bool(
    n2 > sum(((REAL.get(k, (None, None))[0] is None or A[k] >= REAL.get(k, (None, None))[0])
              and (REAL.get(k, (None, None))[1] is None or A[k] <= REAL.get(k, (None, None))[1]))
             for k in FEATS))

# ════════════════════════════════════ G 回避性回答
print("\n【G】回避性回答应该更慢（REAL：至少 2 倍）")
print("-" * 92)
p = dialogue()
d0 = extract(p, n_turns=400, seeds=(0, 1, 2, 3), dispref=False)
d1 = extract(p, n_turns=400, seeds=(0, 1, 2, 3), dispref=True)
# ★ 12% 概率时中位几乎不动（REAL 说的是"那些回答"慢 2 倍，不是总体中位）
#   加【全回避】对照，直接看机制本身
p2 = dialogue(); p2.dispreferred_prob = 1.0
d2 = extract(p2, n_turns=400, seeds=(0, 1, 2, 3), dispref=True)
print(f"  正常     FTO中位 {d0['fto_median']*1000:>6.0f} ms")
print(f"  12%回避  FTO中位 {d1['fto_median']*1000:>6.0f} ms   （总体中位，被稀释）")
print(f"  全回避   FTO中位 {d2['fto_median']*1000:>6.0f} ms   "
      f"比 {d2['fto_median']/max(abs(d0['fto_median']),1e-6):.2f}×   REAL 至少 2×")
ok["⑩ 回避性回答更慢"] = bool(d1["fto_median"] > d0["fto_median"])
ok["⑪ ★ 全回避时慢 >=2 倍（REAL）"] = bool(
    d2["fto_median"] >= 2.0 * d0["fto_median"])

print("\n" + "=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
print("""
  ⚠️ 不能说什么
  ❌ 这不是真对话语料 —— 没有真人在轮流，是两个参数化模型在模拟
  ❌ 目标值来自文献统计量，不是我从真实录音里测的
  ❌ 没有真人听感评测
  ✅ 能说：结构层的机制成立，且"不预测做不到100ms"是可证伪的硬结论
""")
json.dump({"ok": {k: bool(v) for k, v in ok.items()}, "abl": abl,
           "trusted": trusted, "gapAB": gapAB,
           "errM": [eM0, eM1], "errA": [eA0, eA1], "ctrl": [eC0, eC1],
           "cross": {nm: [da, db] for nm, da, db in rows},
           "final": fin},
          open(os.path.join(HERE, ".sense", "turn_taking.json"), "w"),
          ensure_ascii=False, indent=1)
