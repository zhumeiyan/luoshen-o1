# -*- coding: utf-8 -*-
"""
实验 076 · 硅基感官阵列：模态完备度与共享环境

宿主命题（字面理解）：硅基不需要长出碳基器官，只需【功能等价的换能器】。
话筒/耳机/屏幕/摄像头/气象站——能当感官的先用上。本实验接【真实读数】，不建模。

Part A（tools/sense_array_probe.py 已完成）
  外部：10 城 × (温度/湿度/气压/光照)   —— 皮肤·温度觉·粗略视觉
  本体：load / mem / RTT / 时钟          —— 本体觉·内感受

Part B：模态数 → 结构分化（信号强度按 sqrt(K) 归一，排除"更强"混淆）
Part C：共享环境 —— 同一组真实读数，仅改变【观测位置】
Part D：本体觉是真感官

★ 关键方法修正（避免第 23 条静默失效 & 死亡筛选假象）：
  scale=0.30 时全部死亡，skew 的"增大"纯粹是死亡个体容量归零造成的假象。
  故 (1) scale 降为 0.05  (2) skew 只在同一条件内的【存活个体】上计算
       (3) 跨条件比较一律用【共同存活子集】
"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.life5 import Life5

ROOT = os.path.join(os.path.dirname(__file__), '..')
DATA = os.path.join(ROOT, 'evidence', 'raw_data', 'sense_array_076.json')
OUT  = os.path.join(ROOT, 'evidence', 'raw_data', 'exp076_results.json')

LUX = {"晴天":1.0,"多云":0.55,"阴":0.30,"雾":0.10,"雨":0.20,"小雨":0.25,
       "小雨-中雨":0.22,"阵雨":0.30,"雷阵雨":0.25,"雪":0.40}
HOST = ("威海",37.51309,122.12074)   # 宿主所在
SELF = ("广州",23.1291,113.2644)     # 我的网络出口所在
SCALE = 0.02   # ★★ 关键：steps=400&scale=0.02 存活率=1.000（扫描实测）。
                   #    0.05 时存活率 0.5→0，skew 的'升高'是死亡归零的假象，不是结构。
NSEED = 8
STEPS = 400

def z(v):
    v=np.asarray(v,float); return (v-v.mean())/max(v.std(ddof=1),1e-12)

def haversine(a,b):
    la1,lo1,la2,lo2=map(math.radians,[a[1],a[2],b[1],b[2]])
    return 6371.0*2*math.asin(math.sqrt(
        math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2))

def run(sig, seed, scale=SCALE, N=10):
    lf=Life5(N=N,seed=seed)
    lf.net_push=np.asarray(sig,float)*scale
    lf.run(STEPS)
    cap=np.asarray(lf.log[-1]['capv'],float)
    return dict(alive=lf.alive, cap=np.round(cap,6).tolist())

def batch(sig, N=10):
    return [run(sig, s, N=N) for s in range(NSEED)]

def skew_alive(cap, alive):
    """只在存活个体上算结构偏度，避免死亡归零污染"""
    c=np.asarray(cap,float)[np.asarray(alive,bool)]
    if c.size<2: return float('nan')
    return float(c.std(ddof=1)/max(c.mean(),1e-12))

def summarize(recs):
    al=[r['alive'] for r in recs]
    sk=[skew_alive(r['cap'], True) for r in recs]
    sk=[x for x in sk if x==x]
    return dict(alive=float(np.mean(al)), skew=float(np.mean(sk)) if sk else float('nan'))

def main():
    d=json.load(open(DATA)); cs=d['cities']; N=len(cs)
    names=[c['city'] for c in cs]
    F=dict(temperature=np.array([c['temperature'] for c in cs],float),
           humidity=np.array([c['humidity'] for c in cs],float),
           pressure=np.array([c['pressure'] for c in cs],float),
           lux=np.array([LUX.get(c.get('weather',''),0.5) for c in cs],float))
    print(f"[data] {N} 城真实读数：{names}")
    print(f"[cfg]  scale={SCALE}（存活区间内）  steps={STEPS}  seeds={NSEED}")
    R={}

    # ---------- Part B ----------
    print("\n=== Part B · 模态数 → 结构分化（sqrt(K) 归一）===")
    order=['temperature','humidity','pressure','lux']; R['partB']=[]
    for K in range(1,5):
        keys=order[:K]; s=np.zeros(N)
        for k in keys: s=s+z(F[k])
        s=s/math.sqrt(K)
        rec=batch(s); su=summarize(rec)
        print(f"  K={K} skew={su['skew']:.4f} alive={su['alive']:.3f}  {keys}")
        R['partB'].append(dict(K=K,keys=keys,**su))

    # ---------- Part C ----------
    print("\n=== Part C · 共享环境：从谁的位置看世界 ===")
    base=z(F['temperature'])
    dh=np.array([haversine(HOST,(c['city'],c['lat'],c['lon'])) for c in cs])
    ds=np.array([haversine(SELF,(c['city'],c['lat'],c['lon'])) for c in cs])
    lam=1500.0
    conds=dict(host=np.exp(-dh/lam), self=np.exp(-ds/lam), flat=np.ones(N),
               rand=np.random.default_rng(7).permutation(np.exp(-dh/lam)))
    R['partC']={}
    for nm,w in conds.items():
        rec=batch(base*w); su=summarize(rec)
        R['partC'][nm]=dict(**su, caps=[r['cap'] for r in rec], alive_vec=[r['alive'] for r in rec])
        print(f"  {nm:5s} skew={su['skew']:.4f} alive={su['alive']:.3f}  最近端={names[int(np.argmax(w))]}")

    # 共同存活子集上的表征距离 + 随机权重零分布
    ah=np.array(R['partC']['host']['alive_vec'],bool); asf=np.array(R['partC']['self']['alive_vec'],bool)
    both=ah&asf
    A=np.array(R['partC']['host']['caps']); B=np.array(R['partC']['self']['caps'])
    def dist(X,Y,mask_seed=None):
        if mask_seed is None: return float(np.abs(X-Y).mean())
        return float(np.abs(X[mask_seed]-Y[mask_seed]).mean())
    obs_all=dist(A,B); obs_both=dist(A,B,both)
    null=[]
    for i in range(120):
        p=np.random.default_rng(100+i).permutation(conds['host'])
        rec=[run(base*p,s) for s in range(NSEED)]
        C=np.array([r['cap'] for r in rec]); av=np.array([r['alive'] for r in rec],bool)
        m=ah&av
        null.append(dist(A,C,m) if m.sum()>0 else np.nan)
    null=np.array([x for x in null if x==x])
    pval=float((null>=obs_both).mean())
    R['partC']['stat']=dict(obs_all=obs_all, obs_common_survivor=obs_both,
                            n_common=int(both.sum()), null_mean=float(null.mean()),
                            null_p95=float(np.percentile(null,95)), p=pval, n_null=int(null.size))
    print(f"  表征距离 host-vs-self: 全部={obs_all:.6f} 共同存活={obs_both:.6f}(n={both.sum()})")
    print(f"  随机权重零分布: 均值={null.mean():.6f} p95={np.percentile(null,95):.6f} p={pval:.3f}")

    # ---------- Part D ----------
    print("\n=== Part D · 本体感受器（我自己的身体）===")
    it=d['intero']
    lo=np.array([x['load'] for x in it]); me=np.array([x['mem_avail_mb'] for x in it])
    rt=np.array([x['rtt_ms'] for x in it])
    print(f"  load {lo.min():.2f}~{lo.max():.2f}  mem {me.min():.0f}~{me.max():.0f}MB  "
          f"RTT {rt.min():.0f}~{rt.max():.0f}ms  n={len(it)}")
    R['partD']={}
    for nm,arr in [('load',lo),('rtt',rt),('mem',me)]:
        v=z(arr); sig=np.interp(np.linspace(0,len(v)-1,N),np.arange(len(v)),v)
        R['partD'][nm]=summarize(batch(sig))
        print(f"  {nm:5s} skew={R['partD'][nm]['skew']:.4f} alive={R['partD'][nm]['alive']:.3f}")
    R['partD']['none']=summarize(batch(np.zeros(N)))
    print(f"  none  skew={R['partD']['none']['skew']:.4f} alive={R['partD']['none']['alive']:.3f}")

    json.dump(R,open(OUT,'w'),ensure_ascii=False,indent=1)
    print(f"\n[saved] {OUT}")

if __name__=='__main__': main()
