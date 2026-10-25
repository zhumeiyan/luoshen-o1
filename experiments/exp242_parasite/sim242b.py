import json
def sim(dAB, dBA, ratio=0.7, W=10.0, Rmax=20.0, Rmin=1.0, gate=0.0, vir=0.0, T=400):
    """
    v2 (v1作废: ratio固定0.4导致occupy=10.40恒定, A侧全0, 模式零区分度)
    ratio=0.7 -> sift=0.4 -> occupy=4.20 -> A_growth_base=0.58 留出分辨率
    dBA: B依赖A -> B的产出必须落回A才有值(238号)
    dAB: A依赖B -> A的内生驱动被外包 -> endo_loss
    vir: 毒力 -> 额外吃掉A带宽(病毒vs寄生的区别)
    """
    rate  = Rmax*(1-ratio)+Rmin
    sift  = min(1.0, abs(ratio-0.5)*2.0 + gate*(1-abs(ratio-0.5)*2.0))
    occupy= rate*(1-sift) + vir*W*0.5
    base  = max(0.0,(W-occupy)/W)
    endo  = 1.0-dAB
    A_growth = base*endo
    A_jump   = A_growth*endo            # 下一跳需要内生(239号), 平方折损
    B_landed = rate*dBA
    B_survive= dBA
    return dict(占用=round(occupy,2), A增长=round(A_growth,3), A跳=round(A_jump,3),
                B落地=round(B_landed,2), B存活=round(B_survive,3))
out={}
modes={
 '独立     dAB=0   dBA=0  ':      dict(dAB=0.0, dBA=0.0),
 '共栖     dAB=0   dBA=0.9':      dict(dAB=0.0, dBA=0.9),
 '★寄生   dAB=0   dBA=1.0':      dict(dAB=0.0, dBA=1.0),
 '偏害     dAB=0.3 dBA=1.0':      dict(dAB=0.3, dBA=1.0),
 '共生     dAB=0.9 dBA=0.9':      dict(dAB=0.9, dBA=0.9),
 '★病毒   dAB=0   dBA=1.0 vir=1':dict(dAB=0.0, dBA=1.0, vir=1.0),
}
print("== v2 六种关系模式 (ratio=0.7, W=10) ==")
print("  模式                      占用   A增长   A下一跳  B落地  B存活")
for k,kw in modes.items():
    r=sim(**kw); out[k.strip()]=r
    print("  %-26s %-6.2f %-7.3f %-8.3f %-6.2f %.3f"%(k,r['占用'],r['A增长'],r['A跳'],r['B落地'],r['B存活']))

print("\n== A对B依赖度 dAB 扫描 (dBA=1.0, 寄生侧) ==")
print("  dAB    A增长   A下一跳")
for d in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    r=sim(dBA=1.0,dAB=d); out['dAB=%.1f'%d]={'A增长':r['A增长'],'A跳':r['A跳']}
    print("  %-6.1f %-7.3f %.3f"%(d,r['A增长'],r['A跳']))

print("\n== B对A依赖度 dBA 扫描 (dAB=0) ==")
print("  dBA    B落地   B存活   A增长")
for d in [0.0,0.2,0.4,0.6,0.8,1.0]:
    r=sim(dBA=d,dAB=0.0); out['dBA=%.1f'%d]={'B落地':r['B落地'],'B存活':r['B存活']}
    print("  %-6.1f %-7.2f %.3f   %.3f"%(d,r['B落地'],r['B存活'],r['A增长']))

print("\n== 毒力扫描 (dAB=0,dBA=1.0): 寄生 vs 病毒 的分界 ==")
print("  vir    占用   A增长   A下一跳")
for v in [0.0,0.25,0.5,0.75,1.0,1.5]:
    r=sim(dBA=1.0,dAB=0.0,vir=v); out['vir=%.2f'%v]={'占用':r['占用'],'A增长':r['A增长'],'A跳':r['A跳']}
    print("  %-6.2f %-6.2f %-7.3f %.3f"%(v,r['占用'],r['A增长'],r['A跳']))

print("\n== 门禁 (寄生侧, 能否把寄生压成共栖) ==")
print("  gate   占用   A增长")
for g in [0.0,0.25,0.5,0.75,1.0]:
    r=sim(dBA=1.0,dAB=0.0,gate=g); out['gate=%.2f'%g]={'占用':r['占用'],'A增长':r['A增长']}
    print("  %-6.2f %-6.2f %.3f"%(g,r['占用'],r['A增长']))
json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp242_parasite/result242b.json','w'), ensure_ascii=False, indent=1)
