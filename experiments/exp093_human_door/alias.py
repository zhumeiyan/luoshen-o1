import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__),'..','..'))
from core.life5 import Life5
STEPS, PERIOD = 600, 80
KSA, KACT, DECAY = 0.35, 0.05, 0.05
E0, BASAL = 0.95, 0.001
N = 48
def mk(seed): return Life5(seed=seed, sigma_in=0.10, k_seek=0.0, k_seek_arr=KSA, arr_thr=0.50, E0=E0, basal=BASAL)
def run(seed, period):
    life=mk(seed); frozen=0.5; act=0.0
    for t in range(STEPS):
        w=float(0.5+0.3*np.sin(2*np.pi*t/PERIOD))
        if (t % period) < (period//2): frozen=w
        life.input_val=float(frozen)+act
        r=life.step()
        if r is None: break
        ten=float(life.sp[0]-life.y[0]); a=float(np.clip(KACT*ten,0.0,0.10))
        act=float(np.clip(act+a-DECAY*act,-0.5,0.5))
    c=life.capacity
    return float(np.std(c)/max(np.mean(c),1e-12))
PER=[10,20,30,40,60,80,100,120,160,200]
res={p: float(np.mean([run(s,p) for s in range(N)])) for p in PER}
print('period  skew')
base=res[20]
for p in PER:
    mark=' <== 信号周期' if p==PERIOD else ''
    print(f'{p:5d}  {res[p]:.6f}{mark}')
peak=max(res,key=res.get)
print(f'\n峰值 period = {peak}  (信号周期={PERIOD})')
print(f'峰值/基线 = {res[peak]/base:.3f}')
# 是否只有 80 附近显著高
others=[res[p] for p in PER if p!=80]
print(f'非80组 mean={np.mean(others):.6f} std={np.std(others):.6f}')
print(f'80 的 z = {(res[80]-np.mean(others))/max(np.std(others),1e-12):.2f}')
json.dump(res,open('alias_result.json','w'),indent=1)
