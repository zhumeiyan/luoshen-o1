import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json, pathlib, collections
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
plt.rcParams["axes.unicode_minus"] = False

D = pathlib.Path(__file__).parent
lab = json.loads((D/"labels133.json").read_text())
aud = json.loads((D/"audit133.json").read_text())

fig, ax = plt.subplots(2, 3, figsize=(15, 8.4))
fig.suptitle("exp133  声明每条规则指控什么，然后把每个发现拿去对质", fontsize=14)

# 1 anchor proof: before vs after
a0 = ax[0,0]
names = ["exp130\n(旧启发式)", "exp133 v1\n(整节点证明)", "exp133 v3\n(行文本证明)"]
vals = [35.3, 83.9, 91.7]
b = a0.bar(names, vals, color=["#c0392b","#e67e22","#27ae60"])
a0.axhline(60, ls="--", c="k", lw=1)
a0.set_ylim(0,100); a0.set_ylabel("%")
a0.set_title("锚点自证率（只用读者会看到的那一行）")
for r,v in zip(b,vals): a0.text(r.get_x()+r.get_width()/2, v+2, f"{v}%", ha="center")

# 2 strict precision by kind
a1 = ax[0,1]
pres = [x for x in lab if x["kind"]=="present"]
abst = [x for x in lab if x["kind"]=="absent"]
vals = [100*sum(x["strict"] for x in pres)/len(pres),
        100*sum(x["strict"] for x in abst)/len(abst),
        100*sum(x["strict"] for x in lab)/len(lab)]
names = [f"present\nn={len(pres)}", f"absent\nn={len(abst)}", f"全部\nn={len(lab)}"]
b = a1.bar(names, vals, color=["#27ae60","#c0392b","#7f8c8d"])
a1.axhline(60, ls="--", c="k", lw=1)
a1.set_ylim(0,100); a1.set_ylabel("严格精度 %")
a1.set_title("严格精度：absent 规则结构上为 0")
for r,v in zip(b,vals): a1.text(r.get_x()+r.get_width()/2, v+2, f"{v:.1f}%", ha="center")

# 3 key saturation
a2 = ax[0,2]
rates = {"EG005":23.5,"EG011":None,"EG012":7.2,"EG013":12.1,"EGP09":4.0,
         "EG006":100.0,"EGP08":100.0,"EG001":1.7,"EG016":0.9}
ks = list(rates)
vv = [rates[k] if rates[k] is not None else 0 for k in ks]
col = ["#e67e22" if rates[k] is None else ("#c0392b" if rates[k]>95 else "#27ae60") for k in ks]
b = a2.bar(ks, vv, color=col)
a2.axhline(95, ls="--", c="r", lw=1)
a2.set_ylabel("pool 中含 key 的比例 %")
a2.set_title("key 的区分力（橙=未声明，红=饱和）")
a2.tick_params(axis="x", rotation=45, labelsize=8)

# 4 EG011 anchor migration
a3 = ax[1,0]
a3.barh(["olmes L713","olmes L857","helm L172"], [2,3,18], color="#c0392b", label="修前（循环头）")
a3.barh(["olmes L715","olmes L860","helm L190"], [0,0,0], color="#27ae60", label="修后（continue 行）")
a3.set_xlabel("证据距钉住行的行数"); a3.set_title("EG011：钉子移到真正跳过的那一行")
a3.legend(fontsize=8)

# 5 metrics.py substring bug
a4 = ax[1,1]
a4.bar(["修前","修后"], [12,2], color=["#c0392b","#27ae60"])
a4.set_ylabel("olmes 中被判为“报告指标”的语句数")
a4.set_title("子串匹配：memory 含 em，deferred 含 err")
for i,v in enumerate([12,2]): a4.text(i, v+0.3, str(v), ha="center")

# 6 recall preserved
a5 = ax[1,2]
a5.bar(["埋雷 12","pro 14","clean 0"], [12,14,0], color="#2980b9")
a5.set_ylabel("命中数"); a5.set_title("召回未掉（提精度不能靠删召回）")
for i,v in enumerate([12,14,0]): a5.text(i, v+0.3, str(v), ha="center")

plt.tight_layout(rect=[0,0,1,0.95])
plt.savefig(D/"fig133.png", dpi=110)
print("saved", (D/"fig133.png").stat().st_size)
