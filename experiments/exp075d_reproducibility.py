# -*- coding: utf-8 -*-
"""
实验 075d · 真实世界接入 ⇒ 可复现性丧失（核心张力）

本项目一直以"逐位可复现"为卖点：同一 seed 跑两次，输出逐位相同。
那是【封闭系统】（信号由 seed 生成）。

一旦把换能器接到真实世界，信号由【世界】给出，不再由 seed 决定。
命题（可证伪）：
  封闭（合成信号）：跨运行逐位相同
  开放（真实信号）：世界读数若变化，输出随之变化 → 不可复现

方法：在两个时刻采样真实场，比较读数与引擎输出。
"""
import sys,os,json,time,urllib.request
import numpy as np
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..'))
from core.life5 import Life5
ROOT=os.path.join(os.path.dirname(__file__),'..')
CITIES=[("威海",37.51309,122.12074),("北京",39.9042,116.4074),("上海",31.2304,121.4737),
 ("广州",23.1291,113.2644),("深圳",22.5431,114.0579),("哈尔滨",45.8038,126.5349),
 ("乌鲁木齐",43.8256,87.6168),("拉萨",29.6520,91.1721),("三亚",18.2528,109.5119),
 ("成都",30.5728,104.0668),("西安",34.3416,108.9398),("武汉",30.5928,114.3055)]
def sample():
    out=[]
    for n,la,lo in CITIES:
        try:
            u=f"https://apis.map.qq.com/ws/weather/v1/?location={la},{lo}"
            d=json.loads(urllib.request.urlopen(u,timeout=10).read().decode())
            rt=d["result"]["realtime"][0]; inf=rt["infos"]
            out.append(dict(city=n,district=rt["district"],update_time=rt["update_time"],
                temperature=inf["temperature"],humidity=inf["humidity"],
                air_pressure=inf["air_pressure"],weather=inf["weather"]))
        except Exception as e:
            out.append(dict(city=n,error=str(e)))
        time.sleep(0.2)
    return out

f1=json.load(open(os.path.join(ROOT,'evidence','raw_data','real_weather_field_20261016T2305.json')))
print(f"T1 (已存) update_time={f1[0]['update_time']}")
print("  正在采样 T2 ...")
f2=sample()
ok=[x for x in f2 if 'temperature' in x]
print(f"T2 采样成功 {len(ok)}/{len(CITIES)}  update_time={ok[0]['update_time'] if ok else 'N/A'}")

# 比较两轮读数
print("\n=== 真实世界读数：T1 vs T2 ===")
changed=0; total=0
for a,b in zip(f1,f2):
    if 'temperature' not in b: continue
    total+=1
    diffs=[]
    for k in ['temperature','humidity','air_pressure','weather']:
        if a.get(k)!=b.get(k): diffs.append(f"{k}:{a.get(k)}→{b.get(k)}")
    if diffs:
        changed+=1
        print(f"  {a['city']:<5} {'; '.join(diffs)}")
if changed==0: print("  观测窗口内读数无变化")
print(f"\n变化的感受器: {changed}/{total}")

# 可复现性检验：同一 seed，用 T1 场 vs T2 场 驱动
def z(v):
    v=np.asarray(v,float); return (v-v.mean())/max(v.std(ddof=1),1e-12)
def run(sig,seed,scale=0.012,steps=600):
    lf=Life5(N=len(sig),seed=seed); lf.net_push=sig*scale; lf.run(steps)
    cap=np.asarray(lf.log[-1]['capv'],float)
    return lf.alive,float(cap.std(ddof=1)/max(cap.mean(),1e-12)),cap

t1=[x['temperature'] for x in f1 if 'temperature' in x]
t2=[x['temperature'] for x in f2 if 'temperature' in x]
h1=[x['humidity'] for x in f1 if 'humidity' in x]
h2=[x['humidity'] for x in f2 if 'humidity' in x]
print(f"\n=== 可复现性检验（同 seed=3）===")
for nm,(A,B) in [('温度场',(t1,t2)),('湿度场',(h1,h2))]:
    if len(A)!=len(B) or len(A)<2: continue
    zA,zB=z(A),z(B)
    if np.allclose(zA,zB):
        a1,k1,c1=run(zA,3); a2,k2,c2=run(zB,3)
        print(f"  {nm}: T1≡T2 → 输出逐位相同={np.allclose(c1,c2)} "
              f"(alive {a1}/{a2}, skew {k1:.6f}/{k2:.6f})  ← 封闭窗口内仍可复现")
    else:
        a1,k1,c1=run(zA,3); a2,k2,c2=run(zB,3)
        print(f"  {nm}: T1≠T2 → 输出改变: Δskew={k2-k1:+.6f} 逐位相同={np.allclose(c1,c2)} "
              f"← 【不可复现】")
# 对照：合成信号（seed 决定）必然逐位相同
rng=np.random.default_rng(3); sz=rng.normal(0,1,len(t1)); sz=(sz-sz.mean())/sz.std(ddof=1)
a1,k1,c1=run(sz,3); a2,k2,c2=run(sz,3)
print(f"  合成信号(seed=3) 两次运行: 逐位相同={np.allclose(c1,c2)} (skew {k1:.6f}/{k2:.6f})")

json.dump(dict(t1=f1,t2=f2,changed=changed,total=total),
  open(os.path.join(ROOT,'evidence','raw_data','real_weather_T1_T2.json'),'w'),ensure_ascii=False,indent=1)
print("\n已存 evidence/raw_data/real_weather_T1_T2.json")
