import asyncio, json, subprocess, time
from playwright.async_api import async_playwright

TARGETS = [
 ("mail.qq.com",      "https://mail.qq.com"),
 ("api.github.com",   "https://api.github.com/zen"),
 ("github.com",       "https://github.com/KLameng/TACT-Three-Axis-Check"),
 ("captcha.gtimg",    "https://captcha.gtimg.com/static/template/drag_ele.cb7e57e5.html"),
 ("captcha.qq.com",   "https://captcha.qq.com/TCaptcha.js"),
 ("gitee.com",        "https://gitee.com/dromara/easyAi"),
 ("im.qq.com",        "https://im.qq.com/index/#/linux"),
 ("baidu.com",        "https://www.baidu.com"),
 ("oschina.net",      "https://www.oschina.net"),
 ("qq.com",           "https://www.qq.com"),
]

def proto(url):
    t0=time.time()
    try:
        r=subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","-m","12",
                          "-A","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36",url],
                         capture_output=True,text=True)
        code=r.stdout.strip()
        return int(code) if code.isdigit() else 0, time.time()-t0
    except Exception as e:
        return 0, time.time()-t0

async def gui(pg, url):
    t0=time.time()
    try:
        r=await pg.goto(url, timeout=20000, wait_until="domcontentloaded")
        return (r.status if r else 0), time.time()-t0
    except Exception:
        return 0, time.time()-t0

async def main():
    res={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
        pg=await b.new_page()
        await pg.set_extra_http_headers({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36"})
        for name,url in TARGETS:
            pc,pt = proto(url)
            gc,gt = await gui(pg,url)
            res[name]={"proto":pc,"gui":gc,"proto_t":round(pt,2),"gui_t":round(gt,2)}
            print(f"{name:16s} proto={pc:4d} gui={gc:4d}   t={pt:5.2f}/{gt:5.2f}")
        await b.close()
    json.dump(res,open("doors.json","w"),indent=1)
    # 门型分类
    print("\n=== 门型 ===")
    for k,v in res.items():
        P = v["proto"]==200; G = v["gui"]==200
        t = "两扇都开" if (P and G) else ("仅协议" if P else ("仅GUI" if G else "两扇都封"))
        print(f"  {k:16s} {t}")
asyncio.run(main())
