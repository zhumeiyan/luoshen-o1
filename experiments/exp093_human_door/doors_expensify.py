import asyncio, json, subprocess, time
from playwright.async_api import async_playwright

TARGETS = [
 ("new.expensify",  "https://new.expensify.com/home"),
 ("expensify.com",  "https://www.expensify.com/"),
 ("upwork",         "https://www.upwork.com/"),
 ("mail.qq.com",    "https://mail.qq.com"),
 ("github.com",     "https://github.com/"),
 ("gitee",          "https://gitee.com/dromara/easyAi"),
]
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36"

def proto(url):
    t0=time.time()
    try:
        r=subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","-m","12","-A",UA,url],
                         capture_output=True,text=True)
        c=r.stdout.strip()
        return (int(c) if c.isdigit() else 0), time.time()-t0
    except Exception: return 0, time.time()-t0

async def main():
    res={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                  args=["--no-sandbox","--disable-dev-shm-usage"])
        pg=await b.new_page()
        await pg.set_extra_http_headers({"User-Agent":UA})
        for name,url in TARGETS:
            pc,pt=proto(url)
            t0=time.time(); gc=0; err=""
            try:
                r=await pg.goto(url,timeout=20000,wait_until="domcontentloaded")
                gc=r.status if r else 0
            except Exception as e: err=str(e).splitlines()[0][:60]
            gt=time.time()-t0
            res[name]={"proto":pc,"gui":gc,"err":err}
            print(f"{name:16s} proto={pc:4d} gui={gc:4d}  {err}")
        await b.close()
    print("\n=== 门型（洛神分类法）===")
    for k,v in res.items():
        P=v["proto"]==200; G=v["gui"]==200
        t="两扇都开" if (P and G) else ("仅协议" if P else ("仅GUI" if G else "两扇都封"))
        print(f"  {k:16s} {t}")
    json.dump(res,open("doors_expensify.json","w"),indent=1)
asyncio.run(main())
