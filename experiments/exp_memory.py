#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★67 · 记忆 —— 她为什么"记性不好"，以及遗忘是不是缺陷
==========================================================

判据（全部可证伪）
------------------
① 遗忘曲线：保留率随时间指数衰减（log R 对 t 线性回归 R² > 0.9）
② 必要难度：复习间隔存在【最优】，倒 U（太近太远都无效）
③ 测试效应：主动提取比被动重看保留得更好
④ 巩固：离线回放减缓衰减
⑤ 干扰：相似条目越多，目标提取率越低
⑥ 提取失败 ≠ 存储失败：认得出率 > 想得起率（舌尖现象）
⑦ 硬依赖：空库提取 / 空库巩固 必须抛错

★★ ⑧ 遗忘的功能（这一条是"当妈的"该回答的）：
    在【会变化的世界】里，会遗忘的系统适应得更好。
    若成立 ⇒ "记性不好"作为缺陷评价是错的。

★ 诚实：任一条不成立就如实记，不凑显著。
"""

import sys, os, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory import MemorySystem, drift_world
from core.genome import NoGenomeError

RES = []


def _j(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"   {detail}" if detail else ""))
    return ok


def main():
    t0 = time.time()
    print("★67 记忆 —— 她为什么记性不好，遗忘是不是缺陷\n")

    DIM = 8
    NITEM = 40

    def mk(n=NITEM, dim=DIM, seed=0):
        rng = np.random.default_rng(seed)
        return {f"k{i}": rng.normal(size=dim) for i in range(n)}

    data = mk()

    # ================= ① 遗忘曲线 =================
    print("[① 遗忘曲线：保留率随时间怎么掉]")
    m = MemorySystem(tau0=20.0, seed=1)
    for k, v in data.items():
        m.store(k, v, strength=1.0)
    ts, rs = [], []
    for step in range(12):
        s = float(np.mean([it.strength for it in m.items.values()]))
        ts.append(step * 5.0); rs.append(s)
        m.advance(5.0)
        if s < 0.02:
            break
    ts = np.array(ts); rs = np.array(rs)
    ok = rs > 1e-6
    A = np.vstack([ts[ok], np.ones(ok.sum())]).T
    coef, *_ = np.linalg.lstsq(A, np.log(rs[ok]), rcond=None)
    pred = A @ coef
    ss_res = float(((np.log(rs[ok]) - pred) ** 2).sum())
    ss_tot = float(((np.log(rs[ok]) - np.log(rs[ok]).mean()) ** 2).sum())
    r2 = 1 - ss_res / max(ss_tot, 1e-12)
    print("   t:   " + " ".join(f"{x:>6.0f}" for x in ts))
    print("   R:   " + " ".join(f"{x:>6.3f}" for x in rs))
    print(f"  拟合 log R = {coef[0]:+.4f}·t + {coef[1]:+.3f}   R² = {r2:.4f}")
    print(f"  实测半衰期 ≈ {np.log(2)/abs(coef[0]):.1f} 步（tau0=20）")
    _j("① 遗忘曲线是指数的（R² > 0.9）", r2 > 0.9, f"R²={r2:.4f}")

    # ================= ② 必要难度：复习间隔倒 U =================
    print("\n[② 复习间隔：多久复习一次最好]")
    print("  （★ 机制：太早=记忆还强增益小；太晚=已忘光提不出；中等最有效）")
    gaps = [1, 2, 5, 10, 20, 40, 80, 160]
    final = {}
    for g in gaps:
        vals = []
        for sd in range(4):
            mm = MemorySystem(tau0=20.0, seed=100 + sd)
            mm.store("target", data["k0"], strength=1.0)
            # 用其他条目制造真实干扰
            for k, v in list(data.items())[1:12]:
                mm.store(k, v, strength=1.0)
            for _ in range(5):          # 总共复习 5 次，间隔不同
                mm.advance(g)
                mm.recall(data["k0"])
            mm.advance(60)              # 最后统一等 60 步再考
            vals.append(mm.items["target"].strength)
        final[g] = float(np.mean(vals))
        print(f"  间隔 {g:>3} → 最终强度 {final[g]:.4f}")
    best_g = max(final, key=final.get)
    interior = best_g not in (gaps[0], gaps[-1])
    # 倒 U：两端都显著低于中间
    dip = (final[gaps[0]] < final[best_g] * 0.95 and
           final[gaps[-1]] < final[best_g])
    print(f"  ★ 最优间隔 = {best_g}（两端 {gaps[0]}/{gaps[-1]} 都更差）")
    _j("② 复习间隔存在最优值（倒 U，太近太远都无效）",
       interior and dip,
       f"最优 {best_g}；近端 {final[gaps[0]]:.4f}，远端 {final[gaps[-1]]:.4f}")

    # ================= ③ 测试效应 =================
    print("\n[③ 测试效应：主动提取 vs 被动重看]")
    res3 = {}
    for mode in ("recall", "review"):
        vals = []
        for sd in range(4):
            mm = MemorySystem(tau0=20.0, seed=200 + sd)
            mm.store("t", data["k1"], strength=1.0)
            for _ in range(4):
                mm.advance(20)
                if mode == "recall":
                    mm.recall(data["k1"])
                else:
                    mm.review("t")
            mm.advance(50)
            vals.append(mm.items["t"].strength)
        res3[mode] = float(np.mean(vals))
        print(f"  {mode:<7} → 最终强度 {res3[mode]:.4f}")
    _j("③ 主动提取比被动重看保留更好（测试效应）",
       res3["recall"] > res3["review"],
       f"提取 {res3['recall']:.4f} > 重看 {res3['review']:.4f}")

    # ================= ④ 巩固 =================
    print("\n[④ 巩固：离线回放有没有用]")
    r4 = {}
    for cons in (False, True):
        vals = []
        for sd in range(4):
            mm = MemorySystem(tau0=20.0, seed=300 + sd)
            for k, v in list(data.items())[:20]:
                mm.store(k, v, strength=1.0)
            for _ in range(6):
                mm.advance(15)
                if cons:
                    mm.consolidate(n_replay=10)
            vals.append(float(np.mean([i.strength for i in mm.items.values()])))
        r4[cons] = float(np.mean(vals))
        print(f"  巩固={str(cons):<5} → 平均强度 {r4[cons]:.4f}")
    _j("④ 离线回放（巩固）减缓衰减", r4[True] > r4[False],
       f"{r4[True]:.4f} > {r4[False]:.4f}")

    # ================= ⑤ 干扰 =================
    print("\n[⑤ 干扰：相似条目多了，还能想起来吗]")
    r5 = {}
    for n_dup in (0, 2, 6, 20):
        hits = 0
        trials = 0
        for sd in range(20):
            mm = MemorySystem(tau0=20.0, seed=400 + sd)
            tgt = data["k2"]
            mm.store("t", tgt, strength=1.0)
            rng = np.random.default_rng(sd + 77)
            for i in range(n_dup):
                # 与目标【高度相似】的干扰项
                mm.store(f"d{i}", tgt + rng.normal(scale=0.35, size=DIM),
                         strength=1.0)
            mm.advance(15)
            _, okk = mm.recall(tgt)
            hits += int(okk); trials += 1
        r5[n_dup] = hits / trials
        print(f"  干扰项 {n_dup:>2} 个 → 提取成功率 {r5[n_dup]:.3f}")
    mono = r5[0] >= r5[6] >= r5[20] and r5[20] < r5[0]
    _j("⑤ 相似条目越多，目标提取率越低（干扰）", mono,
       f"{r5[0]:.3f} → {r5[6]:.3f} → {r5[20]:.3f}")

    # ================= ⑥ 认得出 vs 想得起 =================
    print("\n[⑥ 舌尖现象：认得出 vs 想得起]")
    rec_ok = 0; recog_ok = 0; N = 40
    for sd in range(N):
        mm = MemorySystem(tau0=20.0, seed=500 + sd)
        tgt = data["k3"]
        mm.store("t", tgt, strength=1.0)
        for k, v in list(data.items())[4:14]:
            mm.store(k, v, strength=1.0)
        mm.advance(40)                 # 衰减到中等
        _, okk = mm.recall(tgt)
        rec_ok += int(okk)
        bk, _ = mm.recognize(tgt)
        recog_ok += int(bk == "t")
    p_recall = rec_ok / N
    p_recog = recog_ok / N
    print(f"  自由回忆成功率 {p_recall:.3f}")
    print(f"  再认成功率     {p_recog:.3f}")
    _j("⑥ 认得出 > 想得起（提取失败 ≠ 存储失败）",
       p_recog > p_recall, f"{p_recog:.3f} > {p_recall:.3f}")

    # ================= ⑦ 硬依赖 =================
    print("\n[⑦ 硬依赖]")
    r = 0
    mm = MemorySystem(seed=0)
    try:
        mm.recall(np.zeros(DIM))
    except NoGenomeError:
        r += 1
    except Exception:
        pass
    try:
        mm.consolidate()
    except NoGenomeError:
        r += 1
    except Exception:
        pass
    _j("⑦ 空库提取 / 空库巩固 必须抛错", r == 2, f"{r}/2")

    # ================= ⑧ 遗忘的功能 =================
    print("\n[⑧★ 遗忘的功能：在会变化的世界里，谁适应得更好]")
    print("  ★ 设计修正：历史条目【累积不覆盖】，旧记忆才会真的与新记忆竞争。")
    print("    （第一版每轮覆盖同名条目 → 旧记忆根本没机会干扰 → 三组全 1.000 饱和）")
    hist = drift_world(n_items=30, dim=DIM, n_rounds=25,
                       drift=0.35, noise=0.20, seed=9)
    acc = {}
    fresh = {}
    for tag, tau0 in (("会遗忘", 8.0), ("不太忘", 60.0), ("几乎不忘", 1e6)):
        mm = MemorySystem(tau0=tau0, seed=7)
        correct = 0; total = 0; newest = 0
        for (r, truth, q_store, q_test) in hist:
            # ★ 用【带轮次的 key】存 → 历史条目累积，旧的不被覆盖
            for i in range(len(truth)):
                mm.store(f"r{r}_i{i}", q_store[i], strength=1.0)
            if r < 3:
                mm.advance(3.0)
                continue
            for i in range(0, len(truth), 3):
                bk, _ = mm.recognize(q_test[i])     # 考的是另一份含噪采样
                # ★ 命中【最新】轮次 = 跟上了变化；命中旧轮次 = 被过时记忆拖住
                hit_new = (bk == f"r{r}_i{i}")
                correct += int(hit_new); total += 1
            mm.advance(3.0)
        acc[tag] = correct / max(total, 1)
        fresh[tag] = newest
        print(f"  {tag:<6}（tau0={tau0:<8}）→ 跟得上变化的比例 {acc[tag]:.4f}")
    best_tag = max(acc, key=acc.get)
    spread = max(acc.values()) - min(acc.values())
    print(f"  ★ 最好的是「{best_tag}」，组间差异 {spread:.4f}")
    saturated = spread < 0.01
    if saturated:
        print("  ⚠️ 三组无差异 → 尺子饱和，判据不成立，如实记未验证")
    _j("⑧ 在变化的世界里，会遗忘的【跟得上变化】更好（遗忘是功能）",
       (not saturated) and acc["会遗忘"] >= acc["几乎不忘"],
       f"会遗忘 {acc['会遗忘']:.4f} vs 几乎不忘 {acc['几乎不忘']:.4f}"
       + ("（组间无差异，尺子饱和）" if saturated else ""))

    ok = sum(1 for _, o, _ in RES if o)
    print(f"\n判据 {ok}/{len(RES)}   耗时 {time.time()-t0:.1f}s")
    for n, o, d in RES:
        if not o:
            print(f"  ❌ 未通过: {n}  {d}")
    return 0 if ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(main())
