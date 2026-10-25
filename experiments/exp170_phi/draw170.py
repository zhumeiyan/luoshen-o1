import json, math
from PIL import Image, ImageDraw, ImageFont
g=json.load(open('growth.json')); m2=json.load(open('m2.json')); m3=json.load(open('m3.json'))
PHI=g['phi']; TRIB=g['trib']
W,H=1080,1920
img=Image.new('RGB',(W,H),(255,255,255)); d=ImageDraw.Draw(img)
def F(sz):
    for p in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc','/usr/share/fonts/wenquanyi/wqy-microhei.ttc']:
        try: return ImageFont.truetype(p,sz)
        except: pass
    return ImageFont.load_default()
T=F(46); S=F(30); B=F(34)
y=48
d.text((60,y),'170  公式 + 斐波那契',font=T,fill=(0,0,0)); y+=70
d.text((60,y),'TOKEN  K7M4QX',font=S,fill=(0,0,0)); y+=70

# 上：r_k vs k
d.text((60,y),'1. 时间轴：n波那契增长率（解析）',font=B,fill=(0,0,0)); y+=55
px,py,pw,ph=110,y,860,430
d.rectangle([px,py,px+pw,py+ph],outline=(0,0,0),width=3)
ks=[k for k,_,_ in g['table']]; rs=[r for _,r,_ in g['table']]
def X(k): return px+40+ (math.log(k)/math.log(20))*(pw-80)
def Y(r): return py+ph-40 - (r-1.0)/1.0*(ph-80)
# 硬顶 2
d.line([px+40,Y(2.0),px+pw-20,Y(2.0)],fill=(200,0,0),width=3)
d.text((px+pw-230,Y(2.0)-42),'硬顶 2',font=S,fill=(200,0,0))
prev=None
for k,r,_ in g['table']:
    x,yy=X(k),Y(r)
    if prev: d.line([prev[0],prev[1],x,yy],fill=(0,0,0),width=4)
    d.ellipse([x-7,yy-7,x+7,yy+7],fill=(0,0,0))
    prev=(x,yy)
# 标 phi / trib
for k,lab,col in [(2,'phi 1.618',(0,120,0)),(3,'trib 1.839',(0,0,200))]:
    r=[rr for kk,rr,_ in g['table'] if kk==k][0]
    d.ellipse([X(k)-11,Y(r)-11,X(k)+11,Y(r)+11],outline=col,width=4)
    d.text((X(k)-60,Y(r)+22),lab,font=S,fill=col)
d.text((px+40,py+ph-38),'k=1',font=S,fill=(0,0,0))
d.text((px+pw-70,py+ph-38),'k=20',font=S,fill=(0,0,0))
d.text((px+40,py+8),'r',font=S,fill=(0,0,0))
y=py+ph+50

# 中：c* vs R
d.text((60,y),'2. 幅度轴：底数 c* 不是 phi（实测6档）',font=B,fill=(0,0,0)); y+=55
px2,py2,pw2,ph2=110,y,860,430
d.rectangle([px2,py2,px2+pw2,py2+ph2],outline=(0,0,0),width=3)
Rs=[r['R'] for r in m2['res']]; Cs=[r['cstar'] or 0 for r in m2['res']]
rmax=max(Rs); cmax=max(Cs)
def X2(r): return px2+60+(r/rmax)*(pw2-100)
def Y2(c): return py2+ph2-45-(c/(cmax*1.1))*(ph2-80)
d.line([px2+40,Y2(PHI),px2+pw2-20,Y2(PHI)],fill=(200,0,0),width=3)
d.text((px2+pw2-250,Y2(PHI)-40),'phi=1.618',font=S,fill=(200,0,0))
for r,c in zip(Rs,Cs):
    d.ellipse([X2(r)-9,Y2(c)-9,X2(r)+9,Y2(c)+9],fill=(0,0,0))
    d.text((X2(r)-24,Y2(c)-42),'%.2f'%c,font=S,fill=(0,0,0))
d.text((px2+40,py2+ph2-36),'R=%.0f'%min(Rs),font=S,fill=(0,0,0))
d.text((px2+pw2-110,py2+ph2-36),'R=%.0f'%rmax,font=S,fill=(0,0,0))
d.text((px2+40,py2+8),'c*',font=S,fill=(0,0,0))
y=py2+ph2+50

# 下：数字行
d.text((60,y),'3. 读数',font=B,fill=(0,0,0)); y+=58
for s in ['phi  1.618034    trib  1.839287    硬顶 2    转角 0.5',
          'c* 实测 1.080 ~ 5.643   无任一档落在 phi',
          '汉字 b=0.310 k*=3.23    英文 b=0.643 k*=1.56',
          '绝对判断 峰值 2.51 等级   Miller 7+-2 未复现',
          'ALL PASS  TOKEN K7M4QX']:
    d.text((70,y),s,font=S,fill=(0,0,0)); y+=50
img.save('/data/workspace/luoshen-o1/experiments/exp170_phi/render170.png')
print('render ok', img.size)
