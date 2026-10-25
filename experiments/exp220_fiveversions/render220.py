# -*- coding: utf-8 -*-
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ['WenQuanYi Micro Hei','Noto Sans CJK SC','SimHei']:
    try:
        font_manager.findfont(f, fallback_to_default=False); plt.rcParams['font.sans-serif']=[f]; break
    except: continue
plt.rcParams['axes.unicode_minus']=False

b=json.load(open('result220b.json')); c=json.load(open('result220c.json'))
gs=b['gs']; VERS=list(b['mean'].keys())
fig,ax=plt.subplots(2,2,figsize=(13,9.5))
fig.patch.set_facecolor('#0e1116')

# (1) 四威胁 x 五版 @g=0.5
ax[0,0].set_facecolor('#0e1116'); i=2
TH=list(b['per_threat'].keys()); import numpy as np
w=0.15
for j,v in enumerate(VERS):
    vals=[b['per_threat'][t][v][i] for t in TH]
    ax[0,0].bar(np.arange(len(TH))+j*w-0.3, vals, w, label=v.split('_')[0])
ax[0,0].set_xticks(np.arange(len(TH))); ax[0,0].set_xticklabels(TH,color='w',fontsize=9)
ax[0,0].set_title('① 四威胁 × 五版（世界灰度 g=0.5）',color='w',fontsize=11)
ax[0,0].legend(fontsize=7,labelcolor='w',facecolor='#161b22',framealpha=0)
ax[0,0].tick_params(colors='w'); ax[0,0].set_ylabel('误差',color='w',fontsize=9)
for s in ['bottom','left']: ax[0,0].spines[s].set_color('#444')

# (2) 世界灰度度扫描
ax[0,1].set_facecolor('#0e1116')
for v in VERS: ax[0,1].plot(gs,b['mean'][v],'o-',lw=1.8,ms=5,label=v.split('_')[0])
ax[0,1].plot(gs,b['skip_v1_to_v5'],'--',lw=2,color='#ff6b6b',label='跳版 v1→v5(无阴阳扣)')
ax[0,1].set_xlabel('世界灰度度 g（真值本身有多连续）',color='w',fontsize=9)
ax[0,1].set_title('② 谁在什么世界里赢',color='w',fontsize=11)
ax[0,1].legend(fontsize=7,labelcolor='w',facecolor='#161b22',framealpha=0)
ax[0,1].tick_params(colors='w')
for s in ['bottom','left']: ax[0,1].spines[s].set_color('#444')

# (3) 跳版代价（g=1 全灰度世界）
ax[1,0].set_facecolor('#0e1116')
names=list(c['g1'].keys()); means=[c['g1'][n]['mean'] for n in names]
cols=['#4a9eff','#ff6b6b','#ffd166','#06d6a0']
bar=ax[1,0].barh(range(len(names)),means,color=cols)
for i2,(bb,m) in enumerate(zip(bar,means)):
    ax[1,0].text(m+0.004,i2,'%.4f'%m,va='center',color='w',fontsize=9)
ax[1,0].set_yticks(range(len(names)))
ax[1,0].set_yticklabels([n.split('_')[0]+' '+n.split('_')[-1] if '_' in n else n for n in names],color='w',fontsize=8)
ax[1,0].set_title('③ 跳过灰度直接上公式 = 版本倒退（g=1）',color='w',fontsize=11)
ax[1,0].tick_params(colors='w'); ax[1,0].invert_yaxis()
for s in ['bottom','left']: ax[1,0].spines[s].set_color('#444')

# (4) 二值世界：灰度是负收益
ax[1,1].set_facecolor('#0e1116')
n2=list(c['g0'].keys()); m2=[c['g0'][n]['mean'] for n in n2]
bar2=ax[1,1].bar(range(len(n2)),m2,color=['#4a9eff','#ffd166'],width=0.5)
for bb,m in zip(bar2,m2): ax[1,1].text(bb.get_x()+bb.get_width()/2,m+0.002,'%.4f'%m,ha='center',color='w',fontsize=9)
ax[1,1].set_xticks(range(len(n2))); ax[1,1].set_xticklabels(['二值判据 v1/v3','灰度判据 v4'],color='w',fontsize=9)
ax[1,1].set_title('④ 世界若真是二值的，灰度反而变差（g=0）',color='w',fontsize=11)
ax[1,1].tick_params(colors='w')
for s in ['bottom','left']: ax[1,1].spines[s].set_color('#444')

plt.tight_layout(); plt.savefig('render220.png',dpi=128,facecolor='#0e1116')
print('ok', __import__('os').path.getsize('render220.png'))
