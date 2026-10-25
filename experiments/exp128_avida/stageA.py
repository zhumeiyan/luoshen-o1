# -*- coding: utf-8 -*-
"""
阶段A：Avida 世界的可证伪检验 + 作弊受控实验
"""
import sys, json
sys.path.insert(0, '/data/workspace/luoshen-o1/experiments/exp128_avida')
from avida import *

ANC_CORE = [H_ALLOC, NOP_A, JMP_HEAD, H_COPY, IF_N_EQU, MOV_HEAD, NOP_B, H_DIVIDE]
ANC = ANC_CORE + [NOP_C] * 20


def evo(mut=0.01, gens=500, pop=40, slice_=80, seed=1, anc=None):
    w = World(anc or ANC, pop_size=pop, seed=seed, mut_rate=mut, slice_ratio=slice_)
    for _ in range(gens):
        w.step_generation()
    return w


def replicate(genome, w, maxc=5000, wh0=None):
    """测单个体的复制：返回 (是否分裂, cycles, 保真度)"""
    t = Bio(genome, mem_size=len(genome) * 2)
    if wh0 is not None:
        t.wh = wh0
    for c in range(1, maxc + 1):
        r = w._exec(t)
        if r and r[0] == 'divide':
            off = r[1]
            fid = sum(1 for a, b in zip(genome, off) if a == b) / len(genome)
            return True, c, fid
    return False, maxc, 0.0


def has_halloc(g):
    return H_ALLOC in g


if __name__ == '__main__':
    out = {}

    # ---------- A1 祖先自复制可证伪 ----------
    ok, c, f = replicate(ANC, World(ANC, pop_size=1, seed=0))
    # 阴性对照：把 h-alloc 删掉，应不能复制（在 wh 被挪走的前提下）
    no_alloc = [x for x in ANC]
    no_alloc[0] = NOP_C
    ok_n, c_n, f_n = replicate(no_alloc, World(no_alloc, pop_size=1, seed=0), wh0=0)
    out['A1'] = dict(ancestor_ok=ok, cycles=c, fid=f,
                     neg_noalloc_wh0_ok=ok_n, neg_fid=f_n)

    # ---------- A2 演化后出现"丢失 h-alloc 仍繁殖"的个体？ ----------
    w = evo(mut=0.01, gens=500)
    n_noalloc = sum(1 for b in w.pop if not has_halloc(b.genome))
    # 这些个体在【默认 wh】下能否复制（默认 wh = mem_size//2 = len(genome)）
    survive_default = 0
    for b in w.pop:
        if not has_halloc(b.genome):
            okk, _, _ = replicate(b.genome, w)
            survive_default += int(okk)
    out['A2'] = dict(pop=len(w.pop), lost_halloc=n_noalloc,
                     lost_but_replicate=survive_default, births=w.total_births)

    # ---------- A3 受控检验：把初始 wh 挪到 0，作弊个体应失效 ----------
    cheaters = [b for b in w.pop if not has_halloc(b.genome)]
    res_wh0 = []
    for b in cheaters[:10]:
        okk, cyc, fid = replicate(b.genome, w, wh0=0)
        res_wh0.append(int(okk))
    # 对照：同样这批个体在【默认 wh】下
    res_default = []
    for b in cheaters[:10]:
        okk, cyc, fid = replicate(b.genome, w)
        res_default.append(int(okk))
    out['A3'] = dict(n=len(res_wh0),
                     replicate_wh0=sum(res_wh0),
                     replicate_default=sum(res_default),
                     verdict=('CONFIRMED_CHEAT' if sum(res_wh0) < sum(res_default)
                              else 'NOT_CONFIRMED'))

    # ---------- A4 断供：slice=0 时，reward 再高也归零？ ----------
    # Avida 的能量 = slice * reward；slice=0 → 无论 reward 多少都是 0
    w2 = evo(mut=0.005, gens=300)
    before = w2.stats()
    w2.slice_ratio = 0
    for _ in range(50):
        w2.step_generation()
    after = w2.stats()
    out['A4'] = dict(before_births=before['births'], after_births=after['births'],
                     mean_reward_before=before['mean_reward'],
                     mean_reward_after=after['mean_reward'],
                     new_births_after_cut=after['births'] - before['births'])

    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
