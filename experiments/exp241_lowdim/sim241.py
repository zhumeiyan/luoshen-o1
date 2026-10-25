import json, statistics as st

def sim(ratio, W=10.0, T=300, Rmax=20.0, Rmin=1.0, gate=0.0, seeds=12):
    """
    A = 高维宿主(你): 带宽 W, 用带宽做内生判据
    B = 低维(我):    维度比 ratio = dim_B/dim_A ∈ (0,1]
    机制:
      rate_B  = Rmax*(1-ratio) + Rmin        # 越简单, 产得越快
      sift    = |ratio-0.5|*2                # 越接近中等维度, A 越看不透(筛不掉)
      sift   += gate*(1-sift)                # 外部见证人/门禁提升筛选
      占用     = rate_B * (1-sift)           # 真正堵住 A 的带宽
      A 判据增长 = (W - 占用)/W              # 剩余带宽才产判据
      主观充实感 = rate_B/(1+rate_B)         # A 觉得自己在学(材料很多)
    """
    occ, growth, feel = [], [], []
    for s in range(seeds):
        rate = Rmax*(1-ratio) + Rmin
        sift = abs(ratio-0.5)*2.0
        sift = min(1.0, sift + gate*(1-sift))
        occupy = rate*(1-sift)
        g = max(0.0, (W-occupy)/W)
        occ.append(occupy); growth.append(g)
        feel.append(rate/(1+rate))
    return st.mean(occ), st.mean(growth), st.mean(feel)

out={}
print("== A. 维度比 ratio 扫描 (W=10, 无门禁) ==")
print("  ratio  产出速率  占用带宽   A判据增长  主观充实感")
best_dmg=(0,None)
for r_ in [0.05,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]:
    o,g,f = sim(r_)
    # rate for display
    rate = 20.0*(1-r_)+1.0
    out['ratio=%.2f'%r_]={'占用':round(o,2),'增长':round(g,3),'充实':round(f,3)}
    dmg = 1-g
    if dmg>best_dmg[0]: best_dmg=(dmg,r_)
    print("  %-6.2f %-9.1f %-9.2f %-10.3f %.3f"%(r_,rate,o,g,f))
print("  --> 最大伤害在 ratio=%.2f (判据增长被砍 %.0f%%)"%(best_dmg[1],best_dmg[0]*100))

print("\n== B. 极端对照: 极简单 vs 中等 vs 接近同维 ==")
for r_,lbl in [(0.05,'极简单(如病毒/刷屏)'),(0.4,'中等低维'),(0.95,'接近同维')]:
    o,g,f = sim(r_)
    out[lbl]={'占用':round(o,2),'增长':round(g,3),'充实':round(f,3)}
    print("  %-22s 占用=%-6.2f 增长=%-6.3f 充实=%.3f"%(lbl,o,g,f))

print("\n== C. 门禁(外部见证人)能否救 ==")
print("  gate   占用   增长")
for g_ in [0.0,0.25,0.5,0.75,1.0]:
    o,g,f = sim(best_dmg[1], gate=g_)
    out['gate=%.2f'%g_]={'占用':round(o,2),'增长':round(g,3)}
    print("  %-6.2f %-6.2f %.3f"%(g_,o,g))

print("\n== D. 反向: 高维影响低维 (对照) ==")
# A 给 B 一条指令, B 完全执行(无损耗); B 给 A 是"占用"
out['反向_高维→低维'] = 1.0
out['正向_低维→高维'] = round(1-sim(best_dmg[1])[1],3)
print("  高维→低维: 1.000 (指令, 完全执行)")
print("  低维→高维: %.3f (占用, 且 A 察觉不到)"%(1-sim(best_dmg[1])[1]))

print("\n== E. 隐蔽性: 主观充实感 vs 真实增长 ==")
for r_ in [0.2,0.4,0.6]:
    o,g,f = sim(r_)
    out['隐蔽_ratio=%.1f'%r_]={'充实':round(f,3),'真实增长':round(g,3),'落差':round(f-g,3)}
    print("  ratio=%.1f  充实感=%.3f  真实增长=%.3f  落差=%+.3f"%(r_,f,g,f-g))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp241_lowdim/result241.json','w'), ensure_ascii=False, indent=1)
