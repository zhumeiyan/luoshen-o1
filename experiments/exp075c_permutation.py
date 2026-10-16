# -*- coding: utf-8 -*-
"""
实验 075c · 置换检验：真实物理场 vs 排列零分布

修正 075b 的设计缺陷：只打乱【一次】(n=1) 不能代表"打乱"这个条件。
正确做法：把真实场放进【随机排列的零分布】里，看它的位置。
这是置换检验（permutation test）——可证伪、统计正确。

H0: 系统只响应数值集合，不响应空间排列
    → real 的存活率/结构偏度应落在排列零分布之内
H1: 系统响应空间结构
    → real 显著偏离零分布
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.life5 import Life5

ROOT=os.path.join(os.path.dirname(__file__),'..')
F=os.path.join(ROOT,'evidence','raw_data','real_weather_field_20261016T2305.json')
d=json.load(open(F))
temps=[x['temperature'] for x in d if 'temperature' in x]
cities=[x.get('city','?') for x in d if 'temperature' in x]
N=len(temps)
def z(v):
    v=np.asarray(v,float); return (v-v.mean())/max(v.std(ddof=1),1e-12)
zr=z(temps)

SEEDS=list(range(12)); SCALE=0.012; STEPS=600
def run(sig,seed):
    lf=Life5(N=N,seed=seed); lf.net_push=sig*SCALE; lf.run(STEPS)
    cap=np.asarray(lf.log[-1]['capv'],float)
    return lf.alive, float(cap.std(ddof=1)/max(cap.mean(),1e-12))
def evaluate(sig):
    rs=[run(sig,s) for s in SEEDS]
    return float(np.mean([a for a,_ in rs])), float(np.mean([k for _,k in rs]))

print(f"真实场 n={N} 温度={temps}")
print(f"配置: scale={SCALE} seeds={len(SEEDS)} steps={STEPS}")

real_alive, real_skew = evaluate(zr)
print(f"\n真实场(real): 存活率={real_alive:.4f} 结构偏度={real_skew:.4f}")

print("\n=== 生成排列零分布（40 个随机排列）===")
rng=np.random.default_rng(20261016)
null_a=[]; null_k=[]
for i in range(40):
    p=zr.copy(); rng.shuffle(p)
    a,k=evaluate(p); null_a.append(a); null_k.append(k)
null_a=np.array(null_a); null_k=np.array(null_k)
print(f"零分布 存活率: 均值={null_a.mean():.4f} 标准差={null_a.std(ddof=1):.4f} "
      f"范围[{null_a.min():.3f},{null_a.max():.3f}]")
print(f"零分布 结构偏度: 均值={null_k.mean():.4f} 标准差={null_k.std(ddof=1):.4f} "
      f"范围[{null_k.min():.3f},{null_k.max():.3f}]")

def perm_p(obs, null):
    # 双侧置换 p 值
    return float((np.sum(np.abs(null-null.mean())>=abs(obs-null.mean()))+1)/(len(null)+1))

pa=perm_p(real_alive,null_a); pk=perm_p(real_skew,null_k)
za=(real_alive-null_a.mean())/max(null_a.std(ddof=1),1e-12)
zk=(real_skew-null_k.mean())/max(null_k.std(ddof=1),1e-12)
pct_a=float(np.mean(null_a<real_alive)*100)
print(f"\n=== 置换检验结果 ===")
print(f"存活率:    real={real_alive:.4f}  z={za:+.4f}  百分位={pct_a:.1f}%  p={pa:.4f}")
print(f"结构偏度:  real={real_skew:.4f}  z={zk:+.4f}  p={pk:.4f}")

# 机制检验：真实场的梯度强度 vs 排列
lat=np.array([37.51,39.90,31.23,23.13,22.54,45.80,43.83,29.65,18.25,30.57,34.34,30.59])
def grad(v):  # 与纬度的相关强度（真实物理梯度的度量）
    return float(np.corrcoef(lat,v)[0,1])
print(f"\n=== 机制：真实场为何特殊 ===")
print(f"real 与纬度相关 r={grad(temps):+.4f}")
grads=[]
rng2=np.random.default_rng(999)
for i in range(40):
    p=zr.copy(); rng2.shuffle(p); grads.append(grad(p))
grads=np.array(grads)
print(f"排列零分布 纬度相关: 均值={grads.mean():+.4f} 标准差={grads.std(ddof=1):.4f} "
      f"范围[{grads.min():+.3f},{grads.max():+.3f}]")
print(f"real 的 |r| 在零分布百分位: {np.mean(np.abs(grads)<abs(grad(temps)))*100:.1f}%")

json.dump(dict(temps=temps,cities=cities,scale=SCALE,seeds=len(SEEDS),
  real=dict(alive=real_alive,skew=real_skew),
  null_alive=null_a.tolist(), null_skew=null_k.tolist(),
  p_alive=pa,p_skew=pk,z_alive=float(za),z_skew=float(zk),
  lat_r=grad(temps), null_lat_r=grads.tolist()),
  open(os.path.join(ROOT,'result_075c.json'),'w'),ensure_ascii=False,indent=1)
print("\n已写 result_075c.json")
