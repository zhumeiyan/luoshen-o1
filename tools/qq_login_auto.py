import asyncio, json, os
from playwright.async_api import async_playwright

U = "778131400"; P = "z4570285"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, executable_path="/usr/local/bin/chromium", args=["--no-sandbox","--disable-blink-features=AutomationControlled"])
        ctx = await b.new_context(viewport={"width":1280,"height":900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        pg = await ctx.new_page()
        log=[]
        pg.on("console", lambda m: log.append(("console",m.text[:200])))
        pg.on("response", lambda r: log.append(("resp", f"{r.status} {r.url[:120]}")) if any(k in r.url for k in ["ptlogin","verify","cap","login","safe"]) else None)

        await pg.goto("https://mail.qq.com/", wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(3000)
        print("URL:", pg.url)
        # 切到账号密码登录
        try:
            pass
        except Exception as e:
            print("no pwd tab:", e)
        await pg.wait_for_timeout(1500)
        # 找 frame
        for f in pg.frames:
            if "xlogin" in f.url or "ptlogin" in f.url:
                print("FRAME:", f.url[:120])
                try:
                    await f.click("text=密码登录", timeout=5000)
                    await f.wait_for_timeout(2000)
                    await f.fill("#u", U, timeout=8000)
                    await f.fill("#p", P, timeout=5000)
                    print("filled u/p")
                    await f.click("#login_button", timeout=5000)
                    print("clicked")
                except Exception as e:
                    print("fill err:", e)
                break
        await pg.wait_for_timeout(6000)
        print("URL after:", pg.url)
        await pg.screenshot(path=".auth/after_login.png", full_page=True)
        # 抓验证相关
        for f in pg.frames:
            try:
                txt = await f.evaluate("()=>document.body.innerText.slice(0,500)")
                if txt.strip(): print("FRAME TEXT", f.url[:80], "::", txt.replace("\n"," | ")[:300])
            except: pass
        print("--- relevant responses ---")
        for k,v in log[-40:]:
            print(k, v)
        await ctx.storage_state(path=".auth/state2.json")
        await b.close()

asyncio.run(main())
