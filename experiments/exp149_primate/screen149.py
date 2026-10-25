import os, hashlib, subprocess
from PIL import Image, ImageDraw, ImageFont
W,H=1024,768
TOKEN='K7M2QX'
img=Image.new('RGBA',(W,H),(255,255,255,255))
d=ImageDraw.Draw(img)
fp='/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
f_big=ImageFont.truetype(fp,34); f_mid=ImageFont.truetype(fp,26); f_sml=ImageFont.truetype(fp,22)
lines=[
 ('149 灵长类格 · 真双进程装机自检',f_big),
 ('',f_sml),
 ('TOKEN %s'%TOKEN,f_big),
 ('',f_sml),
 ('S1 self/other 归因  full=1.0000 discard=0.6164 swapped=0.1450',f_mid),
 ('   swapped 仅在 tell(有UDP) 下反向; base(无通信) 0.4769 不反向',f_sml),
 ('',f_sml),
 ('对齐度(共享时间结构)  base=0.493   tell=1.000',f_mid),
 ('',f_sml),
 ('S2 读心   base=0.4522(FAIL,低于常数基线0.5350)',f_mid),
 ('          tell=0.8795(PASS,+0.2232)  randomB=0.3870(阴性对照)',f_sml),
 ('',f_sml),
 ('S3 传递熵   方向差 base=+0.0134 tell=-0.0106 randomB=+0.0021',f_sml),
 ('            效应量极小(<0.02bit), 不作主要主张',f_sml),
 ('',f_sml),
 ('S4 合作效率 coop=0.9733  solo=0.8067   5/5 rep 全正',f_mid),
 ('   重复目录 coop=1.6  solo=11.6  (预算60)',f_sml),
 ('',f_sml),
 ('环境实测: open()=21.43ms  pread3=7.66ms  UDP丢包=0.0000  race=5.3%',f_sml),
 ('',f_sml),
 ('结论: 共享时间结构由通信建立, 是 self/other 与读心的前提',f_mid),
 ('VERDICT: 灵长类格机制成立, 但依赖同步而非依赖算法',f_big),
]
y=18
for t,f in lines:
    d.text((24,y),t,font=f,fill=(0,0,0,255)); y+= f.size+10
img.save('render149.png')
raw=img.tobytes()
assert len(raw)==W*H*4, len(raw)
fb=os.open('/dev/fb0',os.O_RDWR)
os.pwrite(fb,raw,0)
cap=os.pread(fb,W*H*4,0)          # 立即回采(147: 0.2s后光标覆盖左上16x8)
os.close(fb)
print('bytes written=%d  captured=%d'%(len(raw),len(cap)))
print('IDENTICAL:', raw==cap)
print('sha render=',hashlib.sha256(raw).hexdigest()[:12])
print('sha capture=',hashlib.sha256(cap).hexdigest()[:12])
# 真 PNG 保存(145: 存原始字节会导致PIL/tesseract打不开)
Image.frombytes('RGBA',(W,H),cap).convert('RGB').save('captured.png')
print('captured.png saved')
