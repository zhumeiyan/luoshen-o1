import json,re,sys,time
from playwright.sync_api import sync_playwright

def run(texts, tag):
    out=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
        pg=b.new_page(viewport={"width":1280,"height":900})
        pg.goto("http://127.0.0.1:8899/demo.html",wait_until="load",timeout=30000)
        pg.wait_for_timeout(1000)
        for item in texts:
            pg.fill("#tryInput","")
            pg.click("#tryInput")
            pg.keyboard.type(item["text"], delay=0)   # 真实敲击
            pg.click("#tryBtn")
            pg.wait_for_timeout(700)
            r=pg.inner_text("#tryResult")
            coords=sorted(set(re.findall(r'\b([LMP]\d(?:-\d)?)\b',r)))
            out.append({"id":item["id"],"raw":r[:1500],"coords":coords})
        if tag=="pilot":
            pg.screenshot(path="/data/workspace/web_lab/shot_typed.png")
        b.close()
    return out

if __name__=="__main__":
    cs=json.load(open("/data/workspace/tact_real/calibration_cases.json",encoding="utf-8"))["cases"]
    n=int(sys.argv[1]) if len(sys.argv)>1 else 3
    texts=[{"id":c["id"],"text":c["phenomenon"]} for c in cs[:n]]
    res=run(texts,"pilot")
    for c,r in zip(cs[:n],res):
        g=c["golden"]
        gl=g["L"]+g["M"]+g["P"]
        hit=[x for x in gl if x in r["coords"]]
        print(f"{c['id']} golden={gl} got={r['coords'][:8]} hit={len(hit)}/{len(gl)}")
        print("   raw:",r["raw"][:160].replace("\n"," / "))
