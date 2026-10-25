import asyncio, json
from playwright.async_api import async_playwright
OUT="/data/workspace/luoshen-o1/experiments/exp093_human_door"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
        pg = await b.new_page(viewport={"width":1280,"height":900})
        await pg.goto("https://mail.qq.com", timeout=45000, wait_until="domcontentloaded")
        await pg.wait_for_timeout(6000)
        tgt=None
        for f in pg.frames:
            if "xlogin" in f.url: tgt=f; break
        # 真鼠标：先取主视口绝对坐标
        bb = await tgt.locator("#switcher_plogin").bounding_box()
        print("switcher bbox(main viewport):", bb)
        if bb:
            cx, cy = bb["x"]+bb["width"]/2, bb["y"]+bb["height"]/2
            await pg.mouse.move(cx-30, cy-20)   # 真实移动轨迹
            await pg.mouse.move(cx, cy)
            await pg.mouse.click(cx, cy)        # 真实按下抬起
            print(f"REAL MOUSE CLICK at ({cx:.0f},{cy:.0f})")
        await pg.wait_for_timeout(3500)
        after = await tgt.evaluate("""() => {
          const out={inputs:[],text:document.body.innerText.slice(0,300)};
          document.querySelectorAll('input').forEach(e=>{const r=e.getBoundingClientRect();
            out.inputs.push({id:e.id,type:e.type,ph:e.placeholder,w:Math.round(r.width),h:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y)});});
          ['web_qr_login','qr_area'].forEach(id=>{const e=document.getElementById(id);
            if(e){const cs=getComputedStyle(e);out[id]={display:cs.display,w:Math.round(e.getBoundingClientRect().width)};}});
          return out;}""")
        print(json.dumps(after,ensure_ascii=False,indent=1))
        await pg.screenshot(path=f"{OUT}/after_pwd_switch.png")
        await b.close()
asyncio.run(main())
