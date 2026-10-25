import asyncio, json, os, random, subprocess, cv2, numpy as np
from playwright.async_api import async_playwright
OUT="/data/workspace/luoshen-o1/experiments/exp093_human_door"
U=os.environ["QQ_U"]; P=os.environ["QQ_P"]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
        pg = await b.new_page(viewport={"width":1280,"height":900})
        # 记录所有请求/响应，看验证码资源到底加载了没
        log=[]
        pg.on("response", lambda r: log.append((r.status, r.url[:110])))
        await pg.goto("https://mail.qq.com", timeout=45000, wait_until="domcontentloaded")
        await pg.wait_for_timeout(6000)
        tgt=None
        for f in pg.frames:
            if "xlogin" in f.url: tgt=f; break
        bb = await tgt.locator("#switcher_plogin").bounding_box()
        await pg.mouse.click(bb["x"]+bb["width"]/2, bb["y"]+bb["height"]/2)
        await pg.wait_for_timeout(3000)
        ub = await tgt.locator("#u").bounding_box()
        await pg.mouse.click(ub["x"]+ub["width"]/2, ub["y"]+ub["height"]/2)
        for ch in U: await pg.keyboard.type(ch); await pg.wait_for_timeout(int(random.uniform(60,150)))
        pb = await tgt.locator("#p").bounding_box()
        await pg.mouse.click(pb["x"]+pb["width"]/2, pb["y"]+pb["height"]/2)
        for ch in P: await pg.keyboard.type(ch); await pg.wait_for_timeout(int(random.uniform(60,150)))
        lb = await tgt.locator("#login_button").bounding_box()
        await pg.mouse.click(lb["x"]+lb["width"]/2, lb["y"]+lb["height"]/2)
        await pg.wait_for_timeout(8000)
        await pg.screenshot(path=f"{OUT}/cap_full.png")
        # 验证码相关资源
        caprel=[l for l in log if any(k in l[1].lower() for k in ["captcha","cap_","cdc","tdc","drag","slide"])]
        print("=== CAPTCHA RESOURCES ===")
        for s,u_ in caprel[:25]: print(f"  {s}  {u_}")
        # 列出所有 frame
        print("=== FRAMES ===")
        for f in pg.frames: print("  -", f.url[:120])
        # 在验证码 frame 里找元素
        cf=None
        for f in pg.frames:
            if "captcha" in f.url or "drag" in f.url: cf=f; break
        if cf:
            info = await cf.evaluate("""() => {
              const out={url:location.href,text:document.body.innerText.slice(0,300),imgs:[],divs:[]};
              document.querySelectorAll('img').forEach(e=>{const r=e.getBoundingClientRect();
                out.imgs.push({src:(e.src||'').slice(0,90),w:Math.round(r.width),h:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y),nat:e.naturalWidth+'x'+e.naturalHeight});});
              document.querySelectorAll('div,span').forEach(e=>{const r=e.getBoundingClientRect();
                if(r.width>10&&r.height>10) out.divs.push({id:e.id,cls:(e.className||'').toString().slice(0,30),w:Math.round(r.width),h:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y)});});
              return out;}""")
            print(json.dumps(info,ensure_ascii=False,indent=1)[:2000])
        else:
            print("NO captcha frame found")
        await b.close()
asyncio.run(main())
