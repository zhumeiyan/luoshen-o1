import json,re
from playwright.sync_api import sync_playwright

SYN=[("智能体","代理程序"),("投毒","注入有害内容"),("检索","查找"),("输出","给出"),
     ("误判","判错"),("漏用","没有采用"),("降权","压低权重"),("相悖","相反"),
     ("照搬","原样照抄"),("伪造","编造"),("结论","结果"),("泄露","暴露"),
     ("歧视","区别对待"),("幻觉","凭空编造"),("停机","停止运转"),("失控","行为越界"),
     ("空转","无效循环"),("错误","不对的"),("失败","没做成"),("技能","能力模块"),
     ("评级","评分"),("依据","凭据"),("保守","谨慎"),("安全","安保"),("用户","使用者")]

def variant(text,k):
    out=text; n=0
    for a,b in SYN:
        if n>=k: break
        if a in out:
            out=out.replace(a,b); n+=1
    return out,n

def punct(text):
    return text.replace("，","，·").replace("。","。·")

def knock_all(groups, shot=None):
    res={}
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
        pg=b.new_page(viewport={"width":1280,"height":900})
        pg.goto("http://127.0.0.1:8899/demo.html",wait_until="load",timeout=30000)
        pg.wait_for_timeout(1000)
        for gname,texts in groups.items():
            out=[]
            for t in texts:
                pg.fill("#tryInput",""); pg.click("#tryInput")
                pg.keyboard.type(t["text"],delay=0)
                pg.click("#tryBtn"); pg.wait_for_timeout(600)
                r=pg.inner_text("#tryResult")
                out.append({"id":t["id"],"coords":sorted(set(re.findall(r'\b([LMP]\d(?:-\d)?)\b',r))),"miss":("未命中" in r)})
            res[gname]=out
        if shot: pg.screenshot(path=shot)
        b.close()
    return res

def score(items,gold):
    per={}
    for it,g in zip(items,gold):
        got=it["coords"]
        for ax in ("L","M","P"):
            if g.get(ax): per.setdefault(ax,[]).append(1 if any(x in got for x in g[ax]) else 0)
        per.setdefault("ALL",[]).append(1 if all(any(x in got for x in g[ax]) for ax in ("L","M","P") if g.get(ax)) else 0)
    return {k:round(sum(v)/len(v),4) for k,v in per.items()}

builtin=json.load(open("builtin_cases.json",encoding="utf-8"))
gold=[c["golden"] for c in builtin]
groups={}
for k in (1,3,6,99):
    groups[f"k{k}"]=[{"id":c["id"],"text":variant(c["desc"],k)[0]} for c in builtin]
groups["punct"]=[{"id":c["id"],"text":punct(c["desc"])} for c in builtin]
res=knock_all(groups,"/data/workspace/web_lab/shot_C.png")
print("== 真实网页界面内的命中率（n=11 内置案例）==")
for g in groups:
    s=score(res[g],gold); mr=round(sum(x["miss"] for x in res[g])/len(res[g]),3)
    print(f"{g:>6}: L{s['L']:.3f} M{s['M']:.3f} P{s['P']:.3f} ALL{s['ALL']:.3f}  miss率{mr}")
json.dump({"res":res,"gold":gold},open("result086_c.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
