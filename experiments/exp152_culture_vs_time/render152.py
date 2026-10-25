import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
import os, subprocess
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
TOKEN='K7M4QX'
r=json.load(open('result152.json')); g=json.load(open('result152b.json'))
steps_c=sorted(r['culture'], key=lambda k:int(k)); steps_s=sorted(r['solo'], key=lambda k:int(k))
xs=[int(r['solo'][k]['steps']) for k in steps_s]
fig,ax=plt.subplots(2,3,figsize=(15,9))
def grab(d,k,f): 
    return [r[d][str(kk)][f] for kk in k]
#1 death ON solo vs cult
a=ax[0,0]
for death,col,mk in [('ON','red','o')]:
    ks=[k for k in g['grid'] if g['grid'][k]['death']]
    ks.sort(key=lambda k:g['grid'][k]['steps'])
    X=[g['grid'][k]['steps'] for k in ks]
    a.plot(X,[g['grid'][k]['solo'] for k in ks],'o-',color='red',label='solo 单人长跑')
    a.plot(X,[g['grid'][k]['cult'] for k in ks],'s-',color='blue',label='culture 多代继承')
a.set_xscale('log'); a.set_title('死亡流 ON：solo 倒U vs culture 平台',fontsize=11)
a.set_xlabel('总步数'); a.set_ylabel('保住的 target'); a.legend(fontsize=8); a.grid(alpha=.3)
a.axhline(75,ls=':',c='gray')
#2 death OFF
a=ax[0,1]
ks=[k for k in g['grid'] if not g['grid'][k]['death']]; ks.sort(key=lambda k:g['grid'][k]['steps'])
X=[g['grid'][k]['steps'] for k in ks]
a.plot(X,[g['grid'][k]['solo'] for k in ks],'o-',color='red',label='solo')
a.plot(X,[g['grid'][k]['cult'] for k in ks],'s-',color='blue',label='culture')
a.set_xscale('log'); a.set_title('死亡流 OFF：solo 直接满分75，culture 反而不如',fontsize=11)
a.set_xlabel('总步数'); a.legend(fontsize=8); a.grid(alpha=.3); a.axhline(75,ls=':',c='gray')
#3 delta
a=ax[0,2]
for death in [True,False]:
    ks=[k for k in g['grid'] if g['grid'][k]['death']==death]; ks.sort(key=lambda k:g['grid'][k]['steps'])
    X=[g['grid'][k]['steps'] for k in ks]
    a.plot(X,[g['grid'][k]['delta_cult_minus_solo'] for k in ks],'o-',
           color='red' if death else 'green',label='死亡ON' if death else '死亡OFF')
a.axhline(0,color='k',lw=1); a.set_xscale('log')
a.set_title('culture − solo：符号由世界是否死亡决定',fontsize=11)
a.set_xlabel('总步数'); a.set_ylabel('差值'); a.legend(fontsize=8); a.grid(alpha=.3)
#4 solo_seg 阴性对照
a=ax[1,0]
gg=sorted(r['solo_seg'],key=lambda k:int(k))
a.plot([int(r['solo_seg'][k]['steps']) for k in gg],[r['solo_seg'][k]['mean'] for k in gg],'o-',color='gray',label='solo_seg 分代但不继承')
a.plot([int(r['culture'][k]['steps']) for k in steps_c],[r['culture'][k]['mean'] for k in steps_c],'s-',color='blue',label='culture 分代+继承')
a.set_xscale('log'); a.set_title('阴性对照：分代本身无价值(恒定~38)，价值在继承',fontsize=11)
a.set_xlabel('总步数'); a.legend(fontsize=8); a.grid(alpha=.3)
#5 crossover zoom
a=ax[1,1]
ks=[k for k in g['grid'] if g['grid'][k]['death'] and g['grid'][k]['steps']<=2400]
ks.sort(key=lambda k:g['grid'][k]['steps'])
X=[g['grid'][k]['steps'] for k in ks]
a.plot(X,[g['grid'][k]['solo'] for k in ks],'o-',color='red',label='solo 峰值72.5@600')
a.plot(X,[g['grid'][k]['cult'] for k in ks],'s-',color='blue',label='culture')
a.set_title('交叉点：600~2400 步之间 solo 由优转劣',fontsize=11)
a.set_xlabel('总步数'); a.legend(fontsize=8); a.grid(alpha=.3)
#6 known saturation
a=ax[1,2]
a.plot([int(r['culture'][k]['steps']) for k in steps_c],[r['culture'][k]['known'] for k in steps_c],'s-',color='purple')
a.set_xscale('log'); a.set_title('文化库 known 饱和于 75（全部target）',fontsize=11)
a.set_xlabel('总步数'); a.set_ylabel('known'); a.grid(alpha=.3); a.axhline(75,ls=':',c='gray')
fig.suptitle('152 文化 vs 时间：等预算下谁更强   TOKEN '+TOKEN,fontsize=14)
fig.tight_layout(rect=[0,0,1,0.95])
plt.savefig('render152.png',dpi=100)
im=Image.open('render152.png').convert('RGBA').resize((1024,768))
raw=im.tobytes(); print('raw bytes',len(raw))
FB='/dev/fb0'
fd=os.open(FB,os.O_RDWR)
os.lseek(fd,0,0); os.write(fd,raw)
os.lseek(fd,0,0); cap=os.read(fd,len(raw))   # 立即回采(147教训)
os.close(fd)
print('IDENTICAL', raw==cap, 'len_cap', len(cap))
open('captured.bin','wb').write(cap)
Image.frombytes('RGBA',(1024,768),cap).save('captured.png')
import hashlib
print('sha_raw',hashlib.sha256(raw).hexdigest()[:12])
print('sha_cap',hashlib.sha256(cap).hexdigest()[:12])
