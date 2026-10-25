import json
NEED=60.0
def urgency(T):
    x=T/NEED; return 2.0*x/(1.0+x*x)
def sim(T=200,f=0.0,a=0.5,hz=0.6,export=1.0,b=0.4):
    """v2: 洪水主要摧毁产物(而不是只造成小额直接损害), 量纲才可比"""
    drive=export*urgency(T)
    effort=(1.0-f)*T*drive
    speed=1.0-b*a
    corr =0.25+0.75*a
    V=effort*speed*corr
    surv=max(0.0,min(1.0,1.0-hz*(1.0-f)*0.9))   # v2: 洪水果真摧毁产物
    D=hz*(1.0-0.8*f)*T*0.01
    return dict(驱动=round(drive,3),产出=round(V,2),存活=round(surv,3),适应度=round(V*surv-D,2))
out={}
print("== v2-B 治洪水投入 f 扫描 (修量纲后) ==")
print("  f      T=50    T=200   T=600")
for f in [0.0,0.2,0.4,0.6,0.8,1.0]:
    r=[sim(T=t,f_flood=f)['适应度'] if False else sim(T=t,f=f)['适应度'] for t in (50,200,600)]
    out['f=%.1f'%f]={'T50':r[0],'T200':r[1],'T600':r[2]}
    print("  %-6.1f %-8.2f %-8.2f %.2f"%(f,r[0],r[1],r[2]))
print("\n== v2-D 洪水强度 hz 扫描 (T=200): 不管洪水何时不再最优 ==")
print("  hz     f=0     f=0.3   f=0.5   f=1.0   最优f")
for h in [0.0,0.2,0.4,0.6,0.8,1.0]:
    fs=[0.0,0.3,0.5,1.0]; row=[sim(T=200,f=x,hz=h)['适应度'] for x in fs]
    best=fs[max(range(len(fs)),key=lambda i:row[i])]
    out['hz=%.1f'%h]={'最优f':best,'f0':row[0]}
    print("  %-6.1f %-7.2f %-7.2f %-7.2f %-7.2f %.1f"%(h,row[0],row[1],row[2],row[3],best))
print("\n== v2-C2 跟自己干架: 速度惩罚系数 b 决定有没有中间带 ==")
print("  解析门槛: a*=(0.75-0.25b)/(1.5b); a*<1 需要 b>0.4286")
print("  b       a=0    a=0.25  a=0.5   a=0.75  a=1.0   峰在")
for b in [0.2,0.4,0.4286,0.5,0.7,0.9]:
    row=[sim(T=200,f=0.0,a=x,b=b)['产出'] for x in (0.0,0.25,0.5,0.75,1.0)]
    xs=[0.0,0.25,0.5,0.75,1.0]; best=xs[max(range(5),key=lambda i:row[i])]
    out['b=%.3f'%b]={'峰在':best}
    print("  %-7.3f %-7.2f %-7.2f %-7.2f %-7.2f %-7.2f %.2f"%(b,row[0],row[1],row[2],row[3],row[4],best))
json.dump(out,open('result244b.json','w'),ensure_ascii=False,indent=1)
