import cv2, numpy as np, json
from playwright.sync_api import sync_playwright
from run import Eye, slow_ocr, HTML
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_page(viewport={"width":1024,"height":768})
    eye = Eye(pg, "shots_test")
    got = eye.build_templates()
    print("templates:", got)
    pg.goto(f"{HTML}?seed=1001&shuffle=0&modal=0"); pg.wait_for_timeout(150)
    g,p = eye.shot()
    slow = slow_ocr(g)
    modal, fast, nb = eye.look()
    print("slow OCR:", {k:(round(v[0]),round(v[1])) for k,v in slow.items()})
    print("fast px :", {k:(round(v[0]),round(v[1])) for k,v in fast.items()}, "boxes",nb,"modal",modal)
    for w in ("ALPHA","BETA","GAMMA","DELTA"):
        if w in slow and w in fast:
            print("  ",w,"dist %.1f"%np.hypot(slow[w][0]-fast[w][0], slow[w][1]-fast[w][1]))
    # 点击验证真实鼠标
    from run import Hand
    h=Hand(pg)
    if "BETA" in fast: h.click(fast["BETA"][0], fast["BETA"][1])
    st=pg.evaluate("window.__state()"); ev=pg.evaluate("window.__events()")
    print("after click state:", st)
    print("events:", [(e['t'],e['x'],e['y'],e['tg']) for e in ev[:4]])
    br.close()
