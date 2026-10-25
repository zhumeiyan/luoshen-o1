from playwright.sync_api import sync_playwright
from run import Eye, slow_ocr, HTML
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_page(viewport={"width":1024,"height":768})
    eye = Eye(pg, "shots_test"); eye.build_templates()
    pg.goto(f"{HTML}?seed=1001&shuffle=0&modal=0"); pg.wait_for_timeout(150)
    g,p = eye.shot(); print("OCR:", slow_ocr(g))
    modal,pos,nb = eye.look()
    print("boxes",nb,"pos keys",list(pos.keys()))
    for s in eye.last_scores: print("  ",s)
    # 直接看每个模板与每个box的分数矩阵
    import cv2, numpy as np
    from run import geom_boxes
    boxes=geom_boxes(g)
    print("score matrix rows=boxes cols=templates")
    words=sorted(eye.tpl.keys())
    print("        "+"  ".join("%7s"%w for w in words))
    for (x,y,w,h) in boxes:
        roi=g[y:y+h,x:x+w]
        row=[]
        for wd in words:
            t=eye.tpl[wd]; th,tw=t.shape[:2]
            r=cv2.resize(roi,(tw,th),interpolation=cv2.INTER_AREA)
            row.append(float(cv2.matchTemplate(r,t,cv2.TM_CCOEFF_NORMED)[0][0]))
        print("box(%4d,%3d): "%(x,y)+"  ".join("%7.3f"%v for v in row))
    br.close()
