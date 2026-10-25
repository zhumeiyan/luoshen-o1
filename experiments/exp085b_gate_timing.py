# -*- coding: utf-8 -*-
"""
实验 085b · 主动去看 vs 被动接收（重写）
------------------------------------------------------------------
085 的设计被证伪：世界视野经取均值后，active 与 random 逐位相同
（D_world 全 ~0.028），说明"选哪个视野"不构成有效变量。

重写的核心：信息【内容】完全相同（每拍注入同一个真实世界均值向量），
唯一变量是【门在什么时候开】——也就是说，差异不在"看什么"，在"谁决定看不看"。

  passive : 每拍全开（强制接收）
  active  : 开门概率 ∝ 我当前的内部需求（按需去看），总开门数与 random 匹配
  random  : 恒定概率开门（同样多，但不是我决定的）
  none    : 无感官基线

剂量维度：目标开门率 p ∈ {0.25, 0.5, 0.75, 1.0}
  p=1.0 时三者应当汇合 → 一致性检查（sanity）
"""
import json, os, sys, time
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'core'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from core.life5 import Life5
from sense_array_probe import CITIES, weather

STEPS = 600
SEEDS = list(range(32))          # 放大 seed 数，保证共同存活子集够大
N = 8
WCH = [0, 1, 2]
AMP = 0.005                      # 由 085 有效性扫描选定：有梯度且不全死
RAW = os.path.join(ROOT, 'evidence', 'raw_data', 'world_085b.json')
OUT = os.path.join(ROOT, 'experiments', 'result_085b.json')


def fetch_world():
    """真实换能器读数；量程按【实测极差】自适应（感受器适应）"""
    rows = []
    for name, lat, lon in CITIES:
        for attempt in range(2):
            d, rtt = weather(lat, lon)
            if d: break
        if not d:
            print(f"   [FAIL] {name}"); continue
        rows.append(dict(city=name, lat=lat, lon=lon, rtt_ms=round(rtt, 1),
                         temperature=d['temperature'], humidity=d['humidity'],
                         pressure=d['pressure'], weather=d.get('weather', ''),
                         update_time=d.get('update_time', '')))
    M = np.array([[r['temperature'], r['humidity'], r['pressure']] for r in rows], float)
    lo, hi = M.min(axis=0), M.max(axis=0)
    span = np.where(hi - lo < 1e-9, 1.0, hi - lo)
    W = (M - lo) / span                     # 每维 → [0,1]（自适应量程）
    json.dump(dict(fetched_at=time.strftime('%Y-%m-%d %H:%M:%S'), n_views=len(rows),
                   lo=lo.tolist(), hi=hi.tolist(), cities=rows, world=W.tolist()),
              open(RAW, 'w'), ensure_ascii=False, indent=1)
    return W, rows


def struct_skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def run(seed, mode, p, world_vec, amp=AMP):
    rng = np.random.default_rng(seed * 977 + 13)
    lf = Life5(N=N, seed=seed, ratio=0.45, sigma_in=0.10)
    needs, opens = [], []
    for _ in range(STEPS):
        need = float(np.mean(np.maximum(np.asarray(lf.H, float)[WCH], 0.0)))
        needs.append(need)
        if mode == 'none':
            o = 0
        elif mode == 'passive' or p >= 1.0:
            o = 1
        else:
            # 历史自适应：把 need 映射到 [0,1]，再缩放到目标开门率
            h = needs[:-1] or [need]
            q = (need - min(h)) / max(max(h) - min(h), 1e-12)
            pr = float(np.clip(2.0 * p * q, 0.0, 1.0)) if mode == 'active' else float(p)
            o = 1 if rng.random() < pr else 0
        opens.append(o)
        push = np.zeros(N)
        push[WCH] = amp * world_vec * o
        lf.net_push = push
        lf.step()
        if not lf.alive:
            break
    lf.needs = np.array(needs); lf.opens = np.array(opens)
    return lf


def main():
    print("=" * 68)
    print("实验 085b · 主动去看 vs 被动接收（门在什么时候开）")
    print("=" * 68)
    W, rows = fetch_world()
    print(f"\n[世界] 真实采样点 {len(rows)} 个，实测极差自适应归一化")
    for r in rows[:4]:
        print(f"   {r['city']:5s} {r['temperature']:>6.1f}°C {r['humidity']:>5.1f}% "
              f"{r['pressure']:>7.1f}hPa {r['weather']}")
    wv = W.mean(axis=0)
    print(f"   世界均值向量(真实) = {np.round(wv,4)}")

    conds = [('none', 0.0), ('passive', 1.0)] + \
            [(m, p) for m in ('active', 'random') for p in (0.25, 0.5, 0.75, 1.0)]
    lfs_all, tab = {}, []
    print(f"\n[条件矩阵] amp={AMP}, seeds={len(SEEDS)}")
    for mode, p in conds:
        L = {s: run(s, mode, p, wv) for s in SEEDS}
        al = [s for s in SEEDS if L[s].alive]
        lfs_all[(mode, p)] = (L, al)
        op = float(np.mean([L[s].opens.mean() for s in SEEDS]))
        sk = [struct_skew(L[s]) for s in al]
        tab.append(dict(mode=mode, p=p, alive=len(al), n=len(SEEDS),
                        open_rate=round(op, 4),
                        skew=float(np.mean(sk)) if sk else float('nan')))
        print(f"   {mode:8s} p={p:<5} 存活 {len(al):>2}/{len(SEEDS)}  "
              f"实际开门率 {op:.3f}  偏度 {np.mean(sk) if sk else float('nan'):.4f}")

    # 操纵检查：active 的开门是否真的与内部需求相关（否则变量没接进去）
    print("\n[操纵检查] 开门 与 内部需求 的相关（active 应显著 > random）")
    mc = []
    for mode, p in conds:
        if mode in ('none', 'passive'): continue
        rs = []
        for s in SEEDS:
            L = lfs_all[(mode, p)][0][s]
            o, n = L.opens, L.needs
            if o.std() < 1e-9: continue
            rs.append(float(np.corrcoef(o, n[:len(o)])[0, 1]))
        mc.append(dict(mode=mode, p=p, r=float(np.mean(rs)) if rs else float('nan'),
                       n=len(rs)))
        print(f"   {mode:8s} p={p:<5} r(开门,需求) = {np.mean(rs) if rs else float('nan'):+.4f}")

    common = set(SEEDS)
    for (L, al) in lfs_all.values(): common &= set(al)
    common = sorted(common)
    print(f"\n[多样性 D] 共同存活子集 n={len(common)}")
    div = []
    for mode, p in conds:
        L = lfs_all[(mode, p)][0]
        caps = np.array([np.asarray(L[s].log[-1]['capv'], float) for s in common])
        cn = caps / caps.mean(axis=1, keepdims=True)
        div.append(dict(mode=mode, p=p,
                        D_all=float(np.mean(np.std(cn, axis=0, ddof=1))),
                        D_world=float(np.mean(np.std(cn[:, WCH], axis=0, ddof=1))),
                        skew=float(np.mean([struct_skew(L[s]) for s in common]))))
        d = div[-1]
        print(f"   {mode:8s} p={p:<5} D_all={d['D_all']:.5f}  D_world={d['D_world']:.5f}  "
              f"skew={d['skew']:.4f}")

    json.dump(dict(table=tab, manip=mc, diversity=div, common=common,
                   world_vec=wv.tolist(), n_views=len(rows)),
              open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"\n[OK] {os.path.relpath(OUT, ROOT)}")


if __name__ == '__main__':
    main()
