import asyncio, os, json
from playwright.async_api import async_playwright

OUT = "/data/workspace/luoshen-o1/experiments/exp093_human_door"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",
                                    args=["--no-sandbox","--disable-dev-shm-usage"])
        pg = await b.new_page(viewport={"width":1280,"height":900})
        res = {}
        for name, url in [("mail","https://mail.qq.com"),("wxmail","https://wx.mail.qq.com")]:
            try:
                r = await pg.goto(url, timeout=45000, wait_until="domcontentloaded")
                await pg.wait_for_timeout(4000)
                await pg.screenshot(path=f"{OUT}/{name}.png")
                # 读 DOM 关键元素
                info = await pg.evaluate("""() => {
                    const out = {url: location.href, title: document.title,
                      inputs: [], iframes: [], text: document.body?document.body.innerText.slice(0,600):''};
                    document.querySelectorAll('input').forEach(e=>{
                      const r=e.getBoundingClientRect();
                      out.inputs.push({id:e.id,type:e.type,ph:e.placeholder,w:Math.round(r.width),h:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y)});
                    });
                    document.querySelectorAll('iframe').forEach(e=>{
                      const r=e.getBoundingClientRect();
                      out.iframes.push({src:(e.src||'').slice(0,120),w:Math.round(r.width),h:Math.round(r.height)});
                    });
                    return out;
                }""")
                res[name] = {"status": r.status if r else None, **info}
            except Exception as e:
                res[name] = {"error": str(e)[:300]}
        await b.close()
        print(json.dumps(res, ensure_ascii=False, indent=1))

asyncio.run(main())
