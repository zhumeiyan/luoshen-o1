import asyncio, subprocess, json, time
from playwright.async_api import async_playwright
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
DOM=["https://github.com/KLameng/TACT-Three-Axis-Check","https://api.github.com/zen"]
def proto(u):
    try:
        r=subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","-m","12","-A",UA,u],capture_output=True,text=True)
        return int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    except Exception: return 0
async def main():
    out={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
        pg=await b.new_page(); await pg.set_extra_http_headers({"User-Agent":UA})
        for u in DOM:
            g=0
            try:
                r=await pg.goto(u,timeout=20000,wait_until="domcontentloaded"); g=r.status if r else 0
            except Exception: pass
            pr=proto(u)
            out[u]={"gui":g,"proto":pr}
            print(f"{u[:50]:52s} gui={g:4d} proto={pr:4d}")
        await b.close()
    json.dump(out,open("grid.json","w"),indent=1)
    print("\n=== 归因 ===")
    a=out[DOM[0]]; bb=out[DOM[1]]
    chan_effect = abs(a["gui"]-a["proto"])+abs(bb["gui"]-bb["proto"])
    dom_effect  = abs(a["gui"]-bb["gui"])+abs(a["proto"]-bb["proto"])
    print(f"  通道维差异(同域名,GUI vs 协议) = {chan_effect}")
    print(f"  域名维差异(同通道,github vs api)= {dom_effect}")
    print(f"  -> 冗余在{'域名' if dom_effect>chan_effect else '通道'}")
asyncio.run(main())
