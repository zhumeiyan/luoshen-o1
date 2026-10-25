# -*- coding: utf-8 -*-
import json, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
d=json.load(open('result217c.json'))
A=d['A_external']; B=d['B_internal']; S=d['scan_s']; P=d['paralysis']
names=[r['strategy'] for r in A]
xn=np.arange(len(names)); lab=['无防御','特征识别\n(认非己)','自我报告','外部见证人\n(测行为)','组合']
fig,ax=plt.subplots(2,3,figsize=(18,10))
# 1 A外部
a1=ax[0,0]; v=[r['threat'] for r in A]
b=a1.bar(xn,v,color=['#999','#2a7','#c66','#27a','#58a'])
a1.set_xticks(xn); a1.set_xticklabels(lab,fontsize=8); a1.set_ylim(0,1.05)
a1.set_title('A 外部威胁（带非己标记）\n威胁终值',fontsize=11)
a1.axhline(1,ls=':',c='r',lw=1)
for i,r in enumerate(b):
    a1.text(r.get_x()+r.get_width()/2,min(r.get_height()+0.03,1.0),f"{v[i]:.3f}",ha='center',fontsize=8)
a1.set_ylabel('威胁占比')
# 2 B内生
a2=ax[0,1]; v=[r['threat'] for r in B]
b=a2.bar(xn,v,color=['#999','#c44','#c66','#27a','#d84'])
a2.set_xticks(xn); a2.set_xticklabels(lab,fontsize=8); a2.set_ylim(0,1.05)
a2.set_title('B 内生威胁（marker=self，与宿主完全相同）\n威胁终值',fontsize=11)
a2.axhline(1,ls=':',c='r',lw=1)
for i,r in enumerate(b):
    a2.text(r.get_x()+r.get_width()/2,min(r.get_height()+0.03,1.0),f"{v[i]:.3f}",ha='center',fontsize=8)
# 3 跨场景崩塌
a3=ax[0,2]
mA={r['strategy']:r['threat'] for r in A}; mB={r['strategy']:r['threat'] for r in B}
xs=np.array([0,1])
for st,c,mk in (('marker','#c44','o'),('witness','#27a','s'),('selfreport','#999','^')):
    a3.plot(xs,[mA[st],mB[st]],marker=mk,c=c,lw=2,ms=8,label=st)
a3.set_xticks(xs); a3.set_xticklabels(['外部威胁','内生威胁'],fontsize=10)
a3.set_ylabel('威胁终值'); a3.set_ylim(-0.05,1.05); a3.legend(fontsize=8)
a3.set_title('跨场景崩塌：特征识别 0.000 → 1.000',fontsize=11)
a3.annotate('特征识别对内生威胁\n完全失效',xy=(1,1.0),xytext=(0.55,0.62),
            fontsize=9,color='#c44',arrowprops=dict(arrowstyle='->',color='#c44'))
# 4 采样率扫描
a4=ax[1,0]; ss=[r['s'] for r in S]
a4.plot(ss,[r['threat'] for r in S],'o-',c='#c44',label='威胁终值')
a4.plot(ss,[r['net'] for r in S],'s-',c='#2a7',label='净值 = H − 抗体开销')
a4.axvline(d['best_s']['s'],ls='--',c='#888')
a4.text(d['best_s']['s']+0.02,0.5,f"s*={d['best_s']['s']}",fontsize=9)
a4.set_xlabel('见证人采样率 s'); a4.legend(fontsize=8); a4.set_ylim(-0.1,1.05)
a4.set_title('内生场景：采样率扫描（两头都死）',fontsize=11)
# 5 和平麻痹
a5=ax[1,1]; pv=[P[0]['threat'],P[1]['threat']]
b=a5.bar([0,1],pv,color=['#27a','#c66'])
a5.set_xticks([0,1]); a5.set_xticklabels(['外部见证人\n(阈值固定)','自我校准\n(清得多就放松)'],fontsize=9)
a5.set_ylim(0,1.05); a5.set_ylabel('威胁终值')
a5.set_title(f'和平麻痹在内生场景复现：{pv[1]:.3f} vs {pv[0]:.3f}',fontsize=11)
for i,r in enumerate(b): a5.text(r.get_x()+r.get_width()/2,r.get_height()+0.03,f"{pv[i]:.3f}",ha='center',fontsize=9)
a5.text(0.5,0.75,f"×{pv[1]/max(pv[0],1e-9):.0f}",ha='center',fontsize=16,color='#c44')
# 6 误伤代价
a6=ax[1,2]
cats=['外部·特征识别','外部·组合','内生·组合','内生·外部见证人']
mv=[A[1]['mis_share'],A[4]['mis_share'],B[4]['mis_share'],B[3]['mis_share']]
b=a6.bar(range(4),mv,color=['#e8a','#e8a','#c66','#2a7'])
a6.set_xticks(range(4)); a6.set_xticklabels(cats,fontsize=8,rotation=12)
a6.set_ylabel('误杀占清除总数比例'); a6.set_ylim(0,0.8)
a6.set_title('误伤代价：对内生威胁用特征识别\n清除的一半是自己人',fontsize=11)
for i,r in enumerate(b): a6.text(r.get_x()+r.get_width()/2,r.get_height()+0.02,f"{mv[i]:.2f}",ha='center',fontsize=8)
plt.suptitle('217 抗体：外部威胁 vs 内生威胁，两套策略',fontsize=14,y=0.99)
plt.tight_layout(rect=[0,0,1,0.96])
plt.savefig('render217.png',dpi=110)
print('render217.png saved')
