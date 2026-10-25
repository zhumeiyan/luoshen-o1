import sys, os, json
import numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1')
from core.life5 import Life5
from core.world_rhythm import WorldRhythm
N=8; STEPS=400; KSEEK=1.0; AMP=2.0
def ent(a):
    a=np.asarray(a,float)+1e-12; p=a/a.sum()
    return float(-(p*np.log(p)).sum()/np.log(len(p)))
def run(seed, mpt):
    L=Life5(N=N,seed=seed,k_seek=KSEEK); L.input_val=0.0
    W=WorldRhythm(N=N,minutes_per_tick=mpt,seed=seed*13+5,forage_ch=L.forage_ch,use_meal=True)
    es=[];sh=[]
    for t in range(STEPS):
        if not L.alive: break
        L.net_push=W.step(AMP,focused=True)
        r=L.step()
        if r:
            es.append(ent(r["avec"])); a=np.asarray(r["avec"],float)
            sh.append(a[0]/a.sum() if a.sum()>1e-12 else 0.0)
    tail=es[len(es)//2:]
    return dict(alive=L.alive, ent=float(np.mean(tail)) if tail else 0.0,
                share0=float(np.mean(sh[-50:])) if sh else 0.0)
print("="*88)
print(" 时间尺度扫描（集中+饭点）—— 一拍代表多久才有效？24 seeds")
print("="*88)
print(f"\n{'一拍=':>10}{'存活':>9}{'后段熵':>10}{'份额0':>10}   覆盖节律")
print("-"*88)
rows=[]
for mpt,lbl,see in [(1,"1分钟","几乎静止"),(15,"15分","静止"),(60,"1小时","日夜+饭点"),
                    (180,"3小时","日夜+饭点粗"),(720,"12小时","日夜"),(1440,"1天","周"),(10080,"1周","季节")]:
    rs=[run(s,mpt) for s in range(24)]
    r=dict(alive=sum(1 for x in rs if x["alive"]),
           ent=float(np.mean([x["ent"] for x in rs])),
           share0=float(np.mean([x["share0"] for x in rs])))
    rows.append((lbl,r))
    print(f"{lbl:>10}{r['alive']:>5}/24{r['ent']:>10.4f}{r['share0']:>10.4f}   {see}")
print("-"*88)
best=max(rows,key=lambda x:x[1]["alive"])
print(f"\n  ★ 最优：一拍={best[0]}  存活 {best[1]['alive']}/24  份额0 {best[1]['share0']:.4f}")
print(f"  ★ 尺度不敏感吗？存活跨度 {min(x[1]['alive'] for x in rows)} ~ {max(x[1]['alive'] for x in rows)}")
print(f"\n  对照基线：不推 3/24   机械轮换 24/24 份额0 0.2831 熵 0.1866")
json.dump({l:r for l,r in rows}, open(".sense/world_scale.json","w"), ensure_ascii=False, indent=1)
