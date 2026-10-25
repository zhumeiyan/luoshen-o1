"""095：像人一样拖——不算，只边看边动。
闭环策略只有一条 if：在目标左边就往右挪一点，反之往左，然后重新看。
开环策略：看一次，算好总位移，闭眼一次走完。
"""
import os, time, json, sys, struct, fcntl
from PIL import Image
from playwright.sync_api import sync_playwright

# ---- 眼：只从截图像素里找红(handle)和绿(target)，不读页面任何变量 ----
def see(path):
    im = Image.open(path).convert("RGB"); W,H = im.size; px = im.load()
    rh, rt = int(H*0.24), int(H*0.76); reds=[]; greens=[]
    for x in range(W):
        r1,g1,b1 = px[x,rh]
        r2,g2,b2 = px[x,rt]
        if r1>150 and g1<90 and b1<90: reds.append(x)
        if g2>150 and r2<90 and b2<90: greens.append(x)
    return (sum(reds)/len(reds) if reds else None, sum(greens)/len(greens) if greens else None)

TOL, STEP, MAXSTEP = 12, 14, 80
CLIP = {"x":0,"y":150,"width":1000,"height":105}
Y = 175

def trial(pw, url, st, tag):
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                           args=["--no-sandbox","--disable-dev-shm-usage"])
    pg = b.new_page(viewport={"width":1000,"height":300})
    pg.goto(url); pg.wait_for_timeout(300)
    shot = f"{tag}.png"
    pg.screenshot(path=shot, clip=CLIP); hx,tx = see(shot)
    if hx is None or tx is None:
        b.close(); return {"steps":0,"first_err":None,"final_err":None,"hit":False,"traj":[]}
    first = abs(tx-hx); traj=[]
    mx = hx                                        # 手当前在哪（真实坐标）
    pg.mouse.move(mx, Y); pg.mouse.down()          # 手按下
    pg.wait_for_timeout(60)
    if st == "open":
        # 计算派：看一眼，算总位移，闭眼一次走完（假设一步=一步位移）
        n = int(round(abs(tx-hx)/STEP)); d = STEP if tx>hx else -STEP
        for i in range(min(n,MAXSTEP)):
            mx += d; pg.mouse.move(mx, Y)
        pg.wait_for_timeout(150)
    else:
        # 人类派：不算距离、不算函数——只问"它在哪边"，动一点，再看
        for _ in range(MAXSTEP):
            if tx is None or hx is None: break
            err = tx - hx
            if abs(err) <= TOL: break
            mx += (STEP if err>0 else -STEP)
            pg.mouse.move(mx, Y)
            pg.screenshot(path=shot, clip=CLIP); hx,tx = see(shot); traj.append(round(err,1))
    pg.mouse.up(); pg.wait_for_timeout(120)
    pg.screenshot(path=shot, clip=CLIP); fx,ftx = see(shot)
    fin = None if (fx is None or ftx is None) else abs(fx-ftx)
    b.close()
    return {"steps":len(traj) if st=="closed" else min(int(round(first/STEP)),MAXSTEP),
            "first_err":round(first,1), "final_err":round(fin,1) if fin is not None else None,
            "hit":bool(fin is not None and fin<=TOL), "traj":traj[:8]}

scene, st = sys.argv[1], sys.argv[2]
gain = 1.7 if scene=="失配" else 1.0
mp   = "drift" if scene=="会动" else "honest"
url  = f"http://127.0.0.1:8899/page.html?mode={mp}&gain={gain}"
with sync_playwright() as pw:
    r = trial(pw, url, st, f"s_{scene}_{st}")
r["scene"]=scene; r["策略"]="人类派(边看边动)" if st=="closed" else "计算派(一次算完)"
print(json.dumps({k:v for k,v in r.items() if k!="traj"}, ensure_ascii=False), "traj前8:", r["traj"])
json.dump(r, open(f"r_{scene}_{st}.json","w"), ensure_ascii=False)
