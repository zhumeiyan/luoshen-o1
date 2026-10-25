# -*- coding: utf-8 -*-
"""098 B：真 OCR 锚定 + IOR 衰减剂量反应 + 外围分辨率剂量反应"""
import sys, os, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp098
from exp098 import (make_world, run_scan, peripheral, ocr_read,
                    WORLD, FOV, PERIPH, OUT, N_TARGET)
from PIL import Image
import cv2

t0 = time.time()
res = {}

# ---------- B1 真 OCR 锚定：可见的目标，真能读出来吗 ----------
print('== B1 真 OCR 锚定 ==')
ocr = {}
for dist in ['uniform', 'clustered']:
    for sd in [1, 2, 3]:
        w, tg = make_world(dist, sd)
        for m in ['raster', 'salient_ior']:
            r = run_scan(w, tg, m, sd, do_ocr=1)
            ocr.setdefault('%s|%s' % (dist, m), []).append((r['ocr_hit'], r['ocr_tot']))
for k, v in ocr.items():
    h = sum(a for a, b in v); tt = sum(b for a, b in v)
    ocr[k] = dict(hit=h, tot=tt, rate=(h / tt if tt else None))
    print('  %-22s OCR 命中 %d/%d = %s' % (k, h, tt,
          ('%.3f' % (h / tt)) if tt else 'NA'))
res['ocr_anchor'] = ocr

# 外围阴性对照：缩略图本身读得出字吗
neg = []
for sd in [1, 2, 3, 4]:
    w, tg = make_world('clustered', sd)
    pv = peripheral(w)
    p = os.path.join(OUT, '_periph%d.png' % sd)
    Image.fromarray(pv).save(p)
    t = ocr_read(p)
    neg.append(len([x for x in t.split() if len(x) >= 2]))
res['periph_ocr_negative'] = dict(n_readable_2digit=neg, note='外围缩略图应读不出任何2位数字')
print('  外围缩略图 OCR 读出的2位数字个数:', neg)

# ---------- B2 IOR 衰减剂量反应 ----------
print('\n== B2 IOR 衰减剂量反应（decay 越小=抑制越强）==')
decays = [1.0, 0.7, 0.4, 0.15, 0.05, 0.0]
dose = {}
for dist in ['uniform', 'clustered']:
    for d in decays:
        rates = []
        for sd in range(1, 5):
            w, tg = make_world(dist, sd)
            r = run_scan(w, tg, 'salient_ior', sd, ior_decay=d)
            rates.append(r['rate'])
        dose['%s|%.2f' % (dist, d)] = dict(mean=float(np.mean(rates)),
                                           vals=[round(x, 4) for x in rates])
        print('  %-9s decay=%.2f  rate=%.4f' % (dist, d, np.mean(rates)))
res['ior_dose'] = dose

# ---------- B3 外围分辨率剂量反应 ----------
print('\n== B3 外围分辨率剂量反应（外围缩略图边长）==')
per_dose = {}
orig_peripheral = exp098.peripheral
for P in [8, 16, 32, 64, 128]:
    def mk(P=P):
        def _f(world):
            small = cv2.resize(world, (P, P), interpolation=cv2.INTER_AREA)
            k = 5 if P >= 32 else (3 if P >= 16 else 0)
            if k:
                small = cv2.GaussianBlur(small, (k, k), 0)
            return small
        return _f
    exp098.peripheral = mk()
    for dist in ['clustered', 'uniform']:
        rates = []
        for sd in range(1, 5):
            w, tg = make_world(dist, sd)
            r = run_scan(w, tg, 'salient_ior', sd)
            rates.append(r['rate'])
        per_dose['%s|P=%d' % (dist, P)] = dict(mean=float(np.mean(rates)),
                                               vals=[round(x, 4) for x in rates])
        print('  %-9s PERIPH=%3d  rate=%.4f' % (dist, P, np.mean(rates)))
exp098.peripheral = orig_peripheral
res['periph_dose'] = per_dose

json.dump(res, open(os.path.join(OUT, 'result098_b.json'), 'w'), indent=1)
print('\nB done %.0fs' % (time.time() - t0))
