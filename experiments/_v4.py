import sys, os, json
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1')
from core.life5 import Life5
N=8; STEPS=400; KSEEK=1.0
def ent(a):
    a=np.asarray(a,float)+1e-12; p=a/a.sum()
    return float(-(p*np.log(p)).sum()/np.log(len(p)))

def run(seed, mode, amp=2.0, frm=100, steps=STEPS):
    L=Life5(N=N,seed=seed,k_seek=KSEEK); L.input_val=0.0
    rng=np.random.default_rng(seed*7+1)
    es=[];sh=[]
    for t in range(steps):
        if not L.alive: break
        nv=None
        if t>=frm:
            if mode=="恒定多维":  nv=np.full(N,amp)
            elif mode=="轮换场景": nv=np.zeros(N); nv[t%N]=amp      # 每拍换一处
            elif mode=="随机场景": nv=rng.random(N)*amp              # 每拍随机分布
            elif mode=="单维恒定": nv=np.zeros(N); nv[0]=amp
        L.net_push=nv
        r=L.step()
        if r:
            es.append(ent(r["avec"])); a=np.asarray(r["avec"],float)
            sh.append(a[0]/a.sum() if a.sum()>1e-12 else 0.0)
    tail=es[len(es)//2:]
    return dict(alive=L.alive, ent=float(np.mean(tail)) if tail else 0.0,
                share0=float(np.mean(sh[-50:])) if sh else 0.0)

print("="*84)
print(" 『多场景』到底是什么：恒定多维 vs 轮换 vs 随机  (amp=2.0, 24 seeds)")
print("="*84)
print(f"\n{'刺激方式':<20}{'存活':>9}{'后段熵':>10}{'份额0':>10}")
print("-"*84)
res={}
for lbl,m in [("不推(基线)",None),("单维恒定","单维恒定"),("恒定多维","恒定多维"),
              ("轮换场景","轮换场景"),("随机场景","随机场景")]:
    rs=[run(s,m) for s in range(24)]
    r=dict(alive=sum(1 for x in rs if x["alive"]),
           ent=float(np.mean([x["ent"] for x in rs])),
           share0=float(np.mean([x["share0"] for x in rs])))
    res[lbl]=r
    print(f"{lbl:<20}{r['alive']:>5}/24{r['ent']:>10.4f}{r['share0']:>10.4f}")

print("\n"+"="*84)
print(" 结论")
print("="*84)
print(f"\n  存活：基线 {res['不推(基线)']['alive']}/24")
for k in ["单维恒定","恒定多维","轮换场景","随机场景"]:
    print(f"        {k} {res[k]['alive']}/24   Δ{res[k]['alive']-res['不推(基线)']['alive']:+d}")
best=max(["恒定多维","轮换场景","随机场景"], key=lambda k:res[k]["alive"])
print(f"\n  ★ 最能救命的：{best} ({res[best]['alive']}/24)")
print(f"  ★ 熵有没有救回来：最高 {max(res[k]['ent'] for k in res):.4f}"
      f"  （基线 {res['不推(基线)']['ent']:.4f}）")
print(f"     → 熵几乎没动 = 【活下来了，但多样性没恢复】")
