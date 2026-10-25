import asyncio, json
from playwright.async_api import async_playwright
OUT="/data/workspace/luoshen-o1/experiments/exp093_human_door"

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
        pg = await b.new_page(viewport={"width":1280,"height":900})
        await pg.goto("https://mail.qq.com", timeout=45000, wait_until="domcontentloaded")
        await pg.wait_for_timeout(5000)
        fr = pg.frames
        print("frames:", len(fr))
        for f in fr:
            print(" -", f.url[:100])
        # 找到登录 iframe
        target=None
        for f in fr:
            if "graph.qq.com" in f.url or "xlogin" in f.url or "ptlogin" in f.url:
                target=f; break
        if target is None and len(fr)>1:
            target = fr[1]
        if target:
            info = await target.evaluate("""() => {
              const out={url:location.href,title:document.title,
                inputs:[],clickable:[],text:document.body?document.body.innerText.slice(0,400):'',
                bodySize:document.body?document.body.getBoundingClientRect().width+'x'+document.body.getBoundingClientRect().height:''};
              document.querySelectorAll('input').forEach(e=>{const r=e.getBoundingClientRect();
                out.inputs.push({id:e.id,type:e.type,ph:e.placeholder,w:Math.round(r.width),h:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y)});});
              document.querySelectorAll('a,span,div[id]').forEach(e=>{const r=e.getBoundingClientRect();
                if(r.width>0&&r.height>0&&e.innerText&&e.innerText.trim().length<20)
                  out.clickable.push({tag:e.tagName,id:e.id,txt:e.innerText.trim().slice(0,20),x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)});});
              return out;}""")
            print(json.dumps(info,ensure_ascii=False,indent=1))
            await pg.screenshot(path=f"{OUT}/iframe_view.png")
        await b.close()
asyncio.run(main())
