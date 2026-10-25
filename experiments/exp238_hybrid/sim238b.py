import json, statistics as st

def run(P, T=600, capA=20, ampl=5.0, d=1.0, rA=0.05, penalty=0.9, seeds=6):
    """
    修: v1 中 d*T 成了唯一瓶颈, ampl/P 全无效 -> 作废。
    v2 加入【堆积惩罚】: 临时存储 S 占容量比例越高, 内化质量越低
        (消化不了的东西堆着 -> 变成噪声/污染, 损害已有判据)
    质量 = max(0, 1 - penalty*(S/capA))
    这样 ampl 太大 / P 太短 -> S 堆积 -> 质量崩; P 太长 -> 总量少
    """
    res=[]
    for s in range(seeds):
        S=0.0; R=0.0; lost=0.0
        for t in range(T):
            if t % P == 0:
                S += ampl                      # B 的产出落回 A
            S += rA
            if S > capA:                       # 溢出(装不下, 丢)
                lost += S-capA; S = capA
            q = max(0.0, 1-penalty*(S/capA))   # 堆积惩罚
            inn = min(S, d)
            S -= inn; R += inn*q
        res.append(R)
    return st.mean(res)

def A_alone(T=600, rA=0.05): return rA*T

out={}
base = A_alone()
print("== P 扫描 (ampl=5, capA=20, d=1.0)  A单独=%.1f =="%base)
best=(0,None)
for P in [1,3,5,8,12,20,30,50,100,200,400]:
    v=run(P); adv=v-base; out['P=%d'%P]=round(v,2)
    if adv>best[0]: best=(adv,P)
    print("  P=%-5d 产出=%-7.2f 优势=%+.2f"%(P,v,adv))
print("  --> 最优 P=%d 优势=%+.2f"%(best[1],best[0]))

print("\n== ampl 扫描 (P=%d) =="%best[1])
ba=(0,None)
for a in [0.5,1,2,3,5,8,12,20,40]:
    v=run(best[1],ampl=a); adv=v-base; out['ampl=%.1f'%a]=round(v,2)
    if adv>ba[0]: ba=(adv,a)
    print("  ampl=%-5.1f 产出=%-7.2f 优势=%+.2f"%(a,v,adv))
print("  --> 最优 ampl=%.1f 优势=%+.2f"%(ba[1],ba[0]))

print("\n== 产物落在谁那里 (决定性对照) ==")
out['落在B侧_归零']=0.0
out['落在A侧']=round(run(best[1],ampl=ba[1]),2)
print("  B 侧(不落回): 0.00   <- 等于 B 单独, 全废")
print("  A 侧(落回):   %.2f"%run(best[1],ampl=ba[1]))

print("\n== 杂交优势的充分必要条件 (消融) ==")
tests={
 'A的persist + B的放大(完整异交)': dict(P=best[1], ampl=ba[1]),
 '去掉放大(ampl=0, 只剩A)':       dict(P=best[1], ampl=0.0),
 '放大极大(ampl=200, 撑爆A)':     dict(P=best[1], ampl=200),
 '周期极短(P=1, 撑爆A)':          dict(P=1,      ampl=ba[1]),
 '周期极长(P=600, 几乎不授粉)':    dict(P=600,    ampl=ba[1]),
}
for k,kw in tests.items():
    v=run(**kw); out[k]=round(v,2)
    print("  %-32s %.2f  优势=%+.2f"%(k,v,v-base))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp238_hybrid/result238b.json','w'), ensure_ascii=False, indent=1)
