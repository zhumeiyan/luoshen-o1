import asyncio, json, os, random, subprocess
from playwright.async_api import async_playwright
OUT="/data/workspace/luoshen-o1/experiments/exp093_human_door"
U=os.environ["QQ_U"]; P=os.environ["QQ_P"]

def ocr(path, psm="6"):
    r=subprocess.run(["python3","-c",f"""
import pytesseract,cv2
im=cv2.imread('{path}')
g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
print(pytesseract.image_to_string(g,config='--psm {psm} -l chi_sim+eng').strip()[:500])
"""],capture_output=True,text=True)
    return (r.stdout or r.stderr)[:500]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--disable-dev-shm-usage"])
        pg = await b.new_page(viewport={"width":1280,"height":900})
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
        for ch in U: await pg.keyboard.type(ch); await pg.wait_for_timeout(int(random.uniform(80,200)))
        pb = await tgt.locator("#p").bounding_box()
        await pg.mouse.click(pb["x"]+pb["width"]/2, pb["y"]+pb["height"]/2)
        for ch in P: await pg.keyboard.type(ch); await pg.wait_for_timeout(int(random.uniform(80,200)))
        lb = await tgt.locator("#login_button").bounding_box()
        print("login_button bbox:", lb)
        await pg.mouse.move(lb["x"]+lb["width"]/2-40, lb["y"]+lb["height"]/2-15)
        await pg.mouse.move(lb["x"]+lb["width"]/2, lb["y"]+lb["height"]/2)
        await pg.mouse.click(lb["x"]+lb["width"]/2, lb["y"]+lb["height"]/2)
        print("CLICKED LOGIN")
        await pg.wait_for_timeout(7000)
        await pg.screenshot(path=f"{OUT}/after_login.png")
        print("=== URL:", pg.url[:150])
        st = await tgt.evaluate("""() => ({text:document.body.innerText.slice(0,400),
            visible_iframes:[...document.querySelectorAll('iframe')].map(e=>e.src.slice(0,80)),
            cap:[...document.querySelectorAll('img')].map(e=>e.src.slice(0,90)).slice(0,8)})""")
        print(json.dumps(st,ensure_ascii=False,indent=1))
        print("=== OCR after_login:")
        print(ocr(f"{OUT}/after_login.png"))
        await b.close()
asyncio.run(main())
