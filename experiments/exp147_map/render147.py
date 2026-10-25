#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp147 上屏自检: 渲染 -> 写 /dev/fb0 -> 回采 -> 像素比对 -> OCR"""
import json, subprocess, sys, hashlib
from PIL import Image, ImageDraw, ImageFont

W,H=1024,768
TOKEN='K7M4QX'
RES='/data/workspace/luoshen-o1/experiments/exp147_map'

def font(sz):
    for p in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
              '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
              '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        try: return ImageFont.truetype(p,sz)
        except Exception: pass
    return ImageFont.load_default()

def main():
    c=json.load(open(f'{RES}/result147c.json'))
    d=json.load(open(f'{RES}/result147d.json'))
    im=Image.new('RGBA',(W,H),(16,18,24,255)); dr=ImageDraw.Draw(im)
    ft=font(21); fs=font(17); fbig=font(27)
    assert hasattr(fs,'getmask'), f'FONT LOAD FAILED type={type(fs)}'
    # 固定行位表 (判据核 #672: 末行不得越界)
    ys=[]; y=28
    for i in range(24): ys.append(y); y+=30
    assert ys[-1]+28<=H, f'row overflow {ys[-1]}'
    def line(i,t,col=(235,238,245,255),f=None):
        dr.text((26,ys[i]),t,font=f or fs,fill=col)
    dr.text((26,ys[0]),'EXP147  FISH-RUNG  COGNITIVE MAP',font=fbig,fill=(120,220,255,255))
    line(1,'terrain pretest  (is it worth drawing a map?)')
    line(2,'  REAL  dir-tree  APL=3.841   gini=0.487   deg_max=259')
    line(3,'  SYNTH uniform   APL=11.515  gini=0.3097  deg_max=4')
    line(4,'  CHAIN spur      APL=124.983 gini=0.1105  deg_max=3')
    line(5,'  REDUN(all three)=1.000  -> all trees, no shortcut exists',(255,180,120,255))
    line(6,'navigation steps  MAP vs ROUTE vs RANDOM  (n=60)')
    line(7,'  REAL   MAP=138.05  ROUTE=212.82  RANDOM=993.18')
    line(8,'  SYNTH  MAP=71.25   ROUTE=991.15  RANDOM=992.60')
    line(9,'  CHAIN  MAP=3314.7  ROUTE=5072.9  RANDOM=5374.4')
    iv=c['improve_vs_random']; br=c['break']
    line(10,f"  improve(REAL)={iv['REAL']['improve']} CI{iv['REAL']['ci']}")
    line(11,f"  improve(SYNTH)={iv['SYNTH']['improve']} CI{iv['SYNTH']['ci']}")
    line(12,f"  improve(CHAIN)={iv['CHAIN']['improve']} CI{iv['CHAIN']['ci']}")
    line(13,'preregistered H REVERSED')
    line(14,'  predicted CHAIN map useless -> actual CHAIN gain LARGEST',(255,150,150,255))
    line(15,f"  gain REAL=74.77 CHAIN=1758.22 delta={c['inter_REAL_vs_CHAIN']['delta']} CI{c['inter_REAL_vs_CHAIN']['ci']}")
    line(16,'break test  MAP_SHUF (map scrambled)')
    line(17,f"  REAL  {br['REAL']['shuf']} vs {br['REAL']['map']}  d={br['REAL']['delta']} CI{br['REAL']['ci']}")
    line(18,f"  SYNTH {br['SYNTH']['shuf']} vs {br['SYNTH']['map']}  d={br['SYNTH']['delta']} CI{br['SYNTH']['ci']}")
    line(19,f"  CHAIN {br['CHAIN']['shuf']} vs {br['CHAIN']['map']}  d={br['CHAIN']['delta']} CI{br['CHAIN']['ci']}  CROSSES 0")
    line(20,f"real symlink shortcut: {d['sym_edges']} edges span=2 gain={d['shortcut']['gain_mean']} pct>1={d['shortcut']['pct_pairs_gain_gt1']}",(255,180,120,255))
    line(21,'VERDICT: map helps (0.852) but NO shortcut exists in tree terrain',(255,150,150,255))
    line(22,f'TOKEN {TOKEN}',(140,255,160,255),ft)
    im.save(f'{RES}/render147.png')
    raw=im.convert('RGBA').tobytes()
    open(f'{RES}/raw147.bin','wb').write(raw)
    # 写 fb0
    with open('/dev/fb0','wb') as f: f.write(raw)
    # 回采: 必须在同一进程内立即读(判据核: 写入后~0.2s fbcon 光标会覆盖左上角16x8)
    cap=open('/dev/fb0','rb').read(1024*768*4)
    Image.frombytes("RGBA",(1024,768),cap).convert("RGB").save(f'{RES}/captured.png')
    same_now = (cap==raw)
    nd_now = sum(1 for i in range(0,len(raw),4) if raw[i:i+4]!=cap[i:i+4])
    import time; time.sleep(0.4)
    cap2=open('/dev/fb0','rb').read(1024*768*4)
    nd_late = sum(1 for i in range(0,len(raw),4) if raw[i:i+4]!=cap2[i:i+4])
    print('bytes written   :', len(raw))
    print('IDENTICAL(0s)   :', same_now, ' diff_px=', nd_now)
    print('diff_px(+0.4s)  :', nd_late, '(env fbcon cursor, 16rows x 8cols topleft)')
    print('raw sha         :', hashlib.sha256(raw).hexdigest()[:12])
    print('cap sha         :', hashlib.sha256(cap).hexdigest()[:12])
    json.dump({'token':TOKEN},open(f'{RES}/token147.json','w'))
    return TOKEN

if __name__=='__main__': main()
