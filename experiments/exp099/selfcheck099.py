# -*- coding: utf-8 -*-
import json
"""做完自己看：把 099 的关键数字渲染上屏 -> 从帧缓冲真实采集 -> OCR 读回"""
import os, subprocess, random, hashlib, time
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
OUT=os.path.dirname(os.path.abspath(__file__))
FB='/dev/fb0'; W,H=1024,768
FONT='/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
if not os.path.exists(FONT): FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

rows=[("TACT 原文 三轴召回","L 77.8  M 95.5  P 85.7"),
      ("表面扰动 坐标改变","0 / 29  逐位不变"),
      ("换1词 坐标改变","6 / 20  = 30%"),
      ("换3词 坐标改变","10 / 20 = 50%"),
      ("换全部 坐标改变","11 / 20 = 55%"),
      ("L轴 77.8->50.0","-27.8 pt  最脆弱"),
      ("M轴 95.5->88.2","-7.3 pt  最稳"),
      ("可读性 0.86->0.68","Δ=-0.0056 CI跨0 无效应"),
      ("无感官->有感官","Δ=+2.565 CI[2.18,2.96]")]
code=''.join(random.choice('0123456789ABCDEF') for _ in range(6))
truth={'code':code}
img=Image.new('RGB',(W,H),(255,255,255)); d=ImageDraw.Draw(img)
f1=ImageFont.truetype(FONT,30); f2=ImageFont.truetype(FONT,26)
d.text((40,25),"099 TACT 跑起来之后 -- 判定依赖字面还是语义",font=f1,fill=(0,0,0))
y=90
for a,b in rows:
    d.text((50,y),a,font=f2,fill=(20,20,120)); d.text((540,y),b,font=f2,fill=(160,20,20)); y+=52
d.text((50,y+15),f"RANDOM CHECK = {code}",font=ImageFont.truetype(FONT,34),fill=(0,110,0))
img.save(os.path.join(OUT,'rendered099.png'))

# 写帧缓冲（32bpp BGRA）
arr=np.array(img.convert('RGB'))
canvas=np.zeros((H,W,4),np.uint8)
canvas[:H,:W,0]=arr[:,:,2]; canvas[:H,:W,1]=arr[:,:,1]; canvas[:H,:W,2]=arr[:,:,0]; canvas[:H,:W,3]=255
with open(FB,'wb') as f: f.write(canvas.tobytes())
time.sleep(0.4)
# 真实采集
with open(FB,'rb') as f: raw=f.read(W*H*4)
cap=np.frombuffer(raw,np.uint8).reshape(H,W,4)[:,:,[2,1,0]]
Image.fromarray(cap).save(os.path.join(OUT,'captured099.png'))
txt=subprocess.run(['tesseract',os.path.join(OUT,'captured099.png'),'stdout','--psm','6','-l','eng'],
                   capture_output=True,text=True).stdout
hit = code in txt.replace(' ','')
nums=[t for t in ['77.8','95.5','85.7','30%','50%','55%','2.565'] if t in txt.replace(' ','')]
print("校验码:",code,"| 采集回读命中:",hit)
print("数字命中:",nums,f"({len(nums)}/7)")
print("---OCR节选---"); print('\n'.join([l for l in txt.splitlines() if l.strip()][:12]))
json.dump({'code':code,'code_hit':bool(hit),'nums':nums},open(os.path.join(OUT,'selfcheck099.json'),'w'),ensure_ascii=False,indent=1)
