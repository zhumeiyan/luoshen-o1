# -*- coding: utf-8 -*-
"""
阶段C：断供后 Avida 个体的真实状态分解 + 可证伪对照
====================================================
关键问题：断供后 births=0，是因为
  (a) 个体没有能量（自给没获得）？
  (b) 有能量但丧失了繁殖机制（顾此失彼）？
这两者含义完全不同。

同时做阳/阴性对照，证明指标可证伪。
"""
import sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
sys.path.insert(0, '/data/workspace/luoshen-o1/experiments/exp128_avida')
from core.life5 import Life5
from avida import *

ANC = [H_ALLOC, NOP_A, JMP_HEAD, H_COPY, IF_N_EQU, MOV_HEAD, NOP_B, H_DIVIDE] + [NOP_C] * 20


def budget_of(bio, w):
    """断供(slice=0)后该个体的每代能量"""
    sg = (bio.reward - 1.0) * w.task_energy_scale
    return int((w.slice_ratio * w.scarcity * w.energy_per_cycle) + sg)


def can_replicate(bio, w, maxc=5000):
    t = Bio(bio.genome, mem_size=len(bio.genome) * 2)
    t.mem = list(bio.mem)
    t.ax, t.bx, t.cx = bio.ax, bio.bx, bio.cx
    for _ in range(maxc):
        r = w._exec(t)
        if r and r[0] == 'divide':
            return True
        if r and r[0] == 'divide_fail':
            return False
    return False


def avida_state(seed, gens=400, mut=0.02, pop=40):
    w = World(ANC, pop_size=pop, seed=seed, mut_rate=mut,
              slice_ratio=80, task_energy_scale=20)
    for _ in range(gens):
        w.step_generation()
    w.slice_ratio = 0                      # 断供
    rows = []
    for b in w.pop:
        bud = budget_of(b, w)
        rep = can_replicate(b, w)
        rows.append(dict(has_task=bool(b.tasks_done), budget=bud, replicate=rep))
    n = len(rows)
    return dict(
        seed=seed, n=n,
        n_task=sum(r['has_task'] for r in rows),
        n_energy=sum(r['budget'] > 0 for r in rows),
        n_task_and_energy=sum(r['has_task'] and r['budget'] > 0 for r in rows),
        n_task_and_replicate=sum(r['has_task'] and r['replicate'] for r in rows),
        n_replicate=sum(r['replicate'] for r in rows),
        n_task_not_replicate=sum(r['has_task'] and not r['replicate'] for r in rows),
    )


if __name__ == '__main__':
    out = {'avida_state': [], 'controls': {}}

    print('=== 断供后 Avida 个体状态分解 ===')
    print(f"{'seed':>5}{'N':>5}{'有任务':>8}{'有能量':>8}{'任务∧能量':>10}{'任务∧能繁殖':>12}{'任务但废':>9}")
    for s in range(5):
        r = avida_state(s)
        out['avida_state'].append(r)
        print(f"{s:>5}{r['n']:>5}{r['n_task']:>8}{r['n_energy']:>8}"
              f"{r['n_task_and_energy']:>10}{r['n_task_and_replicate']:>12}{r['n_task_not_replicate']:>9}")

    tot = {k: sum(r[k] for r in out['avida_state']) for k in
           ['n', 'n_task', 'n_energy', 'n_task_and_energy',
            'n_task_and_replicate', 'n_task_not_replicate']}
    out['avida_total'] = tot
    print(f"\n合计：获得自给 {tot['n_task']}/{tot['n']}"
          f"；断供后有能量 {tot['n_energy']}/{tot['n']}"
          f"；【有自给且能繁殖】{tot['n_task_and_replicate']}/{tot['n']}")

    # ---------- 可证伪对照 ----------
    # 阴性：mut=0（无变异）→ 应无任务、无自给
    w_neg = World(ANC, pop_size=40, seed=1, mut_rate=0.0,
                  slice_ratio=80, task_energy_scale=20)
    for _ in range(400):
        w_neg.step_generation()
    n_task_neg = sum(1 for b in w_neg.pop if b.tasks_done)
    # 阳性：人为给全部个体一个任务 → 断供后应有能量
    w_pos = World(ANC, pop_size=40, seed=1, mut_rate=0.0,
                  slice_ratio=80, task_energy_scale=20)
    for _ in range(50):
        w_pos.step_generation()
    for b in w_pos.pop:
        b.tasks_done.add('AND')
        b.reward += 4.0
    w_pos.slice_ratio = 0
    n_energy_pos = sum(1 for b in w_pos.pop if budget_of(b, w_pos) > 0)
    out['controls']['avida'] = dict(neg_mut0_tasks=n_task_neg,
                                    pos_given_task_energy=n_energy_pos, n=len(w_pos.pop))

    # Life5 阳性/阴性对照
    def lf_wean(fg, seed):
        lf = Life5(N=8, seed=seed, fg=fg)
        t0 = lf.t
        while lf.alive and lf.t - t0 < 1500:
            lf.step()
        return bool(lf.alive)
    pos = sum(lf_wean(0.15, s) for s in range(16))
    neg = sum(lf_wean(0.0, s) for s in range(16))
    out['controls']['life5'] = dict(pos_fg015=pos, neg_fg0=neg, n=16)

    print(f"\n=== 可证伪对照 ===")
    print(f"Avida 阴性(mut=0)：获得任务 {n_task_neg}/40   （应为 0）")
    print(f"Avida 阳性(强给任务)：断供有能量 {n_energy_pos}/40   （应 >0）")
    print(f"Life5 阳性(fg=0.15)：断供存活 {pos}/16")
    print(f"Life5 阴性(fg=0)   ：断供存活 {neg}/16   （应为 0）")

    json.dump(out, open('stageC_result.json', 'w'), indent=2, ensure_ascii=False, default=str)
    print('\nsaved stageC_result.json')
