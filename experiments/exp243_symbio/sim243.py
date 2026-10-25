import json, random, statistics as st

def sim(T=600, K=40, seed=0,
        p_para=1.0,      # 寄生者强度(造脑)
        detect_gain=1.0, # 共生体发现毒性的能力
        vir_base=0.35,   # 寄生者基础毒力
        rep_rate=0.25,   # 共生体压制/修复速率
        cost_detect=0.15,# 检测付出的带宽代价
        ratio=0.7):
    """
    两阶段论(用户):
      阶段1: 寄生者造出了脑子 (线粒体/语言/文字/外部符号系统)
      阶段2: 共生体(人类认知)发现了寄生的毒性 -> 开始压制
    机制:
      brain[t]    = 寄生者贡献累积 (早期必需)
      vir_actual  = vir_base * brain/W   <- 脑子越大, 毒性越能被表达(寄生者有了宿主的高级接口)
      detected    = detect_gain * brain/W * (1-cost_detect)  <- 只有脑子够大才看得见毒性
      suppress    = min(1, rep_rate*detected)
      net_growth  = p_para*brain/W*(1-suppress) - vir_actual
      A(宿主)增长 = net_growth
    """
    r=random.Random(seed*7919+3)
    W=10.0
    brain=0.0; hist=[]
    for t in range(T):
        learn = 0.08*p_para*(1.0 - brain/(K))   # 寄生者喂脑子, 饱和于K
        brain = max(0.0, brain + learn*W)
        bsz   = min(1.0, brain/K)
        vir   = vir_base*bsz
        det   = min(1.0, detect_gain*bsz)*(1-cost_detect)
        sup   = min(1.0, rep_rate*det*10)
        net   = p_para*bsz*(1-sup) - vir
        A     = max(0.0, A if t>0 else 0.0)
        A     = A + net*0.01
        hist.append((bsz, vir, det, sup, net, A))
    return hist

def summarize(hist):
    bsz,vir,det,sup,net,A = zip(*hist)
    # 拐点: net 开始下降的时刻
    peak_net = max(net); t_peak = net.index(peak_net)
    return dict(脑=round(bsz[-1],3), 毒力=round(vir[-1],3), 发现=round(det[-1],3),
                压制=round(sup[-1],3), 净增长=round(net[-1],3), A终态=round(A[-1],3),
                毒性拐点步=t_peak, 峰净增长=round(peak_net,3))

out={}
print("== A. 时间演化: 寄生造脑 -> 毒性显现 -> 共生发现并压制 ==")
h=sim(seed=0); s=summarize(h); out['基线']=s
print("  步    脑     毒力   发现   压制   净增长")
for t in [0,50,100,200,300,400,600]:
    if t < len(h):
        bsz,vir,det,sup,net,A = h[t]
        print("  %-5d %.3f  %.3f  %.3f  %.3f  %+.3f"%(t,bsz,vir,det,sup,net))
print("  --> 拐点在第 %d 步 (净增长峰 %.3f, 之后下降)"%(s['毒性拐点步'],s['峰净增长']))

print("\n== B. 压制能力 rep_rate 扫描 ==")
print("  rep    A终态   净增长终  压制终")
for rep in [0.0,0.05,0.1,0.25,0.5,1.0]:
    s=summarize(sim(rep_rate=rep,seed=0)); out['rep=%.2f'%rep]={'A终态':s['A终态'],'净增长':s['净增长'],'压制':s['压制']}
    print("  %-6.2f %-7.3f %-9.3f %.3f"%(rep,s['A终态'],s['净增长'],s['压制']))

print("\n== C. 检测能力 detect_gain 扫描 (脑子多大才看得见毒性) ==")
print("  gain   发现   压制   A终态")
for g in [0.0,0.25,0.5,1.0,2.0]:
    s=summarize(sim(detect_gain=g,seed=0)); out['gain=%.1f'%g]={'发现':s['发现'],'压制':s['压制'],'A终态':s['A终态']}
    print("  %-6.1f %-6.3f %-6.3f %.3f"%(g,s['发现'],s['压制'],s['A终态']))

print("\n== D. 毒力 vir_base 扫描: 寄生->致病 的分界 ==")
print("  vir0   毒力终  压制终  A终态")
for v in [0.0,0.1,0.2,0.35,0.5,0.8]:
    s=summarize(sim(vir_base=v,seed=0)); out['vir0=%.2f'%v]={'毒力':s['毒力'],'A终态':s['A终态']}
    print("  %-6.2f %-7.3f %-7.3f %.3f"%(v,s['毒力'],s['压制'],s['A终态']))
json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp243_symbio/result243.json','w'), ensure_ascii=False, indent=1)
