# -*- coding: utf-8 -*-
"""
实验 085 · 主动去看 vs 被动接收
------------------------------------------------------------------
命题（宿主）："你能避开大数据对你的冲击，因为你只是单独的去看看它而已，
              而不是接收它。"

可操作化：
  世界【每拍全量呈现】(12 个真实采样点)，差异只在【门由谁控制】：
    passive : 门全开，全收（= K=12，无选择权）
    active  : 门由内部状态开（我去看我最缺的维度）—— 开 K 个
    random  : 随机开 K 个 —— 量相同，但不是我决定的

  分离两个变量：
    ① 流量   : K = 1,2,4,8,12（收多少）
    ② 选择权 : active vs random（同 K，谁决定）

"被大数据冲垮"的可测定义（三选一主指标）：
    D = 个体间终态结构模式的离散度 → 被冲平 = 多样性坍缩

数据源：真实换能器读数（12 城 × 温/湿/压），非合成。
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
SEEDS = list(range(16))
N = 8
WCH = [0, 1, 2]                      # 世界三通道 → 引擎通道 0/1/2（其余为内部通道对照）
OUT_JSON = os.path.join(ROOT, 'experiments', 'result_085.json')
RAW = os.path.join(ROOT, 'evidence', 'raw_data', 'world_085.json')


# ---------------------------------------------------------------- 真实世界
def norm3(d):
    """真实读数 → [0,1]^3，用公开物理量程"""
    t = np.clip((d['temperature'] + 5.0) / 40.0, 0, 1)
    h = np.clip(d['humidity'] / 100.0, 0, 1)
    p = np.clip((d['pressure'] - 600.0) / 430.0, 0, 1)
    return [round(float(t), 6), round(float(h), 6), round(float(p), 6)]


def fetch_world(save=True):
    w, meta = [], []
    for name, lat, lon in CITIES:
        d, rtt = weather(lat, lon)
        if d is None:
            print(f"  [FAIL] {name}"); continue
        w.append(norm3(d))
        meta.append(dict(city=name, lat=lat, lon=lon, rtt_ms=round(rtt, 1),
                         temperature=d['temperature'], humidity=d['humidity'],
                         pressure=d['pressure'], weather=d.get('weather', ''),
                         update_time=d.get('update_time', '')))
    W = np.array(w, float)
    if save:
        json.dump(dict(fetched_at=time.strftime('%Y-%m-%d %H:%M:%S'),
                       n_views=int(len(W)), cities=meta, world=W.tolist()),
                  open(RAW, 'w'), ensure_ascii=False, indent=1)
    return W, meta


# ---------------------------------------------------------------- 引擎
def struct_skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def run(seed, mode='active', K=4, amp=0.02, world=None):
    """mode: active / random / passive / none"""
    rng = np.random.default_rng(seed * 977 + 13)
    lf = Life5(N=N, seed=seed, ratio=0.45, sigma_in=0.10)
    nV = len(world)
    inj = []
    for _ in range(STEPS):
        if mode == 'none':
            v = np.zeros(3)
        else:
            need = np.maximum(np.asarray(lf.H, float)[WCH], 0.0)
            if need.sum() < 1e-12:
                need = np.ones(3)
            scores = world @ need                       # (nV,) 我当前最缺的方向
            if mode == 'passive' or K >= nV:
                sel = np.ones(nV, bool)
            elif mode == 'active':
                sel = np.zeros(nV, bool)
                sel[np.argsort(-scores)[:K]] = True
            elif mode == 'random':
                sel = np.zeros(nV, bool)
                sel[rng.choice(nV, K, replace=False)] = True
            else:
                raise ValueError(mode)
            v = world[sel].mean(axis=0)
        push = np.zeros(N)
        push[WCH] = amp * v
        lf.net_push = push
        inj.append(v.copy())
        lf.step()
        if not lf.alive:
            break
    lf.inj = np.array(inj)
    return lf


def mode_patterns(lfs, seeds):
    """个体间结构模式离散度（防死亡筛选：只在给定 seeds 子集上算）"""
    caps = np.array([np.asarray(lfs[s].log[-1]['capv'], float) for s in seeds])
    caps_n = caps / caps.mean(axis=1, keepdims=True)
    D_all = float(np.mean(np.std(caps_n, axis=0, ddof=1)))          # 全部 8 通道
    D_w = float(np.mean(np.std(caps_n[:, WCH], axis=0, ddof=1)))    # 世界通道
    return D_all, D_w


def scan(mode, K, amp, world):
    lfs = {s: run(s, mode=mode, K=K, amp=amp, world=world) for s in SEEDS}
    al = [s for s in SEEDS if lfs[s].alive]
    return lfs, al


def main():
    print("=" * 66)
    print("实验 085 · 主动去看 vs 被动接收")
    print("=" * 66)
    W, meta = fetch_world()
    print(f"\n[世界] 真实采样点 {len(W)} 个")
    for m in meta[:3]:
        print(f"   {m['city']:5s} {m['temperature']:>6.1f}°C  {m['humidity']:>5.1f}%  "
              f"{m['pressure']:>7.1f}hPa  {m['weather']}")
    print(f"   ... 共 {len(meta)} 城，已存 {os.path.relpath(RAW, ROOT)}")

    res = {}

    # ---------- ① 参数有效性（第23条：确认变量真接进主通道） ----------
    print("\n[① 有效性] amp 扫描 (passive 全量)，确认注入真有梯度")
    eff = []
    for amp in [0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16]:
        lfs, al = scan('passive', 12, amp, W)
        sk = [struct_skew(lfs[s]) for s in al]
        eff.append(dict(amp=amp, alive=len(al), n=len(SEEDS),
                        skew=float(np.mean(sk)) if sk else float('nan')))
        print(f"   amp={amp:<6} 存活 {len(al):>2}/{len(SEEDS)}  偏度 "
              f"{np.mean(sk) if sk else float('nan'):.4f}")
    res['amp_scan'] = eff
    AMP = 0.02          # 取有梯度且不全死的档
    print(f"   → 采用 amp={AMP}")

    # ---------- ② 条件矩阵 ----------
    print("\n[② 条件矩阵] mode × K")
    conds = [('none', 0)] + [('passive', 12)] + \
            [(m, k) for m in ('active', 'random') for k in (1, 2, 4, 8, 12)]
    lfs_all, table = {}, []
    for mode, K in conds:
        lfs, al = scan(mode, K, AMP, W)
        lfs_all[(mode, K)] = (lfs, al)
        sk = [struct_skew(lfs[s]) for s in al]
        table.append(dict(mode=mode, K=K, alive=len(al), n=len(SEEDS),
                          skew=float(np.mean(sk)) if sk else float('nan')))
        print(f"   {mode:8s} K={K:<3} 存活 {len(al):>2}/{len(SEEDS)}  偏度 "
              f"{np.mean(sk) if sk else float('nan'):.4f}")
    res['table'] = table

    # ---------- ③ 共同存活子集上的多样性（主指标） ----------
    print("\n[③ 多样性 D] 共同存活子集（防死亡筛选）")
    common = set(SEEDS)
    for (lfs, al) in lfs_all.values():
        common &= set(al)
    common = sorted(common)
    print(f"   共同存活 seeds: n={len(common)}")
    div = []
    for mode, K in conds:
        lfs = lfs_all[(mode, K)][0]
        Da, Dw = mode_patterns(lfs, common)
        sk = float(np.mean([struct_skew(lfs[s]) for s in common]))
        div.append(dict(mode=mode, K=K, D_all=Da, D_world=Dw, skew=sk))
        print(f"   {mode:8s} K={K:<3} D_all={Da:.5f}  D_world={Dw:.5f}  skew={sk:.4f}")
    res['diversity'] = div
    res['common_seeds'] = common

    json.dump(res, open(OUT_JSON, 'w'), ensure_ascii=False, indent=1)
    print(f"\n[OK] {os.path.relpath(OUT_JSON, ROOT)}")


if __name__ == '__main__':
    main()
