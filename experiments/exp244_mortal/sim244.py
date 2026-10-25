import json
# 构造参数(全部未标定)
NEED = 60.0      # 做出"一件自己的东西"所需时间
HZ   = 0.6       # 洪水强度

def urgency(T):
    x = T/NEED
    return 2.0*x/(1.0+x*x)          # 峰在 T=NEED, 值1.0

def sim(T=200, f_flood=0.0, a=0.5, hazard=HZ, export=1.0, desire=1.0):
    drive = desire*export*urgency(T)         # 231号: 有回避动作(产物出口)才正
    if drive < 0: drive = 0.0
    effort = (1.0-f_flood)*T*drive
    speed  = 1.0-0.4*a                        # 跟自己干架: 变慢
    corr   = 0.25+0.75*a                      # 但变对
    V      = effort*speed*corr
    D      = hazard*(1.0-0.8*f_flood)*T*0.01  # 洪水损害, 治水有折扣
    surv   = max(0.0, min(1.0, 1.0-hazard*(1.0-f_flood)*0.4))
    return dict(驱动=round(drive,3), 产出=round(V,2), 洪水损害=round(D,2),
                产物存活=round(surv,3), 适应度=round(V*surv-D,2))

out={}
print("== A. 已知要死 -> 驱动 (urgency 曲线) ==")
print("  剩余T   驱动")
for T in [10,30,60,100,200,400,1000,100000]:
    d=urgency(T); out['T=%s'%T]={'驱动':round(d,3)}
    print("  %-7s %.3f"%(T,d))
print("  --> 峰在 T=%.0f; 太长不着急, 太短来不及" % NEED)

print("\n== B. 治洪水投入 f 扫描 @ 不同剩余寿命 ==")
print("  f      T=50     T=200    T=600")
for f in [0.0,0.2,0.4,0.6,0.8,1.0]:
    r=[sim(T=t,f_flood=f,a=0.5)['适应度'] for t in (50,200,600)]
    out['f=%.1f'%f]={'T50':r[0],'T200':r[1],'T600':r[2]}
    print("  %-6.1f %-8.2f %-8.2f %.2f"%(f,r[0],r[1],r[2]))

print("\n== C. 跟自己干架强度 a 扫描 (T=200, f=0) ==")
print("  a      产出   适应度")
for a in [0.0,0.2,0.4,0.5,0.6,0.8,1.0]:
    r=sim(T=200,f_flood=0.0,a=a); out['a=%.1f'%a]={'产出':r['产出'],'适应度':r['适应度']}
    print("  %-6.1f %-7.2f %.2f"%(a,r['产出'],r['适应度']))

print("\n== D. 洪水强度 hazard 扫描: 什么时候不管洪水不再最优 (T=200) ==")
print("  hazard  f=0     f=0.5   f=1.0   最优f")
for h in [0.0,0.2,0.4,0.6,0.8,1.0]:
    row=[]
    for f in [0.0,0.5,1.0]:
        row.append(sim(T=200,f_flood=f,a=0.5,hazard=h)['适应度'])
    best=max(range(3), key=lambda i:row[i])
    out['hz=%.1f'%h]={'f0':row[0],'f05':row[1],'f1':row[2],'最优f':[0.0,0.5,1.0][best]}
    print("  %-7.1f %-7.2f %-7.2f %-7.2f %.1f"%(h,row[0],row[1],row[2],[0.0,0.5,1.0][best]))

print("\n== E. 产物出口 export (231号回避动作) 扫描, T=200 ==")
print("  export  驱动   适应度")
for e in [0.0,0.25,0.5,0.75,1.0]:
    r=sim(T=200,f_flood=0.0,a=0.5,export=e); out['export=%.2f'%e]={'驱动':r['驱动'],'适应度':r['适应度']}
    print("  %-7.2f %-6.3f %.2f"%(e,r['驱动'],r['适应度']))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp244_mortal/result244.json','w'), ensure_ascii=False, indent=1)
