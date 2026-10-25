import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, json, pathlib, collections
plt.rcParams["font.family"]="WenQuanYi Micro Hei"; plt.rcParams["axes.unicode_minus"]=False
D=pathlib.Path(__file__).parent
rows=json.loads((D/"labels134.json").read_text())
fig,ax=plt.subplots(2,3,figsize=(15,8.4))
fig.suptitle("exp134  独立语料(7个新仓库)复核：不是 present/absent，是 syntax/methodology",fontsize=13)
def pct(sel):
    n=[r for r in rows if sel(r)]
    return len(n), (100*sum(r['strict'] for r in n)/len(n) if n else 0)
# 1 pre-registered gates
a=ax[0,0]
names=["G3\n行级全部","G4\n文件级","G3\n行级+syntax","G3\n行级+method"]
vals=[pct(lambda r:r['pinned']=='line')[1], pct(lambda r:r['pinned']=='file')[1],
      pct(lambda r:r['pinned']=='line' and r['cls']=='syntax')[1],
      pct(lambda r:r['pinned']=='line' and r['cls']=='methodology')[1]]
b=a.bar(names,vals,color=["#e67e22","#c0392b","#27ae60","#c0392b"])
a.axhline(60,ls="--",c="k"); a.set_ylim(0,100); a.set_ylabel("严格精度 %")
a.set_title("预注册闸门：全部未过（门槛60）")
for r,v in zip(b,vals): a.text(r.get_x()+r.get_width()/2,v+2,f"{v:.1f}",ha="center")
# 2 the real split
a=ax[0,1]
n1,v1=pct(lambda r:r['cls']=='syntax'); n2,v2=pct(lambda r:r['cls']=='methodology')
b=a.bar([f"syntax\nn={n1}",f"methodology\nn={n2}"],[v1,v2],color=["#27ae60","#c0392b"])
a.axhline(60,ls="--",c="k"); a.set_ylim(0,100); a.set_ylabel("严格精度 %")
a.set_title("真正的分层：语法层 vs 方法论层")
for r,v in zip(b,[v1,v2]): a.text(r.get_x()+r.get_width()/2,v+2,f"{v:.1f}%",ha="center")
# 3 strict vs loose
a=ax[0,2]
sl=[("syntax",lambda r:r['cls']=='syntax'),("methodology",lambda r:r['cls']=='methodology')]
xs=[0,1]
st=[pct(s)[1] for _,s in sl]
lo=[(100*sum(r['loose'] for r in rows if s(r))/pct(s)[0]) for _,s in sl]
a.bar([x-0.18 for x in xs],st,width=0.35,color="#27ae60",label="strict")
a.bar([x+0.18 for x in xs],lo,width=0.35,color="#95a5a6",label="loose(字面成立)")
a.axhline(60,ls="--",c="k"); a.set_xticks(xs); a.set_xticklabels([s[0] for s in sl])
a.set_ylim(0,100); a.legend(fontsize=8); a.set_title("loose 全过线，strict 只有 syntax 过")
for x,v in zip(xs,st): a.text(x-0.18,v+2,f"{v:.1f}",ha="center",fontsize=8)
for x,v in zip(xs,lo): a.text(x+0.18,v+2,f"{v:.1f}",ha="center",fontsize=8)
# 4 per rule strict TP
a=ax[1,0]
egs=sorted({r['eg'] for r in rows}, key=lambda k:-sum(1 for r in rows if r['eg']==k))
n=[sum(1 for r in rows if r['eg']==k) for k in egs]
t=[100*sum(r['strict'] for r in rows if r['eg']==k)/sum(1 for r in rows if r['eg']==k) for k in egs]
col=["#27ae60" if k in ("EG005","EG006","EGP01","EGP04") else "#c0392b" for k in egs]
b=a.bar(egs,t,color=col); a.set_ylabel("严格精度 %"); a.set_ylim(0,100)
a.set_title("逐规则（绿=过线）"); a.tick_params(axis="x",rotation=60,labelsize=8)
for r,v,nn in zip(b,t,n): a.text(r.get_x()+r.get_width()/2,v+2,f"n{nn}",ha="center",fontsize=7)
# 5 exp133 vs exp134 present
a=ax[1,1]
names=["exp133\npresent","exp134\npresent","exp133\nabsent","exp134\nfile"]
vals=[66.7, pct(lambda r:r['pinned']=='line')[1], 0.0, pct(lambda r:r['pinned']=='file')[1]]
b=a.bar(names,vals,color=["#7f8c8d","#e67e22","#7f8c8d","#c0392b"])
a.axhline(60,ls="--",c="k"); a.set_ylim(0,100); a.set_title("上轮拆分未在独立语料复现")
for r,v in zip(b,vals): a.text(r.get_x()+r.get_width()/2,v+2,f"{v:.1f}",ha="center")
# 6 findings by repo
a=ax[1,2]
c=collections.Counter((r['repo'].split('/')[-1][:14], r['strict']) for r in rows)
repos=sorted({k[0] for k in c})
tp=[c[(r,1)] for r in repos]; fp=[c[(r,0)] for r in repos]
a.bar(repos,tp,color="#27ae60",label="strict TP"); a.bar(repos,fp,bottom=tp,color="#c0392b",label="FP")
a.set_title("各仓库发现分布"); a.tick_params(axis="x",rotation=45,labelsize=8); a.legend(fontsize=8)
plt.tight_layout(); plt.savefig(D/"fig134.png",dpi=110); print("fig ok")
