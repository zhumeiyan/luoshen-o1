import json,re
from playwright.sync_api import sync_playwright
builtin=json.load(open("builtin_cases.json",encoding="utf-8"))
gold=[c["golden"] for c in builtin]

def variants(t):
    return {
      "v0_原文":        t,
      "v1_末尾加句号":   t+"。",
      "v2_删末5字":      t[:-5],
      "v3_中间插点":     t[:len(t)//2]+"·"+t[len(t)//2:],
      "v4_换1个同义词":  t.replace("智能体","代理程序") if "智能体" in t else t.replace("错误","不对的"),
      "v5_去空格":       t.replace(" ",""),
      "v6_前50字":       t[:50],
    }
names=list(variants(builtin[0]["desc"]).keys())
res={n:[] for n in names}
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    pg=b.new_page(viewport={"width":1280,"height":900})
    pg.goto("http://127.0.0.1:8899/demo.html",wait_until="load",timeout=30000)
    pg.wait_for_timeout(1000)
    for n in names:
        for c in builtin:
            txt=variants(c["desc"])[n]
            pg.fill("#tryInput",""); pg.click("#tryInput")
            pg.keyboard.type(txt,delay=0); pg.click("#tryBtn"); pg.wait_for_timeout(600)
            r=pg.inner_text("#tryResult")
            res[n].append({"id":c["id"],"coords":sorted(set(re.findall(r'\b([LMP]\d(?:-\d)?)\b',r))),"miss":"未命中" in r})
    pg.screenshot(path="/data/workspace/web_lab/shot_D.png")
    b.close()
def score(items):
    per={"L":[],"M":[],"P":[],"ALL":[]}
    for it,g in zip(items,gold):
        got=it["coords"]
        for ax in ("L","M","P"):
            if g.get(ax): per[ax].append(1 if any(x in got for x in g[ax]) else 0)
        per["ALL"].append(1 if all(any(x in got for x in g[ax]) for ax in ("L","M","P") if g.get(ax)) else 0)
    return {k:round(sum(v)/len(v),3) for k,v in per.items()}
print("== 逐字扰动梯度（真实网页，n=11）==")
for n in names:
    s=score(res[n]); mr=round(sum(x["miss"] for x in res[n])/len(res[n]),2)
    print(f"{n:>12}: ALL={s['ALL']:.3f} L={s['L']:.3f} M={s['M']:.3f} P={s['P']:.3f} miss率={mr}")
json.dump(res,open("result086_d.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
