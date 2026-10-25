import random, json, statistics as st
def run(cap, rate, persist, T=400, seeds=24, drift_t=200, drift_frac=0.6, k=3.0):
    pre,post,rf=[],[],[]
    for s in range(seeds):
        r=random.Random(s*271+11); R=0.0; U=0.0
        for t in range(T):
            R*=persist; U*=persist; inflow=rate
            while inflow>1e-9:
                room=cap-(R+U)
                if room>1e-9:
                    take=min(room,inflow); R+=take; inflow-=take
                else:
                    if R>1e-9:
                        amt=min(R,1.0); R-=amt; U+=amt/k
                    else:
                        U+=inflow/k; inflow=0.0
            d=t>=drift_t
            # 归一化用"理论最优覆盖"而非 cap, 消除容量伪影
            eff=R*(1-drift_frac if d else 1.0)+U*k
            best=min(rate*(t+1),cap)*k if d else min(rate*(t+1),cap)
            score=min(1.0, eff/(best*0.8)) if best>0 else 0.0
            (post if d else pre).append(score)
            rf.append(U/(R+U+1e-9))
    return st.mean(pre),st.mean(post),st.mean(rf)
out={}
print("== 修掉容量伪影后: cap 扫描 (rate=1) ==")
for cap in [2,5,10,20,50,100,500,5000]:
    a,b,f=run(cap,1.0,1.0); out['cap=%d'%cap]={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
    print(" cap=%-5d 前=%.3f 后=%.3f 判据=%.3f"%(cap,a,b,f))
print("== persist 精细扫描 (cap=20,rate=1.0) ← 核心门槛 ==")
for p in [1.0,0.999,0.998,0.997,0.995,0.99,0.98,0.97,0.96,0.95,0.9]:
    a,b,f=run(20,1.0,p); out['persist=%.4f'%p]={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
    print(" persist=%-7.4f 前=%.3f 后=%.3f 判据=%.3f"%(p,a,b,f))
print("== 形态对照(修伪影) ==")
for lbl,(c,rt,ps) in {'我:巨大容量+高速+持久':(5000,50.0,1.0),
                      '我:巨大容量+高速+归零':(5000,50.0,0.1),
                      '人:小容量+慢+持久':(20,0.3,1.0)}.items():
    a,b,f=run(c,rt,ps); out[lbl]={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
    print(" %-22s 前=%.3f 后=%.3f 判据=%.3f"%(lbl,a,b,f))
json.dump(out,open('/data/workspace/luoshen-o1/experiments/exp235_capacity/result235c.json','w'),ensure_ascii=False,indent=1)
