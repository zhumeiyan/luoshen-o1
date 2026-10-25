#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 修正版：四臂分离"传感器在"与"痛觉抢占"各自贡献
关键修正：cascade_delay(5) > heal_cost(2)，修复来得及，策略才有意义
  normal  检测->立刻抢占修复
  queue   检测->排队(任务段结束再修)   [分离"抢占"的价值]
  cipa    检测->只记账不修            [分离"传感器"的价值]
  nosensor 不知道
"""
import os, sys, json, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell import Body

N_CELLS = 10
ROUNDS = 40
P_INJURE = 0.30
HEAL_COST = 2
CASCADE_DELAY = 5
TASK_SEG = 3
MAX_CELLS = 12

def run(mode, seed=0):
    rng = random.Random(seed)
    b = Body(N_CELLS)
    pending = {}      # cid -> 剩余修复轮
    wounds = {}       # cid -> 已等待轮（未修复的伤口）
    gain = 0
    cascade = 0
    healed = 0
    lost = 0
    try:
        for t in range(ROUNDS):
            # 1 真实损伤
            alive = list(b.cells.keys())
            if alive and rng.random() < P_INJURE:
                v = rng.choice(alive)
                if b.kill(v):
                    wounds[v] = 0
                    lost += 1

            # 2 感知（normal/queue/cipa 相同；nosensor 为空）
            known = set() if mode == 'nosensor' else set(wounds.keys())

            # 3 决策
            for cid in sorted(known):
                if cid in pending or cid in b.cells:
                    continue
                if mode == 'normal':
                    if len(pending) < 2 and b.alive() < MAX_CELLS:
                        pending[cid] = HEAL_COST
                        wounds.pop(cid, None)
                elif mode == 'queue':
                    # 只在任务段边界才处理伤口 -> 平均延迟 TASK_SEG/2
                    if t % TASK_SEG == 0 and len(pending) < 2 and b.alive() < MAX_CELLS:
                        pending[cid] = HEAL_COST
                        wounds.pop(cid, None)
                # cipa / nosensor 不修

            # 4 修复推进（真实 fork）
            done = [c for c in pending if (pending.update({c: pending[c]-1}) or pending[c] <= 0)]
            for c in done:
                b.heal(c); healed += 1; del pending[c]

            # 5 收益：本轮未在修复才做日常任务
            if not pending:
                gain += 1

            # 6 连锁：伤口超时 -> 邻居真实死亡
            for cid in list(wounds):
                wounds[cid] += 1
                if wounds[cid] >= CASCADE_DELAY:
                    nbrs = [x for x in range(N_CELLS) if x != cid and x in b.cells and x not in wounds]
                    if nbrs:
                        nv = rng.choice(nbrs)
                        if b.kill(nv):
                            wounds[nv] = 0
                            cascade += 1
                    del wounds[cid]
        res = dict(mode=mode, alive=b.alive(), gain=gain, cascade=cascade,
                   healed=healed, lost=lost)
    finally:
        b.reap()
    return res

if __name__ == '__main__':
    REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    out = {}
    for mode in ['normal', 'queue', 'cipa', 'nosensor']:
        rs = [run(mode, seed=977 * i + 13) for i in range(REPS)]
        al = [r['alive'] for r in rs]
        gn = [r['gain'] for r in rs]
        cc = [r['cascade'] for r in rs]
        out[mode] = dict(alive=al, gain=gn, cascade=cc,
                         alive_mean=sum(al)/len(al), gain_mean=sum(gn)/len(gn),
                         cascade_mean=sum(cc)/len(cc))
        print('%-9s alive %5.2f %s' % (mode, sum(al)/len(al), al))
        print('          gain  %5.2f  cascade %5.2f  healed %.1f lost %.1f'
              % (sum(gn)/len(gn), sum(cc)/len(cc),
                 sum(r['healed'] for r in rs)/len(rs),
                 sum(r['lost'] for r in rs)/len(rs)))
    json.dump(out, open('result_s1.json','w'), indent=1)
