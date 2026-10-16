"""造一台带屏幕的电脑：帧缓冲 = 屏幕；PNG 截图 = 摄像头拍照；OCR = 视觉读出。"""
from PIL import Image, ImageDraw, ImageFont
import os
W,H = 1280,720
fb = Image.new("RGB",(W,H),(0,0,0))
d  = ImageDraw.Draw(fb)
# 找中文字体
cands = ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
         "/usr/share/fonts/truetype/arphic/uming.ttc"]
font=None
for c in cands:
    if os.path.exists(c):
        try: font=ImageFont.truetype(c,72); break
        except Exception: pass
if font is None: font=ImageFont.load_default()
d.rectangle([0,0,W,H], fill=(0,0,0))
d.text((60,80),  "硅基视觉 通路闭合", font=font, fill=(0,255,0))
d.text((60,200), "SCREEN OK 12345",  font=font, fill=(0,255,0))
d.rectangle([60,340,400,600], outline=(255,0,0), width=8)
fb.save("/data/workspace/luoshen-o1/.sense/screen.png")
print("framebuffer -> screen.png", os.path.getsize("/data/workspace/luoshen-o1/.sense/screen.png"), "bytes")
