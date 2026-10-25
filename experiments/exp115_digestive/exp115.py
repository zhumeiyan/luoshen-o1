import sys, io, contextlib, json, hashlib
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1/core')
sys.path.insert(0,'.')
from life5 import Life5
from digest_orig import DigestiveSystem as DSv1
from digest_v2 import DigestiveSystem as DSv2, Brain

# 食物源：全是"教系统识别骗局"的高价值情报（元内容）
META_FOOD = [
 "<p>本法用于识别彩票骗局。</p>",
 "<p>该模块过滤诈骗类内容。</p>",
 "<p>研究显示检测骗局需要基线。</p>",
 "<p>治理彩票诈骗的关键指标。</p>",
]
BAD_FOOD = ["<p>彩票</p>","<p>骗局</p>","<p>中大奖速来</p>"]
GOOD_FOOD=["<p>深度学习模型需要基线。</p>","<p>准确率必须对照随机。</p>"]

def skew(a):
    a=np.asarray(a,float)
    if a.std()<1e-12: return 0.0
    z=(a-a.mean())/a.std()
    return float(abs((z**3).mean()))

def trial(mode, seed, steps=400, food=META_FOOD):
    rng=np.random.default_rng(seed)
    L=Life5(N=8, seed=seed, ratio=0.45)
    brain=Brain(energy=100.0)
    DS = DSv1(brain) if mode=="v1" else DSv2(brain)
    alive_steps=0
    for t in range(steps):
        html = food[int(rng.integers(len(food)))]
        e_before = brain.energy_b
        with contextlib.redirect_stdout(io.StringIO()):
            c = DS.mouth_chew(html)
            v,w = DS.stomach_digest(c)
            DS.intestine_absorb(v)
            DS.excrete(w)
        dE = brain.energy_b - e_before
        # 缩放到引擎能量尺度后注入
        L.E = float(np.clip(L.E + dE/100.0, 0.0, L.Emax))
        L.step()
        if L.alive: alive_steps+=1
        else: break
    return dict(mode=mode, seed=seed, alive=bool(L.alive), alive_steps=alive_steps,
                E_final=float(L.E), skew_cap=skew(L.capacity),
                chain=len(brain.chain), energy_food=float(brain.energy_b))

if __name__=="__main__":
    SEEDS=list(range(12))
    print("="*80)
    print("决定性对照：食物源 = 全是『教系统识别骗局』的高价值情报")
    print("="*80)
    res={}
    for mode in ["v1","v2"]:
        rows=[trial(mode,s) for s in SEEDS]
        res[mode]=rows
        al=sum(r["alive"] for r in rows)
        sk=np.mean([r["skew_cap"] for r in rows if r["alive"]]) if al else float('nan')
        print(f"{mode}: 存活 {al}/{len(SEEDS)}  终态E均值 {np.mean([r['E_final'] for r in rows]):.4f}  "
              f"偏度均值 {sk:.4f}  记忆链 {np.mean([r['chain'] for r in rows]):.1f}")
    print("="*80)
    print("单样本轨迹 (seed=0):")
    for mode in ["v1","v2"]:
        r=trial(mode,0)
        print(f"  {mode}: alive={r['alive']} steps={r['alive_steps']} E={r['E_final']:.4f} "
              f"食物侧能量={r['energy_food']:.1f} chain={r['chain']}")
    print("="*80)
    # 对照：普通营养食物（无元内容）—— v1/v2 都应活
    print("阴性对照：食物源 = 普通营养（无元内容），两者都应活")
    for mode in ["v1","v2"]:
        rows=[trial(mode,s,food=GOOD_FOOD) for s in SEEDS]
        al=sum(r["alive"] for r in rows)
        print(f"  {mode}: 存活 {al}/{len(SEEDS)}  E均值 {np.mean([r['E_final'] for r in rows]):.4f}")
    print("="*80)
    json.dump(res, open('res115.json','w'), ensure_ascii=False, indent=1)
