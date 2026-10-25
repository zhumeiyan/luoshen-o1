import numpy as np, cv2, subprocess, os
W,H=1024,768
img=cv2.imread("img_circle_conflict.png",0)
h,w=img.shape
s=min(H/h, W/w); nh,nw=int(h*s),int(w*s)
im=cv2.resize(img,(nw,nh),interpolation=cv2.INTER_LINEAR)
canvas=np.full((H,W),255,np.uint8)
canvas[(H-nh)//2:(H-nh)//2+nh, (W-nw)//2:(W-nw)//2+nw]=im
bgra=cv2.cvtColor(canvas,cv2.COLOR_GRAY2BGRA)
open("/dev/fb0","wb").write(bgra.tobytes())
subprocess.run(["ffmpeg","-y","-f","fbdev","-framerate","1","-i","/dev/fb0","-frames:v","1","screen2.png"],capture_output=True)
print("等比上屏",nw,"x",nh,"采集",os.path.getsize("screen2.png"))
