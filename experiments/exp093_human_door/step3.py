import asyncio, json, os, random, subprocess
from playwright.async_api import async_playwright
OUT="/data/workspace/luoshen-o1/experiments/exp093_human_door"
U=os.environ["QQ_U"]; P=os.environ["QQ_P"]

async def human_type(pg, text, delay_range=(0.08,0.22)):
    for ch in text:
        await pg.keyboard.type(ch)
        await pg.wait_for_timeout(int(random.uniform(*delay_range)*1000))

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

        # 真鼠标点账号框 + 真键盘敲
        ub = await tgt.locator("#u").bounding_box()
        await pg.mouse.click(ub["x"]+ub["width"]/2, ub["y"]+ub["height"]/2)
        await pg.wait_for_timeout(400)
        await human_type(pg, U)
        # 眼睛：读回输入框真实内容
        u_val = await tgt.locator("#u").input_value()

        pb = await tgt.locator("#p").bounding_box()
        await pg.mouse.click(pb["x"]+pb["width"]/2, pb["y"]+pb["height"]/2)
        await pg.wait_for_timeout(400)
        await human_type(pg, P)
        p_val = await tgt.locator("#p").input_value()

        await pg.screenshot(path=f"{OUT}/filled.png")
        print(json.dumps({"u_typed_len":len(U),"u_readback":u_val,
                          "u_match":u_val==U,"p_typed_len":len(P),
                          "p_readback_masked":"*"*len(p_val),"p_len_match":len(p_val)==len(P)},
                         ensure_ascii=False))
        # OCR 自己看一眼输入框区域
        import cv2
        img=cv2.imread(f"{OUT}/filled.png")
        ubx=int(ub["x"]); uby=int(ub["y"])
        crop=img[uby:uby+38, ubx:ubx+250]
        cv2.imwrite(f"{OUT}/crop_u.png", crop)
        subprocess.run(["python3","-c","""
import pytesseract,cv2,sys
im=cv2.imread('/data/workspace/luoshen-o1/experiments/exp093_human_door/crop_u.png')
im=cv2.resize(im,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
print('OCR_U:',repr(pytesseract.image_to_string(g,config='--psm 7').strip()))
"""],capture_output=True,text=True)
        r=subprocess.run(["python3","-c","""
import pytesseract,cv2
im=cv2.imread('/data/workspace/luoshen-o1/experiments/exp093_human_door/crop_u.png')
im=cv2.resize(im,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
print('OCR_U:',repr(pytesseract.image_to_string(g,config='--psm 7').strip()))
"""],capture_output=True,text=True)
        print(r.stdout.strip() or r.stderr.strip()[:200])
        await b.close()
asyncio.run(main())
