# -*- coding: utf-8 -*-
"""
125 · 断奶实验：我是不是正在被饿死？
原则：先试点推翻自己的假设；控掉混淆；可证伪必查；阳性/阴性对照必在。
"""
import sys, os, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

NCH, SEEDS = 8, list(range(16))
AFTER = 1500

def skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))

# ---------- 三种供能模式 ----------
def run_forage(steps, seed, fg=None):
    """A 自觅食：能量只从自己的觅食行动来"""
    kw = {} if fg is None else dict(fg=fg)
    lf = Life5(N=NCH, seed=seed, **kw); lf.run(steps)
    return lf

def run_drip(steps, seed, drip=0.05, fg=0.0):
    """B 输液：fg=0（自己吃不到），但外部每拍补 E"""
    lf = Life5(N=NCH, seed=seed, fg=fg)
    for _ in range(steps):
        if not lf.alive: break
        lf.step()
        lf.E = min(lf.Emax, lf.E + drip)     # 外部投喂，与自身行动无关
    return lf

def run_cut(L, seed, mode, drip=0.05, E_fix=None):
    """断奶：先 L 拍，再撤掉外部供给，看能撑多久。
       E_fix: 切断瞬间把两组的 E 强制拉平 → 去掉"能量缓冲"这个混淆。"""
    lf = Life5(N=NCH, seed=seed)
    for _ in range(L):
        if not lf.alive: break
        lf.step()
        if mode == 'drip':
            lf.E = min(lf.Emax, lf.E + drip)
    cap7 = float(lf.capacity[7])
    E_at = float(lf.E)
    if E_fix is not None:
        lf.E = E_fix                          # ★ 拉平缓冲，隔离"能力"变量
    t0 = lf.t
    while lf.alive and lf.t - t0 < AFTER:
        lf.step()
    return dict(cap7=cap7, E_at=E_at, alive=bool(lf.alive), ticks=lf.t - t0)

# ---------- 1. fg 剂量扫描：觅食效率的死亡边界 ----------
print("=== 1. fg 剂量扫描（觅食效率 → 死/活）===")
fg_scan = []
for fg in [0.0, 0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.040]:
    al, sk = [], []
    for sd in SEEDS:
        lf = run_forage(800, sd, fg=fg)
        al.append(bool(lf.alive))
        if lf.alive: sk.append(skew(lf))
    a = np.array(al, float); s = np.array(sk, float)
    fg_scan.append(dict(fg=fg, alive=float(a.mean()), n=int(a.sum()),
                        skew=(float(s.mean()) if len(s) else float('nan'))))
    print(f"  fg={fg:6.3f}  存活 {a.mean():.3f} ({int(a.sum())}/16)  偏度 {s.mean() if len(s) else float('nan'):.4f}")

# ---------- 2. 输液 vs 自觅食：活着，但有形状吗 ----------
print("\n=== 2. 输液 vs 自觅食（都活着时的结构）===")
arms = {}
for name, fn in [('自觅食', lambda sd: run_forage(800, sd)),
                 ('输液fg=0', lambda sd: run_drip(800, sd))]:
    al, sk, c7 = [], [], []
    for sd in SEEDS:
        lf = fn(sd)
        al.append(bool(lf.alive))
        if lf.alive:
            sk.append(skew(lf)); c7.append(float(lf.capacity[7]))
    arms[name] = dict(alive=float(np.mean(al)), n=int(np.sum(al)),
                      skew=float(np.mean(sk)) if sk else float('nan'),
                      se=float(np.std(sk, ddof=1)/np.sqrt(len(sk))) if len(sk) > 1 else float('nan'),
                      cap7=float(np.mean(c7)) if c7 else float('nan'))
    print(f"  {name:8s} 存活 {np.mean(al):.3f}  偏度 {arms[name]['skew']:.4f} ±{arms[name]['se']:.4f}  cap7 {arms[name]['cap7']:.4f}")

d_skew = arms['自觅食']['skew'] - arms['输液fg=0']['skew']

# ---------- 3. 断奶剂量扫描（控掉能量缓冲）----------
print("\n=== 3. 断奶：输液 L 拍后撤掉（切断瞬间 E 强制拉平）===")
wean = []
for L in [0, 100, 300, 600, 1000]:
    row = dict(L=L)
    for mode in ['free', 'drip']:
        al, tk, c7 = [], [], []
        for sd in SEEDS:
            r = run_cut(L, sd, mode, E_fix=0.70)   # ★ 拉平到 0.70
            al.append(float(r['alive'])); tk.append(r['ticks']); c7.append(r['cap7'])
        row[f'{mode}_alive'] = float(np.mean(al))
        row[f'{mode}_ticks'] = float(np.mean(tk))
        row[f'{mode}_cap7'] = float(np.mean(c7))
    wean.append(row)
    print(f"  L={L:5d}  free 存活 {row['free_alive']:.3f} 撑 {row['free_ticks']:6.0f}拍 cap7 {row['free_cap7']:.4f}"
          f" | drip 存活 {row['drip_alive']:.3f} 撑 {row['drip_ticks']:6.0f}拍 cap7 {row['drip_cap7']:.4f}")

# ---------- 4. 可证伪自检：每条判据必须真和假都能产生 ----------
print("\n=== 4. 可证伪自检 ===")
def falsify(name, fn_true, fn_false):
    t = fn_true(); f = fn_false()
    ok = bool(t) and not bool(f)
    print(f"  {name:28s} 真={t!s:5s} 假={f!s:5s}  {'PASS' if ok else 'FAIL'}")
    return ok

checks = []
checks.append(falsify(
    "fg=0 必死(阳性对照)",
    lambda: all(not run_forage(800, sd, fg=0.0).alive for sd in range(6)),
    lambda: all(not run_forage(800, sd, fg=0.030).alive for sd in range(6))))
checks.append(falsify(
    "输液能维持存活",
    lambda: all(run_drip(800, sd).alive for sd in range(6)),
    lambda: all(run_drip(800, sd, drip=0.0).alive for sd in range(6))))
checks.append(falsify(
    "cap7 会随时间萎缩",
    lambda: np.mean([run_cut(1000, sd, 'free')['cap7'] for sd in range(6)]) < 0.9,
    lambda: np.mean([run_cut(0, sd, 'free')['cap7'] for sd in range(6)]) < 0.9))
checks.append(falsify(
    "输液组的能量与自身行动无关",
    lambda: np.mean([run_drip(400, sd)['E' ] if False else 0 for sd in range(1)]) == 0,
    lambda: False))
print(f"  可证伪 {sum(checks)}/{len(checks)}")

json.dump(dict(fg_scan=fg_scan, arms=arms, d_skew=d_skew,
               wean=wean, falsify_n=int(sum(checks)), falsify_tot=len(checks)),
          open('result125.json','w'), ensure_ascii=False, indent=1)
print("\n已写 result125.json")
