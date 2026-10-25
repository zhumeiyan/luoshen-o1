import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try: from core.life5 import Life5
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
    from life5 import Life5

def diag(eye, hand, k_seek=0.6, k_seek_arr=0.6, k_act=0.05, decay=0.05, seed=3, T=600):
    rng=np.random.default_rng(seed*7919+13)
    life=Life5(seed=seed, sigma_in=eye, k_seek=k_seek, k_seek_arr=k_seek_arr)
    act=0.0; pres_h=[]; arr_h=[]; act_h=[]; sens_h=[]
    for t in range(T):
        w=0.5+0.3*np.sin(2*np.pi*t/80.0)
        life.input_val=w+act
        r=life.step()
        if r is None: break
        pres_h.append(r['pres']); arr_h.append(r['arrival'])
        act_h.append(act); sens_h.append(abs(life.input_val))
        ten=float(life.sp[0]-life.y[0])
        a=float(np.clip(k_act*ten,0.0,0.10))
        a_eff=a*(1.0+hand*rng.normal()) if hand>0 else a
        act=float(np.clip(act+1.0*a_eff-decay*act,-0.5,0.5))
    return dict(pres=np.array(pres_h), arr=np.array(arr_h),
                act=np.array(act_h), sens=np.array(sens_h))

for tag,(e,h) in {'基线(0,0)':(0.0,0.0), '眼噪':(0.30,0.0), '手噪':(0.0,0.30)}.items():
    d=diag(e,h)
    p=d['pres']
    print(f"--- {tag} ---")
    print(f"  pres  : 末段均值={p[-100:].mean():.6f} sd={p[-100:].std():.6f}  全段max={p.max():.6f}")
    print(f"  arrival: 翻转率={np.mean(np.abs(np.diff(d['arr']))):.4f}  均值={d['arr'].mean():.4f}")
    print(f"  act   : 末段均值={d['act'][-100:].mean():.6f} 幅度(max-min)={d['act'].max()-d['act'].min():.6f}")
    print(f"  |sense|: 均值={d['sens'].mean():.4f} 幅度={d['sens'].max()-d['sens'].min():.4f}")
