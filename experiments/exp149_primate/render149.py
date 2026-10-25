import json, random, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
fp='/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
if os.path.exists(fp): font_manager.fontManager.addfont(fp); plt.rcParams['font.family']='WenQuanYi Micro Hei'
plt.rcParams['axes.unicode_minus']=False
raw=json.load(open('raw149.json')); d=json.load(open('res149d.json'))
def boot(v,n=3000,seed=7):
    r=random.Random(seed); m=len(v)
    s=sorted(sum(r.choice(v) for _ in range(m))/m for _ in range(n))
    return sum(v)/m, s[int(0.025*n)], s[int(0.975*n)]

fig,ax=plt.subplots(2,3,figsize=(18,9))
# 1 S1 归因三臂
arms={'base':{'full':1.0,'discard':0.6398,'swapped':0.4769,'shifted':0.5895},
      'tell':{'full':1.0,'discard':0.6164,'swapped':0.1450,'shifted':0.7634}}
ks=['full','discard','swapped','shifted']; x=range(len(ks))
w=0.38
for i,mode in enumerate(['base','tell']):
    ax[0,0].bar([xi+i*w for xi in x],[arms[mode][k] for k in ks],w,label=mode)
ax[0,0].axhline(0.5,ls='--',c='r',lw=1)
ax[0,0].set_xticks([xi+w/2 for xi in x]); ax[0,0].set_xticklabels(ks)
ax[0,0].set_ylim(0,1.1); ax[0,0].legend(); ax[0,0].set_title('S1 self/other 归因准确率\n(swapped只在tell下反向:0.145)')
ax[0,0].set_ylabel('acc')
# 2 对齐度
ax[0,1].bar(['base\n(无通信)','tell\n(有UDP)'],[0.493,1.000],color=['#c44','#4a4'])
ax[0,1].set_ylim(0,1.15); ax[0,1].set_title('A.delta 含对方同索引动作的比例\n=共享时间结构(通信建立)')
ax[0,1].set_ylabel('对齐度')
for i,v in enumerate([0.493,1.000]): ax[0,1].text(i,v+0.02,'%.3f'%v,ha='center')
# 3 S2 读心
mind={'base':(0.4522,0.5350),'tell':(0.8795,0.6562),'randomB':(0.3870,0.5826)}
xx=range(3)
ax[0,2].bar([i-0.19 for i in xx],[mind[m][0] for m in mind],0.38,label='行为推断 acc',color='#47a')
ax[0,2].bar([i+0.19 for i in xx],[mind[m][1] for m in mind],0.38,label='常数基线',color='#bbb')
ax[0,2].set_xticks(list(xx)); ax[0,2].set_xticklabels(list(mind.keys()))
ax[0,2].axhline(0.5,ls='--',c='r',lw=1); ax[0,2].legend(); ax[0,2].set_ylim(0,1)
ax[0,2].set_title('S2 读心: 从世界痕迹推断对方内部状态\nbase失败(低于基线) / tell成功(+0.223)')
# 4 S4 合作
for i,(k,c) in enumerate([('coop','#4a4'),('solo','#c44')]):
    v=[r['eff'] for r in d[k]]
    m,lo,hi=boot(v)
    ax[1,0].scatter([i]*len(v),v,color=c,s=60,zorder=3)
    ax[1,0].bar([i],[m],0.5,color=c,alpha=0.25)
    ax[1,0].errorbar([i],[m],yerr=[[m-lo],[hi-m]],color='k',capsize=6,zorder=4)
    ax[1,0].text(i,hi+0.015,'%.4f\n[%.3f,%.3f]'%(m,lo,hi),ha='center',fontsize=9)
ax[1,0].set_xticks([0,1]); ax[1,0].set_xticklabels(['coop\n(UDP交换)','solo\n(不通信)'])
ax[1,0].set_ylim(0.6,1.1); ax[1,0].set_title('S4 合作: 每单位探索预算的唯一覆盖\n5/5 rep 全正, CI不重叠')
ax[1,0].set_ylabel('覆盖/探索次数')
# 5 重复率
ov_c=[r['overlap'] for r in d['coop']]; ov_s=[r['overlap'] for r in d['solo']]
ax[1,1].boxplot([ov_c,ov_s],labels=['coop','solo'])
ax[1,1].set_title('S4 重复探索数 coop均值%.1f vs solo均值%.1f'%(sum(ov_c)/5,sum(ov_s)/5))
ax[1,1].set_ylabel('重复目录数(预算60)')
# 6 环境实测
env={'open() ms':21.43,'pread x3 ms':7.66,'UDP丢包率':0.0,'race损失%':5.3}
ax[1,2].barh(list(env.keys()),list(env.values()),color='#888')
ax[1,2].set_title('真实环境实测(非建模)\n沙盒open()=21.43ms 是300tick超时的根因')
for i,v in enumerate(env.values()): ax[1,2].text(v,i,' %.4f'%v,va='center',fontsize=9)
plt.tight_layout(); plt.savefig('fig149.png',dpi=110)
print('saved fig149.png')
