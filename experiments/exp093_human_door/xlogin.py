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
            if "xlogin" in f.url:
                tgt=f; break
        print("xlogin frame:", tgt.url[:120] if tgt else None)
        raw = await tgt.evaluate("""() => {
          const out={inputs:[],hidden:[],clickable:[],text:document.body.innerText.slice(0,300)};
          document.querySelectorAll('input').forEach(e=>{const r=e.getBoundingClientRect();
            out.inputs.push({id:e.id,type:e.type,w:Math.round(r.width),h:Math.round(r.height),x:Math.round(r.x),y:Math.round(r.y)});});
          // 找出被隐藏的祖先
          ['web_qr_login','login','switcher_plogin','qr_area'].forEach(id=>{
            const e=document.getElementById(id);
            if(e){const cs=getComputedStyle(e);const r=e.getBoundingClientRect();
              out.hidden.push({id:id,display:cs.display,vis:cs.visibility,w:Math.round(r.width),h:Math.round(r.height)});}
          });
          document.querySelectorAll('a,div[id],span[id]').forEach(e=>{const r=e.getBoundingClientRect();
            if(r.width>0&&r.height>0&&e.innerText&&e.innerText.trim().length<12)
              out.clickable.push({tag:e.tagName,id:e.id,txt:e.innerText.trim().slice(0,12),x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)});});
          return out;}""")
        print(json.dumps(raw,ensure_ascii=False,indent=1))
        await pg.screenshot(path=f"{OUT}/xlogin_before.png")
        await b.close()
asyncio.run(main())
