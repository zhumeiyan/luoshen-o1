import asyncio, json
from playwright.async_api import async_playwright
U="778131400"; P="z4570285"
JS = """
([u,p])=>{
  const set=(el,v)=>{const d=Object.getOwnPropertyDescriptor(el.__proto__,'value')||Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');
    d.set.call(el,v); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));};
  const eu=document.querySelector('#u'), ep=document.querySelector('#p');
  if(!eu||!ep) return {err:'no inputs'};
  set(eu,u); set(ep,p);
  return {u:eu.value.length, p:ep.value.length, hasBtn: !!document.querySelector('#login_button')};
}
"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True, executable_path="/usr/local/bin/chromium",
            args=["--no-sandbox","--ignore-certificate-errors"])
        ctx=await b.new_context(viewport={"width":1280,"height":900},ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        pg=await ctx.new_page()
        errs=[]
        pg.on("console", lambda m: errs.append(m.text[:160]))
        url=("https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=522005705&daid=4&style=33&low_login=1"
             "&s_url=https%3A%2F%2Fmail.qq.com%2F&proxy_url=https%3A%2F%2Fmail.qq.com%2Fproxy.html")
        await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(5000)
        try:
            r=await pg.evaluate(JS,[U,P]); print("FILL:",json.dumps(r))
        except Exception as e: print("fill err",str(e)[:200])
        await pg.wait_for_timeout(1000)
        try:
            await pg.evaluate("()=>{const b=document.querySelector('#login_button'); if(b){b.click(); return 'clicked';} if(typeof pt_login!=='undefined'){return 'pt_login exists';} return 'no btn';}")
        except Exception as e: print("click err",str(e)[:150])
        await pg.wait_for_timeout(9000)
        print("URL:",pg.url)
        try: print("TEXT:", (await pg.evaluate("()=>document.body.innerText"))[:500].replace("\n"," | "))
        except: pass
        for f in pg.frames: print("FRAME:", f.url[:140])
        await pg.screenshot(path=".auth/s5.png", full_page=True)
        await ctx.storage_state(path=".auth/state4.json")
        await b.close()
asyncio.run(main())
