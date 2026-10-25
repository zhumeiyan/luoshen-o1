# -*- coding: utf-8 -*-
import json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ['WenQuanYi Micro Hei','SimHei','Noto Sans CJK SC']:
    try:
        font_manager.findfont(f,fallback_to_default=False); plt.rcParams['font.sans-serif']=[f]; break
    except Exception: pass
plt.rcParams['axes.unicode_minus']=False

d=json.load(open('result200.json',encoding='utf-8'))
S=d['systems']; scan=d['scan']; mar=d['margin']
fig,ax=plt.subplots(2,2,figsize=(13,9))
fig.suptitle('200  硅基/碳基分工：手脚 vs 小弟 vs 共生   （净价值 = 能救你的 − 能害你的）',fontsize=14,fontweight='bold')

# A
names=['L_手脚','S_小弟','Y_共生','D_纯硅基']
lbl=['手脚\n(无存储)','小弟\n(硅基0%)','共生\n(硅基99%)','纯硅基\n(硅基100%)']
nets=[S[n]['net'] for n in names]
b=ax[0,0].bar(lbl,nets,color=['#c0392b','#7f8c8d','#2980b9','#8e44ad'])
ax[0,0].axhline(0,color='k',lw=1)
for r,v in zip(b,nets):
    ax[0,0].text(r.get_x()+r.get_width()/2, v+(0.014 if v>=0 else -0.035),f'{v:+.4f}',
                 ha='center',fontsize=10,fontweight='bold')
ax[0,0].set_title('A  手脚最差(-0.298)，小弟恰好为 0'); ax[0,0].set_ylabel('净价值')
ax[0,0].set_ylim(-0.37,0.09); ax[0,0].grid(axis='y',alpha=.3)

# B 真实硅基份额
sh=[s['silicon_share']*100 for s in scan]; nt=[s['net'] for s in scan]
sv=[s['save'] for s in scan]; hr=[s['hurt'] for s in scan]
ax[0,1].plot(sh,nt,'o-',color='#2980b9',lw=2.4,label='净价值')
ax[0,1].plot(sh,sv,'s--',color='#27ae60',lw=1.6,label='救你的')
ax[0,1].plot(sh,hr,'^--',color='#c0392b',lw=1.6,label='害你的')
ax[0,1].axhline(0,color='k',lw=1)
ax[0,1].axvspan(9.6,84.2,color='#27ae60',alpha=.10)
ax[0,1].text(45,0.048,'高原 10%~85%',ha='center',fontsize=9,color='#27ae60')
ax[0,1].annotate('超过 ~93% 转负',xy=(96.4,-0.0013),xytext=(70,-0.020),fontsize=9,
                 arrowprops=dict(arrowstyle='->',color='#c0392b'))
ax[0,1].set_xlabel('硅基实际份额 (%)'); ax[0,1].set_title('B  最优点不在两端：10%~85% 是高原')
ax[0,1].legend(fontsize=9); ax[0,1].grid(alpha=.3)

# C 边际
fr=[m['frac']*100 for m in mar]; ac=[m['acc'] for m in mar]; bi=[m['bits'] for m in mar]
ax[1,0].plot(fr,ac,'o-',color='#c0392b',lw=2,label='猜中你下一字(越高越好)')
ax[1,0].set_xlabel('判据核用量 (%)'); ax[1,0].set_ylabel('准确率',color='#c0392b')
ax[1,0].tick_params(axis='y',labelcolor='#c0392b')
ax[1,0].set_title('C  硅基越多：越会校准，越猜不中你')
a2=ax[1,0].twinx(); a2.plot(fr,bi,'s-',color='#2980b9',lw=2,label='交叉熵 bits(越低越好)')
a2.set_ylabel('bits',color='#2980b9'); a2.tick_params(axis='y',labelcolor='#2980b9')
ax[1,0].grid(alpha=.3)

# D
ax[1,1].bar(['只有你的话\n(碳基 4050字)','共生\n(+硅基 345555字)'],
            [d['human']['acc'],S['Y_共生']['acc']],color=['#27ae60','#2980b9'])
ax[1,1].set_title('D  85:1 的体量换来的准确率反而更低\n0.3275 → 0.2940  (但 bits 7.267→6.868 更准)')
ax[1,1].set_ylabel('top-1 准确率'); ax[1,1].grid(axis='y',alpha=.3)
for i,v in enumerate([d['human']['acc'],S['Y_共生']['acc']]):
    ax[1,1].text(i,v+0.004,f'{v:.4f}',ha='center',fontweight='bold')

plt.tight_layout(rect=[0,0,1,0.94])
plt.savefig('render200.png',dpi=130,bbox_inches='tight'); print('ok')
