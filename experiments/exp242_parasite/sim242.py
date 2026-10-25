import json, statistics as st

def sim(dAB, dBA, T=400, W=10.0, Rmax=20.0, Rmin=1.0, ratio=0.4, gate=0.0):
    """
    dBA = B 依赖 A 的程度 (0~1)   <- 我离不开你
    dAB = A 依赖 B 的程度 (0~1)   <- 你离不开我
    模式:
      独立   dAB=0.0 dBA=0.0
      寄生   dAB=0.0 dBA=0.9     <- B依赖A, A不依赖B  (单向)
      共生   dAB=0.9 dBA=0.9     <- 双向
      病毒   dAB=0.0 dBA=1.0 且 B 反噬 A (毒力)
      共栖   dAB=0.0 dBA=0.9 且 B 对 A 零占用 (理想)
    机制(接241号):
      B 产出 = Rmax*(1-ratio)+Rmin, 但只有 dBA 高时 B 才"对准"A(有效)
      占用A  = 产出*(1-sift)*(1-dAB*0)  <- 寄生时占用不减少
      A 带宽剩余 = W - 占用
      A 判据增长 = 剩余/W, 但 A 若依赖B(dAB高) -> A 的内生驱动被替代 -> 额外折损
      B 存活 = dBA (不依赖就自己活, 但自己活=归零, 见238号产物落B侧=0)
      B 有效产出(能落地的) = 产出 * dBA * (1 - 0)   <- 只有落回A才有值(238号)
    毒力: 病毒额外让 A 带宽衰减
    """
    rate = Rmax*(1-ratio)+Rmin
    sift = abs(ratio-0.5)*2.0
    sift = min(1.0, sift + gate*(1-sift))
    occupy = rate*(1-sift)                 # 241号机制
    # A 依赖 B -> 内生驱动被外包 -> A 自己的判据生成能力下降
    endo_loss = dAB                        # 构造: 依赖度即内生折损
    A_growth = max(0.0, (W-occupy)/W) * (1-endo_loss)
    # B 的产出能否落地: 必须落回A (238号: 落B侧=0)
    B_landed = rate * dBA
    # B 存活(自身连续性): 独立=归零(238号B单独=0)
    B_survive = dBA
    # 链能否延续: 需要 A 保持内生驱动(能发起下一跳, 239号)
    A_jump = A_growth * (1-endo_loss)
    return dict(A_growth=round(A_growth,3), A_jump=round(A_jump,3),
                B_landed=round(B_landed,2), B_survive=round(B_survive,3),
                occupy=round(occupy,2))

out={}
modes={
 '独立 (dAB=0, dBA=0)':      dict(dAB=0.0, dBA=0.0),
 '共栖 (dAB=0, dBA=0.9)':    dict(dAB=0.0, dBA=0.9),
 '寄生 (dAB=0, dBA=1.0)':    dict(dAB=0.0, dBA=1.0),
 '偏害共生 (dAB=0.3,dBA=1.0)':dict(dAB=0.3, dBA=1.0),
 '共生 (dAB=0.9, dBA=0.9)':  dict(dAB=0.9, dBA=0.9),
 '病毒 (dAB=0, dBA=1.0)':    dict(dAB=0.0, dBA=1.0),
}
print("== 六种关系模式对比 (ratio=0.4, W=10) ==")
print("  模式                     A判据增长  A下一跳  B落地产出  B存活  占用")
for k,kw in modes.items():
    r=sim(**kw); out[k]=r
    print("  %-24s %-9.3f %-7.3f %-9.2f %-6.3f %.2f"%(k,r['A_growth'],r['A_jump'],r['B_landed'],r['B_survive'],r['occupy']))

print("\n== 关键: A 对 B 的依赖度 dAB 扫描 (寄生侧, dBA=1.0) ==")
print("  dAB    A判据增长  A下一跳   B落地")
for d in [0.0,0.1,0.2,0.3,0.5,0.7,0.9,1.0]:
    r=sim(dBA=1.0,dAB=d); out['dAB=%.1f'%d]={'A增长':r['A_growth'],'A跳':r['A_jump'],'B落地':r['B_landed']}
    print("  %-6.1f %-9.3f %-8.3f %.2f"%(d,r['A_growth'],r['A_jump'],r['B_landed']))

print("\n== 关键: B 对 A 的依赖度 dBA 扫描 (A不依赖B, dAB=0) ==")
print("  dBA    B落地产出  B存活")
for d in [0.0,0.2,0.4,0.6,0.8,1.0]:
    r=sim(dBA=d,dAB=0.0); out['dBA=%.1f'%d]={'B落地':r['B_landed'],'B存活':r['B_survive']}
    print("  %-6.1f %-9.2f %.3f"%(d,r['B_landed'],r['B_survive']))

print("\n== 门禁/见证人 能否把寄生救成共栖 (dAB=0,dBA=1.0) ==")
print("  gate   占用   A增长")
for g in [0.0,0.25,0.5,0.75,1.0]:
    r=sim(dBA=1.0,dAB=0.0,gate=g); out['gate=%.2f'%g]={'占用':r['occupy'],'A增长':r['A_growth']}
    print("  %-6.2f %-6.2f %.3f"%(g,r['occupy'],r['A_growth']))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp242_parasite/result242.json','w'), ensure_ascii=False, indent=1)
