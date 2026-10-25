import cv2, numpy as np, json, subprocess
cases=json.load(open("cases.json"))
def geom(p):
    im=cv2.imread(p,0)[:330]           # 只看图形区
    _,bw=cv2.threshold(im,128,255,cv2.THRESH_BINARY_INV)
    cnts,_=cv2.findContours(bw,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cnts=[c for c in cnts if cv2.contourArea(c)>2000]
    c=sorted(cnts,key=lambda c:cv2.boundingRect(c)[1])[0]
    A=cv2.contourArea(c);P=cv2.arcLength(c,True);circ=4*np.pi*A/(P*P)
    hull=cv2.convexHull(c);sol=A/cv2.contourArea(hull)
    v=len(cv2.approxPolyDP(c,0.03*P,True))
    g="circle" if circ>0.82 else ("star" if (v>=8 and sol<0.75) else ("triangle" if v<=3 else "square"))
    return g
def ocr(p):
    im=cv2.imread(p,0)[340:]           # 只看文字区
    cv2.imwrite("_t.png",im)
    r=subprocess.run(["tesseract","_t.png","stdout","-l","chi_sim","--psm","10"],
                     capture_output=True,text=True)
    return "".join(r.stdout.split()).strip()
lab={"circle":"圆","square":"方","triangle":"三角","star":"星"}
res=[]
for c in cases:
    g=geom(c["path"]); t=ocr(c["path"])
    ocr_ok = (t==c["text"]) if c["text"] else (t=="")
    geo_ok = (g==c["shape"])
    conflict = None
    if c["text"]:
        inv={v:k for k,v in lab.items()}
        conflict = (t in inv) and (inv[t]!=g)
    res.append({**c,"geom":g,"ocr":t,"ocr_ok":ocr_ok,"geo_ok":geo_ok,"conflict":conflict})
json.dump(res,open("read2.json","w"),ensure_ascii=False,indent=1)
print(f'{"shape":9s} {"mode":9s} 字真值 OCR  字对 | 形真值 几何  形对 | 矛盾检出')
for r in res:
    print(f'{r["shape"]:9s} {r["mode"]:9s} {str(r["text"]):5s} {r["ocr"]:5s} {str(r["ocr_ok"]):5s} | {r["shape"]:9s} {r["geom"]:9s} {str(r["geo_ok"]):5s} | {r["conflict"]}')
import collections
print("\n几何准确率", sum(r["geo_ok"] for r in res),"/",len(res))
print("OCR准确率(有字组)", sum(r["ocr_ok"] for r in res if r["text"]),"/",len([r for r in res if r["text"]]))
print("无字组幻觉数", sum(1 for r in res if not r["text"] and r["ocr"]!=""),"/",len([r for r in res if not r["text"]]))
cf=[r for r in res if r["mode"]=="conflict"]
print("矛盾检出", sum(1 for r in cf if r["conflict"]),"/",len(cf))
