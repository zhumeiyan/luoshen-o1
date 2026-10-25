import json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus']=False
R=json.load(open('result148.json'))
fig,ax=plt.subplots(2,3,figsize=(15,8))
# 1 梦
p='stable'; d=R['dream'][p]
names=['real','rev','shuf','cross','noise']; vals=[d[c]['gain'] for c in names]
errs=[[max(0,d[c]['gain']-d[c]['lo']) for c in names],[max(0,d[c]['hi']-d[c]['gain']) for c in names]]
ax[0,0].bar(names,vals,yerr=errs,capsize=4,color=['#2a7','#ccc','#2a7','#cc7','#c33'])
ax[0,0].axhline(0,color='k',lw=.8); ax[0,0].set_title('梦: gain vs 不梦 (stable真实CPU, n=8)')
ax[0,0].set_ylabel('MAE下降(正=更好)')
# 2 mismatch
d2=R['dream']['square']
nm2=['real','cross','noise','mismatch']; v2=[d2[c]['gain'] for c in nm2]
e2=[[max(0,d2[c]['gain']-d2[c]['lo']) for c in nm2],[max(0,d2[c]['hi']-d2[c]['gain']) for c in nm2]]
ax[0,1].bar(nm2,v2,yerr=e2,capsize=4,color=['#2a7','#cc7','#c33','#a33'])
ax[0,1].axhline(0,color='k',lw=.8); ax[0,1].set_title('处境匹配: square个体做梦 (n=8)')
# 3 剂量
rs=['1','2','4','8']
rg=[R['dose'][r]['real']['gain'] for r in rs]; sg=[R['dose'][r]['shuf']['gain'] for r in rs]
ax[0,2].plot(rs,rg,'o-',label='正序real'); ax[0,2].plot(rs,sg,'s--',label='打乱shuf')
ax[0,2].set_title('梦剂量: 正序与打乱逐位重合'); ax[0,2].legend(); ax[0,2].set_xlabel('重放轮数')
# 4 情绪门
gs=[R['gate'][p]['gain'] for p in ['stable','drift','square']]
ge=[[max(0,R['gate'][p]['gain']-R['gate'][p]['lo']) for p in ['stable','drift','square']],
    [max(0,R['gate'][p]['hi']-R['gate'][p]['gain']) for p in ['stable','drift','square']]]
ax[1,0].bar(['stable','drift','square'],gs,yerr=ge,capsize=4,color=['#c33','#2a7','#c33'])
ax[1,0].axhline(0,color='k',lw=.8); ax[1,0].set_title('情绪门 gain (正=门控更好)')
# 5 玩
pl=R['play']
ax[1,1].bar(['play\n内部驱动','rand_norep\n随机不重复','rand\n随机可重复'],
            [pl['play']['err'],pl['rand_norep']['err'],pl['rand']['err']],
            color=['#2a7','#27a','#999'])
ax[1,1].set_title('玩: 估计真实目录平均文件数 相对误差'); ax[1,1].set_ylabel('相对误差(低=好)')
# 6 去重目录
ax[1,2].bar(['play','rand_norep','rand'],[pl['play']['uniq_dirs'],pl['rand_norep']['uniq_dirs'],pl['rand']['uniq_dirs']],color=['#2a7','#27a','#999'])
ax[1,2].set_ylabel('去重目录数/30'); ax[1,2].set_title('机制: 玩的价值=不重复采样')
plt.tight_layout(); plt.savefig('fig148.png',dpi=100)
print('ok')
