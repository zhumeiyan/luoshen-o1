import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus']=False
d=json.load(open('result199.json',encoding='utf-8'))
b=json.load(open('result199b.json',encoding='utf-8'))
fig,ax=plt.subplots(2,2,figsize=(13,9))

cs=d['cap_scan']; xs=[r['A_chars'] for r in cs]
ax[0,0].plot(xs,[r['alpha0.1']['bits_B_by_Bonly'] for r in cs],'o--',label='只用你的话(B-only)',color='#888')
ax[0,0].plot(xs,[r['alpha0.1']['bits_B_by_mono'] for r in cs],'o-',label='混合Mono(A+B)',color='#c0392b',lw=2)
ax[0,0].plot(xs,[r['alpha0.1']['bits_B_by_Aonly'] for r in cs],'s:',label='只有工作能力(A-only)',color='#2980b9')
ax[0,0].set_xscale('log'); ax[0,0].set_xlabel('工作能力A的字符量'); ax[0,0].set_ylabel('读你的话的代价 bits/字符')
ax[0,0].set_title('① 工作能力越多，读你的话越容易\n(不是淹没，是帮忙)',fontsize=11)
ax[0,0].legend(fontsize=8); ax[0,0].grid(alpha=.3)

vs=b['voice']; vx=[r['A_chars'] for r in vs]
ax[0,1].plot(vx,[r['volume_share_B_expected']*100 for r in vs],'o--',label='B的体量份额(期望)',color='#888')
ax[0,1].plot(vx,[r['B_voice_mean']*100 for r in vs],'o-',label='B的实际话语权',color='#27ae60',lw=2)
ax[0,1].plot(vx,[r['B_voice_known_ctx']*100 for r in vs],'s:',label='A也见过的上下文上',color='#e67e22')
ax[0,1].set_xscale('log'); ax[0,1].set_xlabel('工作能力A的字符量'); ax[0,1].set_ylabel('B 的话语权 %')
ax[0,1].set_title('② 独特性在保护你\n体量1.16%，话语权50%',fontsize=11)
ax[0,1].legend(fontsize=8); ax[0,1].grid(alpha=.3)

r=[x for x in d['arch'] if x['alpha']==0.1 and x['A_chars']==345555][0]
names=['混合\nMono','子AI\n仲裁(对抗)','只用你的话\nB-only','子AI\n排班']
vals=[r['B_mono'],r['B_arbitrate'],r['B_Bonly'],r['B_sched_vol']]
cols=['#27ae60','#e67e22','#95a5a6','#c0392b']
ax[1,0].bar(names,vals,color=cols)
for i,v in enumerate(vals): ax[1,0].text(i,v+.03,f'{v:.3f}',ha='center',fontsize=10,fontweight='bold')
ax[1,0].set_ylabel('读你的话的代价 bits/字符'); ax[1,0].set_ylim(7.8,9.6)
ax[1,0].set_title('③ 分成子AI反而更差\n(越低越好)',fontsize=11); ax[1,0].grid(alpha=.3,axis='y')

u=d['uniqueness']; order=sorted(u.keys(),key=lambda k:u[k]['swamp'])
ax[1,1].barh([k.replace('(最独特)','\n(最独特)') for k in order],[u[k]['swamp'] for k in order],
             color=['#c0392b' if u[k]['swamp']>=0 else '#2980b9' for k in order])
ax[1,1].set_xlabel('混合后代价变化 bits (负=被工作能力帮到)')
ax[1,1].set_title('④ 越独特，越帮不上\nswamp=0 处两者完全无关',fontsize=11); ax[1,1].grid(alpha=.3,axis='x')
plt.tight_layout(); plt.savefig('render199.png',dpi=110)
print('ok')
