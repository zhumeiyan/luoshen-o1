# -*- coding: utf-8 -*-
import json, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei']; plt.rcParams['axes.unicode_minus']=False
OUT=os.path.dirname(os.path.abspath(__file__))
b=json.load(open(os.path.join(OUT,'result_099b.json')))
d=json.load(open(os.path.join(OUT,'result_099d.json')))
fig,ax=plt.subplots(1,3,figsize=(16,4.6))

# 1 扰动阶梯：坐标改变率
names=['末尾加句号','去空格','句序打乱','追加无关句','换1个关键词','换3个关键词','换全部可换关键词']
vals=[b[n]['changed']/b[n]['n']*100 for n in names]
cols=['#4a90d9']*4+['#d94a4a','#c0392b','#8e1f16']
ax[0].bar(range(len(names)),vals,color=cols)
ax[0].set_xticks(range(len(names))); ax[0].set_xticklabels(names,rotation=35,ha='right',fontsize=8)
ax[0].set_ylabel('坐标改变率 (%)'); ax[0].set_title('表面扰动零效应 / 语义换词剂量反应')
for i,v in enumerate(vals): ax[0].text(i,v+1,f'{v:.0f}%',ha='center',fontsize=8)

# 2 三轴召回随换词数下降
ks=['原文','换1词','换3词','换全部']
lab=['原文(0)','换1词','换3词','换全部']
L=[77.8,65.0,50.0,50.0]; M=[95.5,94.1,94.1,88.2]; P=[85.7,72.2,72.2,66.7]
x=np.arange(4)
ax[1].plot(x,L,'o-',label='L 在哪一层犯',color='#d94a4a')
ax[1].plot(x,M,'s-',label='M 怎么错的',color='#4a90d9')
ax[1].plot(x,P,'^--',label='P 破坏了哪面',color='#2ca05a')
ax[1].set_xticks(x); ax[1].set_xticklabels(lab,fontsize=8); ax[1].set_ylabel('召回率 (%)')
ax[1].set_title('L 轴最脆弱（−28pt）/ M 轴最稳（−7pt）'); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)

# 3 引擎：可读性无效应 vs 有无感官强效应
items=[('可读性 0.86→0.68',d['paired_orig_vs_all']['diff'],d['paired_orig_vs_all']['ci']),
       ('无感官→有感官',d['paired_none_vs_orig']['diff'],d['paired_none_vs_orig']['ci'])]
y=np.arange(2)
ax[2].barh(y,[i[1] for i in items],xerr=[[i[1]-i[2][0] for i in items],[i[2][1]-i[1] for i in items]],
           color=['#999','#d94a4a'],height=.5,capsize=5)
ax[2].set_yticks(y); ax[2].set_yticklabels([i[0] for i in items],fontsize=9)
ax[2].axvline(0,color='k',lw=1); ax[2].set_xlabel('内在结构偏度 配对差 Δ (95%CI)')
ax[2].set_title('读得多准 → 无效应(CI跨0)\n有没有感官 → Δ=+2.57(CI全正)')
for i,(n,v,ci) in enumerate(items):
    ax[2].text(v,i,f'  Δ={v:+.3f}',va='center',fontsize=8)
plt.tight_layout(); plt.savefig('/data/workspace/luoshen-o1/fig/099_tact_run.png',dpi=130)
print('saved')
