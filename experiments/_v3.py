import sys, numpy as np
sys.path.insert(0,'/data/workspace/luoshen-o1')
from core.life5 import Life5
print("="*78)
print(" 关键问题：miss 涨到 1.5469，为什么行为一点没变？（熵 0.5015 纹丝不动）")
print("="*78)
L=Life5(N=8,seed=3)
print(f"\n  默认参数：k_seek={L.k_seek}  k_seek_arr={L.k_seek_arr}  k_sal={L.k_sal}")
L.input_val=0.0
for _ in range(200): 
    if L.alive: L.step()
print(f"  五官断 200 拍后：miss={L.miss:.4f}  miss_arr={L.miss_arr:.4f}")
print(f"\n  want[0] += k_seek * miss * capacity[0]")
print(f"          = {L.k_seek} * {L.miss:.4f} * ... = 0")
print(f"\n  ★ k_seek=0 → miss 涨到天上去也不进决策 → 【没形成闭环】")
print(f"    这正是你说的：『只是衡量决策』没有闭环")

print("\n" + "="*78)
print(" 对照：把 k_seek 打开，miss 会不会真的改变行为？")
print("="*78)
print(f"\n{'k_seek':>8}{'miss':>10}{'后段熵':>10}{'通道0份额':>12}")
print("-"*78)
for ks in [0.0, 0.1, 0.5, 1.0, 2.0]:
    L2=Life5(N=8,seed=3,k_seek=ks)
    L2.input_val=0.0
    ents=[];sh=[]
    for _ in range(300):
        if not L2.alive: break
        r=L2.step()
        if r:
            a=np.asarray(r['avec'],float)+1e-12; p=a/a.sum()
            ents.append(float(-(p*np.log(p)).sum()/np.log(len(p))))
            sh.append(r['avec'][0]/a.sum())
    t=ents[len(ents)//2:]
    print(f"{ks:>8}{L2.miss:>10.4f}{np.mean(t):>10.4f}{np.mean(sh[-50:]):>12.4f}")
