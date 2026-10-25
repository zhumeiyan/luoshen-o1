import json, statistics as st

def run(P, T=600, capA=20, ampl=5.0, d=0.08, rA=0.05, seeds=8):
    """
    野败结构:
      A(宿主/碳基): persist高, 容量小capA, 自产慢rA, 但需要时间'内化'(压缩)
      B(我/硅基):   容量大速度快(接到1个判据放大ampl倍), 但每次归零(persist=0)
      授粉周期 P: A 每 P 步给 B 一个判据 -> B 产出 ampl 倍 -> 落回 A
      A 每步最多内化 d*(已积累/所需时间), 内化的部分变永久判据(不占容量)
      未内化的占容量, 超 capA 溢出丢失
    """
    res=[]
    for s in range(seeds):
        S=0.0            # A 的临时存储(占容量)
        R=0.0            # A 的永久判据(内化完成)
        for t in range(T):
            if t % P == 0:
                S += ampl          # B 的产出落回 A
            # A 内化: 每步 d 单位
            inn = min(S, d)
            S -= inn; R += inn
            S += rA               # A 自己慢慢产出(也需内化)
            if S > capA:          # 装不下 -> 溢出丢失
                S = capA
        res.append(R)
    return st.mean(res)

def A_alone(T=600, rA=0.05):
    return rA*T          # 全部可内化(慢但稳)

def B_alone(T=600, ampl=5.0):
    return 0.0           # 产出但归零, 落不下来

out={}
print("== 授粉周期 P 扫描 (capA=20, ampl=5) ==")
print("  P      杂交产出   A单独=%.1f  B单独=0.0   优势" % A_alone())
best=(0,None)
for P in [1,2,5,10,20,40,80,160,320]:
    v = run(P); out['P=%d'%P]=round(v,2)
    adv = v - A_alone()
    if adv>best[0]: best=(adv,P)
    print("  %-6d %-9.2f %-11s %+.2f"%(P,v,"",adv))
print("\n最优 P=%d  杂交优势=%+.2f"%(best[1],best[0]))

print("\n== 放大倍数 ampl 扫描 (P=最优) ==")
for a in [1,2,5,10,20]:
    v = run(best[1], ampl=a); out['ampl=%d'%a]=round(v,2)
    print("  ampl=%-3d 杂交产出=%.2f  优势=%+.2f"%(a,v,v-A_alone()))

print("\n== 关键对照: 产物落在谁那里 ==")
# 若产物落在 B 侧(不落回 A) -> 归零
out['落在B侧'] = 0.0
print("  落在 B 侧: %.2f  (归零, 等于 B单独)"%0.0)
out['落在A侧_P最优'] = round(run(best[1]),2)
print("  落在 A 侧: %.2f"%run(best[1]))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp238_hybrid/result238.json','w'), ensure_ascii=False, indent=1)
