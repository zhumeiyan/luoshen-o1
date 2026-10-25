# -*- coding: utf-8 -*-
"""
阶段B：外部平台基线对照 —— Avida（演化） vs LuoshenLife5（学习）
==============================================================
共同协议：
  阶段1 供给期：给外部供给，让系统有机会获得【自给能力】
  阶段2 断供期：外部供给 = 0，只看自身获取能力能否维持

  Avida     的自给能力 = 完成任务（reward 独立于 slice 供能）
  Life5     的自给能力 = fg（觅食效率，从 0 起学）

可比的是【无量纲成功率】，不是时间（代 vs 拍 单位不可通约）。
"""
import sys, json, time
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1')
sys.path.insert(0, '/data/workspace/luoshen-o1/experiments/exp128_avida')
from core.life5 import Life5
from avida import *

ANC = [H_ALLOC, NOP_A, JMP_HEAD, H_COPY, IF_N_EQU, MOV_HEAD, NOP_B, H_DIVIDE] + [NOP_C] * 20

# ============ Life5 侧（复用 126 协议）============
TAU, ETA, DRIP = 20.0, 0.004, 0.010
T1, T2 = 1200, 1500
FCH = 7


def world_response(scheme, act, rng):
    if scheme in ('practice_closed', 'tool_plus_self'):
        return act * (0.8 + 0.4 * rng.random())
    if scheme == 'practice_open':
        return 0.30 * (0.5 + rng.random())
    return 0.0


def life5_wean(scheme, seed):
    lf = Life5(N=8, seed=seed, fg=0.0)
    rng = np.random.default_rng(seed * 7919 + 13)
    fg, ma, mf = 0.0, 0.0, 0.0
    for _ in range(T1):
        if not lf.alive:
            break
        lf.fg = fg
        lf.step()
        act = lf.log[-1]['avec'][FCH]
        fb = world_response(scheme, act, rng)
        lf.E = min(lf.Emax, lf.E + DRIP)          # 供给期输液
        if scheme in ('practice_closed', 'practice_open', 'tool_plus_self'):
            ma += (act - ma) / TAU
            mf += (fb - mf) / TAU
            fg = max(0.0, fg + ETA * (act - ma) * (fb - mf))
        elif scheme == 'variation':
            fg = max(0.0, fg + 0.0008 * rng.normal())
    learned = float(fg)
    # 断供
    lf.fg = learned
    t0 = lf.t
    while lf.alive and lf.t - t0 < T2:
        lf.step()
    return dict(fg=learned, alive=bool(lf.alive), ticks=int(lf.t - t0))


# ============ Avida 侧 ============
def avida_wean(seed, gens=400, mut=0.02, pop=40):
    w = World(ANC, pop_size=pop, seed=seed, mut_rate=mut,
              slice_ratio=80, task_energy_scale=20)
    for _ in range(gens):
        w.step_generation()
    n_self = sum(1 for b in w.pop if b.tasks_done)      # 获得自给能力的个体
    # 断供
    b0 = w.total_births
    w.slice_ratio = 0
    for _ in range(200):
        w.step_generation()
    return dict(pop=len(w.pop), n_self=n_self,
                births_supply=b0,
                births_after_cut=w.total_births - b0,
                self_rate=n_self / len(w.pop))


if __name__ == '__main__':
    out = {'life5': {}, 'avida': {}}

    print('=== Life5 断供（16 seed）===')
    print(f"{'方案':<18}{'学到fg':>10}{'断供存活':>10}{'存活率':>9}")
    for sc in ['practice_closed', 'practice_open', 'no_practice', 'variation']:
        rs = [life5_wean(sc, s) for s in range(16)]
        fg = np.array([r['fg'] for r in rs])
        al = np.array([r['alive'] for r in rs], dtype=float)
        out['life5'][sc] = dict(fg=float(fg.mean()), fg_sd=float(fg.std(ddof=1)),
                                survive=float(al.mean()), n=16,
                                ticks=float(np.mean([r['ticks'] for r in rs])))
        print(f'{sc:<18}{fg.mean():10.5f}{int(al.sum()):>8}/16{al.mean():9.3f}')

    print('\n=== Avida 断供（5 seed）===')
    print(f"{'seed':>5}{'获得自给':>10}{'占比':>8}{'断供后新增':>12}")
    av = [avida_wean(s) for s in range(5)]
    tot_self = sum(a['n_self'] for a in av)
    tot_pop = sum(a['pop'] for a in av)
    tot_after = sum(a['births_after_cut'] for a in av)
    for i, a in enumerate(av):
        print(f"{i:>5}{a['n_self']:>8}/{a['pop']:<3}{a['self_rate']:8.3f}{a['births_after_cut']:>12}")
    out['avida'] = dict(seeds=av, tot_self=tot_self, tot_pop=tot_pop,
                        self_rate=tot_self / tot_pop, births_after_cut=tot_after)

    print(f"\nAvida 合计：获得自给 {tot_self}/{tot_pop} = {tot_self/tot_pop:.3f}"
          f"；断供后新增出生 {tot_after}")
    print(f"Life5 相倚练习：存活率 {out['life5']['practice_closed']['survive']:.3f}")

    json.dump(out, open('stageB_result.json', 'w'), indent=2, ensure_ascii=False, default=str)
    print('\nsaved stageB_result.json')
