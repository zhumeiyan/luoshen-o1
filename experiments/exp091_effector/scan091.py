import numpy as np, json
from optical_mouse2 import *

def batch_eta(eta, tex=0.02, n=30, noise_floor=0.01, led=1.0, glare=0.0, shift=(3,2)):
    """直接控制 eta 做剂量反应（脱离具名表面）"""
    p = dict(eta=eta, glare=glare, tex=tex)
    rng0 = np.random.default_rng(0)
    surf = np.clip(rng0.normal(0.5, tex, (160,160)), 0, 1)
    oks=[]; peaks=[]
    for s in range(n):
        rng = np.random.default_rng(s+999)
        f0,_ = cmos_frame(surf,p,60,60,18,led,noise_floor,rng)
        f1,_ = cmos_frame(surf,p,60+shift[0],60+shift[1],18,led,noise_floor,rng)
        img,peak = estimate_shift(f0,f1)
        peaks.append(peak)
        if img is None: oks.append(False); continue
        oks.append((-img[0],-img[1])==shift)
    return dict(eta=eta, acc=float(np.mean(oks)), peak=float(np.mean(peaks)))

def shift_scan(kind='pad', maxd=14, n=25):
    out=[]
    for d in range(0, maxd+1):
        r = batch(kind, (d, max(0,d//2)), n=n)
        out.append(dict(d=d, acc=r['acc'], err=r['err'], peak=r['peak']))
    return out

def led_rescue(kind='glass', leds=(1,2,4,8,16,32), n=30):
    out=[]
    for L in leds:
        r = batch(kind, (3,2), n=n, led=L)
        out.append(dict(led=L, acc=r['acc'], peak=r['peak'], sat=r['sat']))
    return out

if __name__=='__main__':
    print('=== A. 返回效率 eta 剂量反应 (tex=0.02, noise_floor=0.01) ===')
    etas=[0.001,0.002,0.005,0.01,0.02,0.04,0.08,0.16,0.32,0.64]
    A=[batch_eta(e) for e in etas]
    for r in A: print(f"  eta={r['eta']:<6} acc={r['acc']:.3f} peak={r['peak']:.4f}")

    print('\n=== B. 帧间位移扫描 (pad, win=18 => 可测范围 ±9) ===')
    B=shift_scan('pad', maxd=14, n=25)
    for r in B: print(f"  d={r['d']:<3} acc={r['acc']:.3f} peak={r['peak']:.4f}")

    print('\n=== C. 提高 LED 能否救回玻璃 ===')
    C=led_rescue('glass', n=30)
    for r in C: print(f"  led={r['led']:<3} acc={r['acc']:.3f} peak={r['peak']:.4f} sat={r['sat']:.3f}")

    json.dump(dict(A=A,B=B,C=C), open('scan091.json','w'), ensure_ascii=False, indent=1)
