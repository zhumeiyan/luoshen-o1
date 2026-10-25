# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus']=False

fig,ax=plt.subplots(2,2,figsize=(13,9))
Ks=[0,5,10,20,40,60,80,100,150,200]
net=[294.3,320.9,319.3,316.6,312.2,301.9,292.8,278.4,218.9,35.2]
ax[0,0].plot(Ks,net,'o-',color='#c0392b',lw=2)
ax[0,0].axvline(5,ls='--',color='#2980b9')
ax[0,0].set_title('A 乱烧期 K 的中间带（预算200件）',fontsize=12)
ax[0,0].set_xlabel('先乱烧 K 件'); ax[0,0].set_ylabel('净值')
ax[0,0].annotate('纯乱烧 K=200\n净值崩到 35',xy=(200,35),xytext=(120,120),
                 arrowprops=dict(arrowstyle='->',color='#7f8c8d'),fontsize=9)

al=[0.8,1.5,3.0,6.0]; ks=[5,5,40,60]
ax[0,1].bar(range(4),ks,color=['#e67e22','#27ae60','#2980b9','#8e44ad'])
ax[0,1].set_xticks(range(4)); ax[0,1].set_xticklabels([f'α={a}' for a in al])
ax[0,1].set_title('B 世界越平坦，所需探索越多',fontsize=12)
ax[0,1].set_ylabel('最优探索期 K*')

sp=[0.2,0.5,1.0,2.0]; kk=[60,5,5,5]
ax[1,0].plot(sp,kk,'s-',color='#16a085',lw=2)
ax[1,0].set_title('C 组间差异越大，越少的乱烧就够',fontsize=12)
ax[1,0].set_xlabel('组间差异 spread'); ax[1,0].set_ylabel('K*')

aa=[0.8,1.0,1.5,2.0,3.0,6.0,12.0]; cc=[66.9,46.6,17.6,9.0,4.4,2.1,1.4]
ax[1,1].plot(aa,cc,'^-',color='#c0392b',lw=2)
ax[1,1].set_title('D 厚尾度 → 大奖集中度（top1%占总价值）',fontsize=12)
ax[1,1].set_xlabel('帕累托 α（越小越厚尾）'); ax[1,1].set_ylabel('占比 %')
plt.tight_layout(); plt.savefig('render229.png',dpi=110)
print('ok')
