import cv2,numpy as np,subprocess
im0=cv2.imread("screen2.png"); H,W,_=im0.shape
# 内容区：等比后居中，按 480 高占比取图形/文字分界
top=im0[:int(H*0.687)]
gg=cv2.cvtColor(top,cv2.COLOR_BGR2GRAY)
_,bw=cv2.threshold(gg,128,255,cv2.THRESH_BINARY_INV)
c=[x for x in cv2.findContours(bw,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0] if cv2.contourArea(x)>5000]
c=sorted(c,key=lambda x:cv2.boundingRect(x)[1])[0]
A=cv2.contourArea(c);P=cv2.arcLength(c,True);circ=4*np.pi*A/(P*P)
v=len(cv2.approxPolyDP(c,0.03*P,True))
x,y,w_,h_=cv2.boundingRect(c); ar=w_/h_
geom="circle" if circ>0.82 else ("star" if v>=8 else ("triangle" if v<=3 else "square"))
t=im0[int(H*0.71):]; cv2.imwrite("_s2.png",t)
ocr="".join(subprocess.run(["tesseract","_s2.png","stdout","-l","chi_sim","--psm","10"],capture_output=True,text=True).stdout.split()).strip()
print(f'采集图 {W}x{H} → 几何={geom} (circ={circ:.3f} v={v} 长宽比={ar:.2f}) ; OCR={ocr}')
print("真值 画=circle / 写=方  → 矛盾检出:", ocr=="方" and geom=="circle")
