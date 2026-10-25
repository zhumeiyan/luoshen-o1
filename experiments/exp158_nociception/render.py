#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染结果到 /dev/fb0 并立即回采自检（0.2s 后 fbcon 会覆盖左上角）"""
import json, os, hashlib
from PIL import Image, ImageDraw, ImageFont
W,H=1024,768
F="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
def fnt(s):
    try: return ImageFont.truetype(F,s)
    except: return ImageFont.load_default()

d=json.load(open('result_s1.json'))
sw=json.load(open('result_sweep.json'))
hb=json.load(open('result_hab.json'))
hy=json.load(open('result_hyper.json'))

im=Image.new('RGB',(W,H),(255,255,255)); dr=ImageDraw.Draw(im)
dr.rectangle([0,0,W-1,H-1],outline=(0,0,0),width=3)
y=14
dr.text((24,y),"exp158 痛觉 NOCICEPTION",font=fnt(34),fill=(0,0,0)); y+=50
dr.text((24,y),"感官里唯一 不想有但不能没有 的那一类",font=fnt(24),fill=(80,80,80)); y+=40
dr.line([24,y,W-24,y],fill=(0,0,0),width=2); y+=16

dr.text((24,y),"S1 四臂 传感器在 vs 痛觉驱动行为",font=fnt(25),fill=(0,0,0)); y+=34
for k,lab in [('normal','痛觉 抢占'),('queue','排队 不抢占'),('cipa','记账 不修'),('nosensor','无传感器')]:
    v=d[k]
    dr.text((34,y),"%-14s alive %5.2f   gain %5.2f   cascade %4.1f"%(lab,v['alive_mean'],v['gain_mean'],v['cascade_mean']),font=fnt(23),fill=(0,0,0)); y+=29
dr.text((34,y),"cipa与nosensor逐位相同 不通向行动的信息价值为零",font=fnt(22),fill=(180,0,0)); y+=32

dr.text((24,y),"S2 紧迫性相图 normal-queue 存活差",font=fnt(24),fill=(0,0,0)); y+=34
x0=300
dr.text((34,y),"delay\\p",font=fnt(22),fill=(0,0,0))
for j,p in enumerate([0.2,0.4,0.6]):
    dr.text((x0+j*120,y),"p=%.1f"%p,font=fnt(22),fill=(0,0,0))
y+=30
for cd in [2,12]:
    dr.text((34,y),"delay=%-3d"%cd,font=fnt(21),fill=(0,0,0))
    for j,p in enumerate([0.2,0.4,0.6]):
        e=sw['cd%d_p%.1f'%(cd,p)]
        t="%+5.2f %s"%(e['d_alive'],'W' if e['worth'] else '-')
        dr.text((x0+j*120,y),t,font=fnt(21),fill=(0,140,0) if e['worth'] else (120,120,120))
    y+=26
dr.text((34,y),"W 仅出现在 紧迫delay<=4 或 高损伤p>=0.6",font=fnt(21),fill=(180,0,0)); y+=32

dr.text((24,y),"S3 真实习惯化 感官=/proc真实读取",font=fnt(24),fill=(0,0,0)); y+=34
for k,lab in [('habit','习惯化'),('pain','不可习惯')]:
    v=hb[k]
    dr.text((34,y),"%-10s alive %5.2f 检查 %6.1f 漏检 %5.2f"%(lab,v['alive_mean'],v['checked_mean'],v['miss_mean']),font=fnt(22),fill=(0,0,0)); y+=30
dr.text((34,y),"省3.5倍采样开销 代价是全灭",font=fnt(21),fill=(180,0,0)); y+=30

dr.text((24,y),"S4 过敏=资源重分配 不是过度反应",font=fnt(24),fill=(0,0,0)); y+=34
for p in ['0.3','0.5','0.7']:
    c=hy['p%s_const'%p]; h=hy['p%s_hyper'%p]
    ec=c['checked_mean']/max(0.5,c['alive_mean']); eh=h['checked_mean']/max(0.5,h['alive_mean'])
    dr.text((34,y),"p=%s const %.1f  hyper %.1f  %s"%(p,ec,eh,'省' if eh<ec else '亏'),font=fnt(22),fill=(0,0,0)); y+=28

assert y < H-60, "内容越界 y=%d > %d" % (y, H-60)
dr.line([24,H-58,W-24,H-58],fill=(0,0,0),width=2)
dr.text((24,H-52),"TOKEN K7M4QX",font=fnt(30),fill=(0,0,0))
print('OK final y', y, '<', H-60, ' TOKEN at', H-52)
im.save('render158.png')

raw=im.convert('RGBA').tobytes()
assert len(raw)==W*H*4, len(raw)
fb=open('/dev/fb0','wb'); fb.write(raw); fb.flush(); os.fsync(fb.fileno())
cap=open('/dev/fb0','rb').read(W*H*4)   # 立即回采
print('IDENTICAL', cap==raw, 'raw_sha', hashlib.sha256(raw).hexdigest()[:12],
      'cap_sha', hashlib.sha256(cap).hexdigest()[:12])
Image.frombytes('RGBA',(W,H),cap).convert('RGB').save('captured.png')
print('saved captured.png')
