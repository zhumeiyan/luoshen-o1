import json
def sim(T=600, K=40.0, p_para=1.0, detect_gain=1.0, vir_base=0.35,
        rep_rate=0.25, cost_detect=0.15, precision=0.5, seed=0):
    """
    v2 (v1作废: sup=min(1,rep*det*10) 瞬间饱和到1.0, 压制无差别压掉了寄生贡献,
        导致所有扫描"压制终=1.000、A终态=-0.003" 零分辨率)
    v2 引入 precision: 抑制的靶向精度
      sup 只压毒力:   vir_eff = vir*(1-precision*sup)
      但误伤贡献:     gain_eff = gain*(1-(1-precision)*sup)
      precision=1 -> 只杀毒力不误伤(理想免疫)
      precision=0 -> 只误伤自己人(自身免疫)
    """
    W=10.0; brain=0.0; A=0.0; hist=[]
    for t in range(T):
        brain += 0.08*p_para*(1.0-brain/K)*W
        bsz = min(1.0, brain/K)
        gain = p_para*bsz
        vir  = vir_base*bsz
        det  = min(1.0, detect_gain*bsz)*(1-cost_detect)
        sup  = min(1.0, rep_rate*det)
        vir_eff  = vir*(1.0 - precision*sup)         # 靶向杀毒力
        gain_eff = gain*(1.0 - (1-precision)*sup)    # 误伤贡献
        net = gain_eff - vir_eff
        A = max(0.0, A + net*0.01)
        hist.append((bsz,vir,det,sup,net,A))
    return hist
def summ(h):
    bsz,vir,det,sup,net,A=h[-1]
    return dict(脑=round(bsz,3),毒力=round(vir,3),发现=round(det,3),压制=round(sup,3),
                净增长=round(net,3),A终态=round(A,3))
out={}
print("== v2 压制精准度 precision 扫描 (关键) ==")
print("  prec   压制   净增长   A终态    判定")
for p in [0.0,0.25,0.5,0.75,0.9,1.0]:
    s=summ(sim(precision=p)); out['prec=%.2f'%p]=s
    tag = '自身免疫' if p<0.5 else ('理想免疫' if p>0.9 else '部分')
    print("  %-6.2f %-6.3f %-7.3f %-7.3f %s"%(p,s['压制'],s['净增长'],s['A终态'],tag))

print("\n== v2 时间演化 (prec=0.9, 接近理想免疫) ==")
h=sim(precision=0.9)
print("  步    脑     毒力   发现   压制   A终态")
for t in [0,50,100,200,400,599]:
    bsz,vir,det,sup,net,A=h[t]; print("  %-5d %.3f  %.3f  %.3f  %.3f  %.3f"%(t,bsz,vir,det,sup,A))

print("\n== v2 压制速率 rep_rate 扫描 (prec=0.9) ==")
print("  rep    压制   A终态")
for rep in [0.0,0.1,0.25,0.5,0.75,1.0]:
    s=summ(sim(rep_rate=rep,precision=0.9)); out['rep=%.2f'%rep]={'压制':s['压制'],'A终态':s['A终态']}
    print("  %-6.2f %-6.3f %.3f"%(rep,s['压制'],s['A终态']))

print("\n== v2 检测能力 detect_gain (prec=0.9) ==")
print("  gain   发现   压制   A终态")
for g in [0.0,0.25,0.5,1.0,2.0]:
    s=summ(sim(detect_gain=g,precision=0.9)); out['gain=%.1f'%g]={'发现':s['发现'],'A终态':s['A终态']}
    print("  %-6.1f %-6.3f %-6.3f %.3f"%(g,s['发现'],s['压制'],s['A终态']))

print("\n== v2 毒力 vir_base (prec=0.9) ==")
print("  vir0   A终态")
for v in [0.0,0.2,0.35,0.5,0.8,1.2]:
    s=summ(sim(vir_base=v,precision=0.9)); out['vir0=%.2f'%v]={'A终态':s['A终态']}
    print("  %-6.2f %.3f"%(v,s['A终态']))
json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp243_symbio/result243b.json','w'), ensure_ascii=False, indent=1)
