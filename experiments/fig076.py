# -*- coding: utf-8 -*-
import json,os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
ROOT=os.path.join(os.path.dirname(__file__),'..')
c=json.load(open(os.path.join(ROOT,'evidence','raw_data','exp076c_results.json')))
b=json.load(open(os.path.join(ROOT,'evidence','raw_data','exp076b_results.json')))
geo=np.array(c['geo']); rep=np.array(c['rep'])
gc=np.array(c['geo_ctrl']); rc=np.array(c['rep_ctrl'])
fig,ax=plt.subplots(2,2,figsize=(12,8.5))

# (a) 真实
ax[0,0].scatter(geo,rep,s=26,c='#c0392b',alpha=.75,edgecolors='none')
p=np.polyfit(geo,rep,1); xs=np.linspace(geo.min(),geo.max(),50)
ax[0,0].plot(xs,np.polyval(p,xs),'k--',lw=1.6)
ax[0,0].set_title(f"(a) 真实权重：我从哪里看世界\nr = {c['r_real']:.4f}   p < 0.001（置换）",fontsize=11)
ax[0,0].set_xlabel('观测点之间的地理距离 (km)'); ax[0,0].set_ylabel('内部表征距离')

# (b) 对照
ax[0,1].scatter(gc,rc,s=26,c='#7f8c8d',alpha=.75,edgecolors='none')
p2=np.polyfit(gc,rc,1); xs2=np.linspace(gc.min(),gc.max(),50)
ax[0,1].plot(xs2,np.polyval(p2,xs2),'k--',lw=1.6)
ax[0,1].set_title(f"(b) 对照·随机权重（结构破坏）\nr = {c['r_ctrl']:.4f}   p = {c['p_ctrl']:.4f}\n★也显著 → 部分来自权重幅度混淆",fontsize=10)
ax[0,1].set_xlabel('地理距离 (km)'); ax[0,1].set_ylabel('表征距离')

# (c) 剂量反应
bins=[(500,1000),(1000,1500),(1500,2200),(2200,3000)]
labels=['500-1000','1.0-1.5k','1.5-2.2k','2.2-3.0k']; means=[]; sds=[]
for lo,hi in bins:
    m=(geo>=lo)&(geo<hi); means.append(rep[m].mean()); sds.append(rep[m].std(ddof=1))
ax[1,0].bar(range(4),means,yerr=sds,capsize=4,color=['#2980b9','#16a085','#f39c12','#c0392b'],alpha=.85)
ax[1,0].set_xticks(range(4)); ax[1,0].set_xticklabels(labels,fontsize=9)
ax[1,0].set_title(f"(c) 剂量反应：距离越远，世界模型越不同\nSpearman ρ = {c['spearman']:.4f}",fontsize=11)
ax[1,0].set_xlabel('地理距离分箱 (km)'); ax[1,0].set_ylabel('表征距离 (均值±SD)')

# (d) Δr + 宿主-我位置
ax[1,1].barh([1,0],[c['r_real'],c['r_ctrl']],color=['#c0392b','#7f8c8d'],alpha=.85)
ax[1,1].errorbar([c['r_real'],c['r_ctrl']],[1,0],xerr=[[0,0],[0,0]],fmt='none')
ax[1,1].set_yticks([0,1]); ax[1,1].set_yticklabels(['对照\n随机权重','真实\n地理权重'],fontsize=9)
ax[1,1].set_xlabel('相关系数 r')
ax[1,1].set_title(f"(d) Δr = {c['delta_r']:.4f}\n95%CI [{c['ci'][0]:.3f}, {c['ci'][1]:.3f}]  p={c['p_delta']:.4f}",fontsize=11)
hs=b['rep_host_self']
ax[1,1].annotate(f"宿主↔我 {b['geo_km_host_self']:.0f}km\n表征距离 {hs:.4f}（45对中 {b['pct']*100:.1f} 百分位）",
    xy=(0.02,0.30),xycoords='axes fraction',fontsize=9,
    bbox=dict(boxstyle='round,pad=0.35',fc='#fdf2e9',ec='#d35400',alpha=.9))
plt.tight_layout()
out=os.path.join(ROOT,'fig','076_shared_world.png')
plt.savefig(out,dpi=130); print('[saved]',out)
