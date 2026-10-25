# -*- coding: utf-8 -*-
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc","/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    import os
    if os.path.exists(p):
        font_manager.fontManager.addfont(p); plt.rcParams["font.family"]="WenQuanYi Micro Hei"; break
plt.rcParams["axes.unicode_minus"]=False
d=json.load(open("result126d.json")); c=json.load(open("result126c.json")); e=json.load(open("result126e.json"))
R=d["res"]; LAB={'no_practice':'只输液\n不练','practice_open':'练·相继\n不相倚','practice_closed':'练·相倚',
 'tool_only':'纯外置\n工具','tool_plus_self':'工具+\n自觅食','variation':'随机\n变异'}
order=['no_practice','practice_open','practice_closed','tool_only','tool_plus_self','variation']
fig,ax=plt.subplots(2,3,figsize=(16,9))
a=ax[0,0]
fg=[R[k]['fg'] for k in order]; al=[R[k]['n'] for k in order]
x=np.arange(6)
a.bar(x-0.2,fg,0.4,color='#4C72B0',label='学到的 fg')
a.set_xticks(x); a.set_xticklabels([LAB[k] for k in order],fontsize=9)
a2=a.twinx(); a2.bar(x+0.2,[n/16 for n in al],0.4,color='#C44E52',label='撤除后存活率')
a.axhline(0.008,ls='--',c='k',lw=1); a.text(0.05,0.010,'死亡阈值 0.008',fontsize=8)
a.set_title('① 六方案：学到的觅食能力与撤除后存活',fontsize=11)
a.set_ylabel('fg'); a2.set_ylabel('存活率'); a2.set_ylim(0,1.05)

a=ax[0,1]
tk=[R[k]['ticks'] for k in order]
a.bar(x,tk,0.5,color=['#999999' if R[k]['n']==0 else '#55A868' for k in order])
a.set_xticks(x); a.set_xticklabels([LAB[k] for k in order],fontsize=9)
a.set_title('② 撤除后平均支撑拍数（上限1500）',fontsize=11); a.set_ylabel('拍')

a=ax[0,2]
B=[r['burn'] for r in c]; o=[r['open']['fg'] for r in c]; cl=[r['closed']['fg'] for r in c]
oa=[r['open']['n'] for r in c]; ca=[r['closed']['n'] for r in c]
a.plot(B,o,'o-',c='#C44E52',label='相继不相倚')
a.plot(B,cl,'s-',c='#4C72B0',label='相倚')
a.axhline(0.008,ls='--',c='k',lw=1)
a.set_xlabel('burn-in 拍数'); a.set_ylabel('学到的 fg')
a.set_title('③ 瞬态偏差：burn=0 时"不相倚"也像学会了',fontsize=11); a.legend(fontsize=8)

a=ax[1,0]
m=['reflect','free','harmful']; lab=['只能变好\n(下限反射)','可好可坏','大概率有害']
v=[e[k]['n'] for k in m]
a.bar(range(3),v,0.5,color=['#DD8452','#937860','#C44E52'])
a.set_xticks(range(3)); a.set_xticklabels(lab,fontsize=9)
a.set_title('④ 变异(#19)的三种建模：撤除后存活数/16',fontsize=11); a.set_ylim(0,16)
for i,vv in enumerate(v): a.text(i,vv+0.4,str(vv),ha='center',fontsize=10)

a=ax[1,1]
ks=list(d['comp'].keys()); dl=[d['comp'][k]['delta'] for k in ks]
lo=[d['comp'][k]['lo'] for k in ks]; hi=[d['comp'][k]['hi'] for k in ks]
names=['相倚-相继','练-不练','工具+自觅-纯工具','自觅-(工具+自觅)']
y=np.arange(4)
a.errorbar(dl,y,xerr=[np.array(dl)-np.array(lo),np.array(hi)-np.array(dl)],fmt='o',c='#4C72B0',capsize=4)
a.axvline(0,ls='--',c='k',lw=1); a.set_yticks(y); a.set_yticklabels(names,fontsize=9)
a.set_title('⑤ 配对 Δfg 与 95%CI（跨0=不显著）',fontsize=11); a.set_xlabel('Δfg')

a=ax[1,2]
ac=[R[k]['act'] for k in order]
a.bar(x,ac,0.5,color='#8172B3'); a.set_xticks(x); a.set_xticklabels([LAB[k] for k in order],fontsize=9)
a.set_title('⑥ 训练期自身觅食投入（工具组最低）',fontsize=11); a.set_ylabel('平均投入')
plt.tight_layout(); plt.savefig("/data/workspace/luoshen-o1/fig/126_wean_protocol.png",dpi=110)
print("saved fig")
