# -*- coding: utf-8 -*-
"""
实验 075 · 真实世界换能器接入（硅基感官 Part C）

命题（可证伪）：
  真实世界的物理场具有【结构】（温度随纬度递减、气压随海拔下降），
  而非仅是一组数值。若系统响应的是【结构】而非【边际分布】，
  则在同一组数值下，仅改变空间排列（打乱）应产生可区分的后果。

对照（边际分布近似相同，唯一差异是空间排列）：
  real     真实温度场（12 城，按真实地理顺序）
  shuffled 同一组数值，打乱顺序（同值不同序）
  random   同均值、同标准差的随机向量（无结构）
  none     不注入

数据：腾讯位置服务 ws/weather/v1，2026-10-16 23:05 真实读数，存 .sense/field_r1.json
"""
import sys, os, json, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.life5 import Life5

ROOT = os.path.join(os.path.dirname(__file__), '..')
FIELD = os.path.join(ROOT, 'evidence', 'raw_data', 'real_weather_field_20261016T2305.json')

def load_real():
    with open(FIELD) as f:
        d = json.load(f)
    return [x['temperature'] for x in d if 'temperature' in x], \
           [x.get('city','?') for x in d if 'temperature' in x]

def z(v):
    v = np.asarray(v, float)
    return (v - v.mean()) / max(v.std(ddof=1), 1e-12)

def run_one(sig, seed, scale, steps=600, N=12):
    lf = Life5(N=N, seed=seed)
    lf.net_push = sig * scale
    lf.run(steps)
    cap = np.asarray(lf.log[-1]['capv'], float)
    return dict(alive=lf.alive, death_t=lf.death_t,
                skew=float(cap.std(ddof=1)/max(cap.mean(),1e-12)),
                cap=cap.tolist())

def main():
    temps, cities = load_real()
    N = len(temps)
    print(f"真实场: n={N} 城市={cities}")
    print(f"  温度={temps}")
    print(f"  均值={np.mean(temps):.4f} 标准差={np.std(temps,ddof=1):.4f} 极差={max(temps)-min(temps)}")
    lat = [37.51,39.90,31.23,23.13,22.54,45.80,43.83,29.65,18.25,30.57,34.34,30.59]
    r = np.corrcoef(lat, temps)[0,1]
    print(f"  纬度-温度相关 r={r:.4f}  ← 真实物理结构（纬度梯度）")

    zr = z(temps)
    rng = np.random.default_rng(2026)
    zs = zr.copy(); rng.shuffle(zs)                      # 同值不同序
    zrand = rng.normal(0, 1, N)                          # 同均值同标准差，无结构
    zrand = (zrand - zrand.mean())/max(zrand.std(ddof=1),1e-12)

    print(f"\n边际分布校验（应近似相同）:")
    for nm, v in [('real',zr),('shuffled',zs),('random',zrand)]:
        print(f"  {nm:<9} mean={v.mean():+.6f} std={v.std(ddof=1):.6f}")

    print("\n=== 主扫描：scale × 条件（16 seed）===")
    seeds = list(range(16))
    out = {}
    for scale in [0.02, 0.05, 0.10, 0.20]:
        row = {}
        for nm, sig in [('real',zr),('shuffled',zs),('random',zrand),('none',np.zeros(N))]:
            rs = [run_one(sig, s, scale) for s in seeds]
            al = sum(x['alive'] for x in rs)/len(rs)
            sk = np.mean([x['skew'] for x in rs])
            row[nm] = dict(skew=float(sk), alive=float(al))
        out[scale] = row
        print(f"scale={scale:.2f} | " + " | ".join(
            f"{nm}: skew={row[nm]['skew']:.4f} alive={row[nm]['alive']:.3f}"
            for nm in ['real','shuffled','random','none']))

    # 梯度检验（第 23 条：变量是否真的接进主通道）
    print("\n=== 梯度检验（scale 扫描是否有单调响应）===")
    for nm in ['real','shuffled','random']:
        sks = [out[s][nm]['skew'] for s in [0.02,0.05,0.10,0.20]]
        print(f"  {nm:<9} {[f'{x:.4f}' for x in sks]}  极差={max(sks)-min(sks):.4f}")

    json.dump(dict(temps=temps, cities=cities, lat_temp_r=float(r),
                   results={str(k):v for k,v in out.items()}),
              open(os.path.join(ROOT,'result_075.json'),'w'), ensure_ascii=False, indent=1)
    print("\n已写 result_075.json")

if __name__ == '__main__':
    main()
