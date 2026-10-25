#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE=os.path.dirname(os.path.abspath(__file__))
for p in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
          '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc']:
    if os.path.exists(p):
        font_manager.fontManager.addfont(p); break
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus']=False

b=json.load(open(os.path.join(BASE,'result175b.json'),encoding='utf-8'))
c=json.load(open(os.path.join(BASE,'result175c.json'),encoding='utf-8'))

fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,4.6))

# 左: 对齐程度 (随机划分, 排除时间局部性)
ps=[10,20,30,50,75,100]
acc=[c['res'][str(p)]['mean']['2'] for p in ps]
ax1.plot(ps,acc,'o-',color='#c0392b',lw=2,ms=7,label='k=2 (随机划分,20种子平均)')
# 175b 时间划分对照
ps2=[5,10,20,30,50,75,100]
acc2=[b['对齐程度扫描'][str(p)]['2']['acc'] for p in ps2]
ax1.plot(ps2,acc2,'s--',color='#7f8c8d',lw=1.4,ms=5,label='k=2 (按时间取前p%)')
ax1.axhline(0.0271,color='#2980b9',ls=':',lw=1.6,label='M→U 不对齐基线 0.0271')
ax1.set_xlabel('对齐程度: 我看见你多少 %')
ax1.set_ylabel('预测你的下一个字 · top-1 准确率')
ax1.set_title('看见得越多 → 预测越准\n(边际递减: +.036 → +.023 → +.015)')
ax1.legend(fontsize=8); ax1.grid(alpha=.3)

# 右: 四组对照 vs k
names={'U->U_对齐':'#c0392b','M+U->U_混合':'#e67e22',
       'M->M_自预测':'#27ae60','M->U_不对齐':'#2980b9','U->M_反向':'#8e44ad'}
ks=list(range(1,7))
for nm,col in names.items():
    row=b['跨侧_修正ppl'][nm]
    ax2.plot(ks,[row[str(k)]['acc'] for k in ks],'o-',color=col,lw=1.8,ms=5,label=nm)
ax2.set_xlabel('阶数 k (对齐深度)')
ax2.set_ylabel('top-1 准确率')
ax2.set_title('转角都在 k=2\n对齐 0.2303 vs 不对齐 0.0271 = 8.5x')
ax2.legend(fontsize=8); ax2.grid(alpha=.3)

plt.tight_layout()
plt.savefig(os.path.join(BASE,'render175.png'),dpi=130)
print('saved')
