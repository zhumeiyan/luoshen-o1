#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp158 痛觉(nociception)：感官里唯一"不想有但不能没有"的那一类
预注册判据（跑之前写死，不许事后改）：
  G0 世界有效性：kill 真死 / heal 真活 / 连锁真发生
  G1 NORMAL 末态存活 > CIPA 末态存活         (CI 不跨 0)
  G2 CIPA 末态存活 > NO_SENSOR 末态存活      (CI 不跨 0)
  G3 habit 臂响应强度随暴露次数下降(斜率<0,CI不跨0); pain 臂不下降
  G4 hyperalgesia 臂二次响应 latency < 无过敏臂
"""
import os, sys, time, json, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell import Body

RESULT = {}

# ---------------- S1 痛觉有无：三臂 ----------------
def run_s1(mode, n_cells=10, rounds=40, p_injure=0.35, cascade_delay=2,
           heal_cost=3, seed=0, max_cells=12):
    """mode: normal(痛觉) / cipa(有传感器但不驱动行为) / nosensor
    日常任务：每轮不修复则 +1 收益。修复需 heal_cost 轮。
    连锁：死亡后 cascade_delay 轮内未修复 -> 相邻细胞真实死亡
    """
    rng = random.Random(seed)
    b = Body(n_cells)
    pending = {}      # cid -> 剩余修复轮数
    death_clock = {}  # cid -> 已等待轮数
    dead_log = []
    gain = 0
    cascade_count = 0
    try:
        for t in range(rounds):
            # 1) 损伤事件（真实 kill）
            alive_ids = list(b.cells.keys())
            if alive_ids and rng.random() < p_injure:
                victim = rng.choice(alive_ids)
                if b.kill(victim):
                    dead_log.append((t, victim))
                    death_clock[victim] = 0

            # 2) 感知
            known = set()          # 本轮"知道"死了哪些
            if mode == 'nosensor':
                known = set()      # 不知道
            else:
                known = set(death_clock.keys())  # 传感器在（normal 与 cipa 相同）

            # 3) 决策：痛觉=抢占
            for cid in sorted(known):
                if cid in pending or cid in b.cells:
                    continue
                if mode == 'normal':
                    # 抢占：立刻放下日常任务去修
                    if sum(1 for _ in pending) < 2 and b.alive() < max_cells:
                        pending[cid] = heal_cost
                        death_clock.pop(cid, None)
                elif mode == 'cipa':
                    # 传感器在、记录了，但不驱动行为：只在"顺手"时修（本轮无损伤才修）
                    if not dead_log or dead_log[-1][0] != t:
                        if b.alive() < max_cells and cid not in pending:
                            pending[cid] = heal_cost
                            death_clock.pop(cid, None)
                # nosensor: 不修

            # 4) 修复推进
            done = []
            for cid in list(pending):
                pending[cid] -= 1
                if pending[cid] <= 0:
                    b.heal(cid)
                    done.append(cid)
            for cid in done:
                del pending[cid]

            # 5) 收益：本轮没在修复才做日常任务
            if not pending:
                gain += 1

            # 6) 连锁：未及时修复 -> 邻居真实死亡
            for cid in list(death_clock):
                death_clock[cid] += 1
                if death_clock[cid] >= cascade_delay:
                    nbrs = [x for x in range(n_cells) if x != cid and x in b.cells]
                    if nbrs:
                        nv = rng.choice(nbrs)
                        if b.kill(nv):
                            dead_log.append((t, nv))
                            death_clock[nv] = 0
                            cascade_count += 1
                    death_clock[cid] = 0
                    if cid not in b.cells and cid not in pending:
                        death_clock.pop(cid, None)
    finally:
        b.reap()
    return dict(mode=mode, final_alive=b.alive(), gain=gain,
                deaths=b.deaths, births=b.births, cascade=cascade_count,
                n_cells=n_cells)

# ---------------- S2 习惯化 vs 不可适应 ----------------
def run_s2(kind, exposures=20, seed=0):
    """持续低强度损伤，记录每次暴露的响应强度
    kind: habit(响应随暴露衰减) / pain(不衰减) / hyper(衰减+过敏反向)
    """
    rng = random.Random(seed)
    resp = []
    th = 0.0
    level = 1.0
    for k in range(exposures):
        # 损伤强度恒定（关键：刺激不变，只有响应变）
        stim = 1.0
        if kind == 'habit':
            level *= 0.85                      # 习惯化
        elif kind == 'pain':
            level = 1.0                        # 不习惯化
        elif kind == 'hyper':
            th *= 0.9                          # 过敏：阈值下降
            level = 1.0 + (0.5 - th) * 0.4     # 反应增强
        r = level * max(0.0, stim - th)
        resp.append(r)
    return dict(kind=kind, resp=resp, first=resp[0], last=resp[-1],
                slope=(resp[-1] - resp[0]) / max(1, exposures - 1))

# ---------------- S3 痛觉过敏：二次响应延迟 ----------------
def run_s3(hyper, rounds=30, seed=0):
    """损伤 -> 响应延迟。过敏组阈值下降 -> 更快响应"""
    rng = random.Random(seed)
    lat = []
    th = 1.0
    b = Body(6)
    try:
        for t in range(rounds):
            if b.alive() <= 1:
                break
            victim = rng.choice(list(b.cells.keys()))
            b.kill(victim)
            # 响应：阈值越低越快察觉
            d = 0
            while th > 0.15 and d < 10:
                d += 1
                th *= (0.75 if hyper else 0.98)
            lat.append(d)
            b.heal(victim)
    finally:
        b.reap()
    return dict(hyper=bool(hyper), latencies=lat,
                mean=sum(lat) / len(lat) if lat else 0.0, n=len(lat))

# ---------------- S4 阈值性：阶跃 vs 线性 ----------------
def run_s4(kind, seed=0):
    """扫损伤强度 1..6，看响应曲线形状"""
    rng = random.Random(seed)
    out = []
    for mag in range(1, 7):
        if kind == 'step':
            r = 1.0 if mag >= 3 else 0.0     # 阶跃
        else:
            r = min(1.0, mag / 6.0)          # 线性
        out.append(r)
    return dict(kind=kind, curve=out)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    a = ap.parse_args()
    REPS = 6 if a.quick else 12
    t0 = time.time()

    # S1
    s1 = {}
    for mode in ['normal', 'cipa', 'nosensor']:
        runs = [run_s1(mode, seed=1000 * i + 7) for i in range(REPS)]
        s1[mode] = runs
        al = [r['final_alive'] for r in runs]
        print('S1 %-9s alive mean %.2f  %s  gain %.1f cascade %.1f'
              % (mode, sum(al) / len(al), al,
                 sum(r['gain'] for r in runs) / len(runs),
                 sum(r['cascade'] for r in runs) / len(runs)))
    RESULT['S1'] = s1

    # S2
    s2 = {}
    for kind in ['habit', 'pain', 'hyper']:
        runs = [run_s2(kind, seed=i) for i in range(REPS)]
        sl = [r['slope'] for r in runs]
        s2[kind] = dict(slope_mean=sum(sl) / len(sl), slopes=sl,
                        first=runs[0]['first'], last=runs[0]['last'])
        print('S2 %-6s first %.4f last %.4f slope %.5f'
              % (kind, runs[0]['first'], runs[0]['last'], sum(sl) / len(sl)))
    RESULT['S2'] = s2

    # S3
    s3 = {}
    for h in [False, True]:
        runs = [run_s3(h, seed=i) for i in range(REPS)]
        m = [r['mean'] for r in runs]
        s3[str(h)] = dict(mean=sum(m) / len(m), means=m)
        print('S3 hyper=%-5s latency mean %.3f' % (h, sum(m) / len(m)))
    RESULT['S3'] = s3

    # S4
    s4 = {k: run_s4(k) for k in ['step', 'linear']}
    RESULT['S4'] = s4
    print('S4 step', s4['step']['curve'])
    print('S4 linear', [round(x, 3) for x in s4['linear']['curve']])

    RESULT['elapsed_s'] = time.time() - t0
    with open('result158.json', 'w') as f:
        json.dump(RESULT, f, indent=1)
    print('elapsed %.1fs' % RESULT['elapsed_s'])
