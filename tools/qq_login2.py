import asyncio
from playwright.async_api import async_playwright
U="778131400"; P="z4570285"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True, executable_path="/usr/local/bin/chromium",
            args=["--no-sandbox","--disable-blink-features=AutomationControlled","--ignore-certificate-errors"])
        ctx=await b.new_context(viewport={"width":1280,"height":900},ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        pg=await ctx.new_page()
        url=("https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=522005705&daid=4&style=33&low_login=1"
             "&s_url=https%3A%2F%2Fmail.qq.com%2F&proxy_url=https%3A%2F%2Fmail.qq.com%2Fproxy.html")
        await pg.goto(url, wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(3000)
        print("URL:",pg.url)
        await pg.screenshot(path=".auth/s1.png")
        try:
            await pg.click("text=密码登录", timeout=8000); print("clicked 密码登录")
        except Exception as e: print("click err",e)
        await pg.wait_for_timeout(2500)
        await pg.screenshot(path=".auth/s2.png")
        for sel in ["#u","#p"]:
            try:
                await pg.fill(sel, U if sel=="#u" else P, timeout=8000); print("filled",sel)
            except Exception as e: print("fill",sel,"err",str(e)[:120])
        await pg.screenshot(path=".auth/s3.png")
        try:
            await pg.click("#login_button", timeout=8000); print("clicked login")
        except Exception as e: print("loginbtn err",str(e)[:120])
        await pg.wait_for_timeout(8000)
        print("URL after:",pg.url)
        await pg.screenshot(path=".auth/s4.png")
        try: print("TEXT:", (await pg.evaluate("()=>document.body.innerText"))[:600].replace("\n"," | "))
        except Exception as e: print(e)
        # 是否有验证码iframe
        for f in pg.frames:
            print("FRAME:", f.url[:130])
        await ctx.storage_state(path=".auth/state3.json")
        await b.close()
asyncio.run(main())
