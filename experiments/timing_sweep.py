#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同样的 26 拍峰值，放在不同时刻，损伤一样吗？—— 验证上一步的反直觉结果"""
import sys,os,json
import numpy as np
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','core'))
from life5 import Life5
STEPS=600; CH=0; SEEDS=range(16)

def run(peak_at, others=8, seeds=SEEDS):
    pt=[60*i for i in range(1,10)]
    sched={}
    for k in range(26): sched[peak_at+k]=True
    for t in pt:
        if abs(t-peak_at)<40: continue      # 跳过与峰值重叠的那次按键
        for k in range(others): sched[t+k]=True
    rows=[]
    for sd in seeds:
        def alloc(want,B,s):
            o=np.argsort(-want); a=np.zeros(s.N); left=B
            if sched.get(s.t,False):
                for i in o:
                    if i==CH: continue
                    tk=min(want[i],left); a[i]=tk; left-=tk
                    if left<=1e-12: break
                return a
            for i in o:
                tk=min(want[i],left); a[i]=tk; left-=tk
                if left<=1e-12: break
            return a
        lf=Life5(N=8,seed=sd,alloc_fn=alloc); lf.run(STEPS)
        rows.append(dict(seed=int(sd),cap0=float(np.asarray(lf.capacity)[0]),alive=bool(lf.alive)))
    return rows

def main():
    print("="*72); print(" 同样一次 26 拍峰值，落在不同时刻"); print("="*72)
    print(f" {'落点':<12}{'存活':>7}{'cap0':>10}")
    res={}
    for at in [0,60,120,240,360,480]:
        r=run(at); res[at]=r
        print(f" 拍{at:<9}{sum(x['alive'] for x in r)}/{len(r):<5}{np.mean([x['cap0'] for x in r]):>10.4f}")
    xs=[np.mean([x['cap0'] for x in res[a]]) for a in res]
    print()
    print(f"   最早(拍0) {xs[0]:.4f}  →  最晚(拍480) {xs[-1]:.4f}   差 {xs[-1]-xs[0]:+.4f}")
    if xs[-1]>xs[0]:
        print("   ✅ 单调：同样的打击，越晚挨越轻 —— 早期最脆")
        print("   → 那么'把成本挪到开机'是挪到了【最脆的时刻】，补丁方向错了")
    else:
        print("   ⬜ 非单调，落点时间不是主因")
    json.dump({str(a):res[a] for a in res},open(os.path.join(os.path.dirname(__file__),'..','data','timing_sweep.json'),'w'),ensure_ascii=False,indent=1)
    return 0
if __name__=="__main__": sys.exit(main())
