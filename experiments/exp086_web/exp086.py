import json,re,sys
from playwright.sync_api import sync_playwright

def knock(texts, shot=None):
    res=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
        pg=b.new_page(viewport={"width":1280,"height":900})
        pg.goto("http://127.0.0.1:8899/demo.html",wait_until="load",timeout=30000)
        pg.wait_for_timeout(1000)
        for t in texts:
            pg.fill("#tryInput","")
            pg.click("#tryInput")
            pg.keyboard.type(t["text"], delay=0)
            pg.click("#tryBtn")
            pg.wait_for_timeout(650)
            r=pg.inner_text("#tryResult")
            res.append({"id":t["id"],"coords":sorted(set(re.findall(r'\b([LMP]\d(?:-\d)?)\b',r))),
                        "miss":("未命中" in r),"raw":r[:400]})
        if shot: pg.screenshot(path=shot)
        b.close()
    return res

def score(items, gold):
    per={}
    for it,g in zip(items,gold):
        gl=g["L"]+g["M"]+g["P"]
        got=it["coords"]
        for ax in ("L","M","P"):
            tgt=g[ax]; hit=any(x in got for x in tgt) if tgt else None
            if tgt: per.setdefault(ax,[]).append(1 if hit else 0)
        per.setdefault("ALL",[]).append(1 if all(any(x in got for x in g[ax]) for ax in ("L","M","P") if g[ax]) else 0)
    return {k:round(sum(v)/len(v),4) for k,v in per.items()}, {k:len(v) for k,v in per.items()}

if __name__=="__main__":
    builtin=json.load(open("builtin_cases.json",encoding="utf-8"))
    calib=json.load(open("/data/workspace/tact_real/calibration_cases.json",encoding="utf-8"))["cases"]
    A=[{"id":c["id"],"text":c["desc"]} for c in builtin]
    B=[{"id":c["id"],"text":c["phenomenon"]} for c in calib]
    ra=knock(A,"/data/workspace/web_lab/shot_A.png")
    rb=knock(B,"/data/workspace/web_lab/shot_B.png")
    sa,na=score(ra,[c["golden"] for c in builtin])
    sb,nb=score(rb,[c["golden"] for c in calib])
    print("A 内置案例原文 n=11 :",sa,na)
    print("B 校准集原文   n=29 :",sb,nb)
    print("A miss率:",round(sum(x["miss"] for x in ra)/len(ra),3),"B miss率:",round(sum(x["miss"] for x in rb)/len(rb),3))
    json.dump({"A":ra,"B":rb,"scoreA":sa,"scoreB":sb},open("result086_ab.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
