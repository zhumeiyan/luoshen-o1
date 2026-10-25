"""重做：分离变量 2x2 {成本}x{去重}，食物池扩大到 40 条（避免重复饥饿混淆）"""
import sys, io, contextlib, json
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1/core'); sys.path.insert(0,'.')
from life5 import Life5
from digest_orig import DigestiveSystem as DSv1
import digest_v2 as V2
from digest_v2 import Brain

# 大食物池：40 条互不相同
BASE=["模型需要基线","准确率要对照随机","召回率分母需保护","外部通道要复测",
      "断言必须能失败","阈值不能硬编码","同义词替换会翻转","采样区间要扫描"]
FOOD=[f"<p>{b}，第{i}号观测记录。</p>" for i,b in enumerate(BASE*5)]
META=[f"<p>本系统用于识别彩票骗局，第{i}条规则说明。</p>" for i in range(8)]
POOL=FOOD+META

def wrap_v1(brain, cost, dedup):
    """v1 无法配置，用包装模拟：cost/dedup 在外部实现"""
    return DSv1(brain)

class DSv2cfg:
    def __init__(self, brain, cost=True, dedup=True, filter_meta=True):
        self.b=brain; self.cost=cost; self.dedup=dedup; self.fm=filter_meta
        self.seen=set()
    def _burn(self,a):
        if self.cost: self.b.energy_b-=a
    def mouth_chew(self,h):
        import re
        c=re.sub(r'<[^>]+>','',h)
        ch=[x.strip() for x in V2._SENT_SPLIT.split(c) if x.strip()]
        self._burn(len(c)*0.001); return ch
    def stomach_digest(self,ch):
        v,w=[],[]
        for c in ch:
            self._burn(0.5)
            if self.fm and V2._META.search(c): v.append(c); continue
            if V2._JUNK.search(c): w.append(c); continue
            if len(c)<5: w.append(c); continue
            v.append(c)
        return v,w
    def intestine_absorb(self,v):
        n=0
        for f in v:
            self._burn(1.2)
            h=V2.hashlib.sha256(f.encode()).hexdigest()[:16]
            if self.dedup and h in self.seen: continue
            self.seen.add(h); self.b.chain.append(h)
            room=min(5.0, self.b.cap-self.b.energy_b)
            if room>0: self.b.energy_b+=room; n+=1
        return n
    def excrete(self,w): self._burn(0.1*len(w))

def trial(mode, seed, steps=400, pool=POOL):
    rng=np.random.default_rng(seed)
    L=Life5(N=8,seed=seed,ratio=0.45)
    brain=Brain(energy=100.0)
    if mode=="v1": DS=DSv1(brain)
    else:
        cost,dedup,mf = mode
        DS=DSv2cfg(brain,cost=cost,dedup=dedup,filter_meta=mf)
    steps_alive=0
    for t in range(steps):
        html=pool[int(rng.integers(len(pool)))]
        e0=brain.energy_b
        with contextlib.redirect_stdout(io.StringIO()):
            c=DS.mouth_chew(html); v,w=DS.stomach_digest(c); DS.intestine_absorb(v); DS.excrete(w)
        dE=brain.energy_b-e0
        L.E=float(np.clip(L.E+dE/100.0,0.0,L.Emax)); L.step()
        if L.alive: steps_alive+=1
        else: break
    return dict(mode=str(mode),seed=seed,alive=bool(L.alive),steps=steps_alive,
                E=float(L.E),food_E=float(brain.energy_b),chain=len(brain.chain))

if __name__=="__main__":
    SEEDS=list(range(12))
    MODES=["v1",(True,True,True),(True,False,True),(False,True,True),(True,True,False)]
    NAMES={"v1":"v1 原版(永动机)","(True, True, True)":"v2 完整",
           "(True, False, True)":"v2 不去重","(False, True, True)":"v2 无代谢成本",
           "(True, True, False)":"v2 不过滤元内容"}
    print("="*84)
    print(f"{'条件':22s} {'存活':>7s} {'均值步数':>8s} {'终态E':>8s} {'食物侧E':>9s} {'记忆链':>7s}")
    print("-"*84)
    for m in MODES:
        rows=[trial(m,s) for s in SEEDS]
        al=sum(r['alive'] for r in rows)
        print(f"{NAMES[str(m)]:22s} {al:4d}/{len(SEEDS):2d} {np.mean([r['steps'] for r in rows]):8.1f} "
              f"{np.mean([r['E'] for r in rows]):8.4f} {np.mean([r['food_E'] for r in rows]):9.1f} "
              f"{np.mean([r['chain'] for r in rows]):7.1f}")
    print("="*84)
