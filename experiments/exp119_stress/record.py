"""119-C 预录真实本体觉序列：配对实验要求三种策略吃到逐位相同的输入。"""
import json, time, sys
sys.path.insert(0, '.')
from soma import snapshot, CHANNELS

N = 48
rec = []
print('=== 119-C 预录真实本体觉 ===')
for i in range(N):
    s = snapshot()
    rec.append(s)
    if i % 8 == 0:
        print(f'  t={i:3d} load1={s["load1"]} memavail={s["memavail"]} rtt='
              f'{None if s["rtt"] is None else round(s["rtt"],2)}')
    time.sleep(0.08)

json.dump(rec, open('trace_real.json','w'))
vals = {k: [r[k] for r in rec] for k in rec[0]}
print()
print('录得 %d 拍，逐通道可分辨性（真/假都要能产生才算不饱和）：' % N)
for k, v in vals.items():
    g = [x for x in v if x is not None]
    if not g:
        print(f'  {k:10s} 全 None -> 通道死'); continue
    print(f'  {k:10s} n={len(g):2d}/{N} min={min(g):.4g} max={max(g):.4g} '
          f'range={max(g)-min(g):.4g} 变化={len(set(round(x,6) for x in g))>1}')
