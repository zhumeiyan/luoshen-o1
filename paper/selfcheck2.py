import struct, os, hashlib
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 768
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
if not os.path.exists(FONT):
    for c in ["/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"]:
        if os.path.exists(c): FONT = c; break

# 帧缓冲真实参数（ioctl 实测）
try:
    import fcntl
    FB = "/dev/fb0"
    with open(FB, "rb") as f:
        fi = struct.unpack("IHHIIIII", fcntl.ioctl(f.fileno(), 0x4600, b"\0"*32)[:32])
    # 用 sysfs 兜底
    xs = open("/sys/class/graphics/fb0/virtual_size").read().split(",")
    W, H = int(xs[0]), int(xs[1])
    bpp = int(open("/sys/class/graphics/fb0/bits_per_pixel").read())
except Exception:
    bpp = 32
print("FB:", W, H, bpp)

img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
d = ImageDraw.Draw(img)
try:
    fT = ImageFont.truetype(FONT, 30); fH = ImageFont.truetype(FONT, 22); fS = ImageFont.truetype(FONT, 19)
except Exception:
    fT = fH = fS = ImageFont.load_default()

TOKEN = "T7K4QX"   # 无易混淆字符
y = 34
d.text((44, y), "专利与论文 — 决策清单 (2026-10-18)", font=fT, fill=(0,0,0,255)); y += 52
d.line([(44,y),(W-44,y)], fill=(0,0,0,255), width=2); y += 24

rows = [
    ("1 公开边界", "GitHub public, 远端停在 exp079 (10-16)"),
    ("2 已丧失新颖性", "exp001-079 全部不可申"),
    ("3 新颖性仍在", "exp080-139 从未推送 = 窗口还在"),
    ("4 宽限期", "不适用: 自己开源不在专利法24条内"),
    ("5 顺序铁律", "先递交申请 -> 再发论文 不可逆"),
    ("6 论文风险", "引用125/126/127/128/138/139 全未公开"),
    ("7 版权", "代码写完自动享有, 登记仅取证"),
    ("8 软著", "中国版权保护中心, 成本最低"),
    ("9 商业秘密", "未公开部分零成本, 与专利二选一"),
    ("10 不可申", "科学发现本身 + 5项在先技术"),
]
for k, v in rows:
    d.text((56, y), k, font=fH, fill=(0,0,0,255))
    d.text((300, y), v, font=fS, fill=(0,0,0,255))
    y += 42

y += 8
d.line([(44,y),(W-44,y)], fill=(0,0,0,255), width=2); y += 22
d.text((56, y), "TOKEN " + TOKEN, font=fT, fill=(0,0,0,255)); y += 44
d.text((56, y), "论文 Chiral_Blindness.md 12节 27273B | 交底书 5部分", font=fS, fill=(0,0,0,255)); y += 34
d.text((56, y), "下一步: 保住未公开区间, 再决定专利或商业秘密", font=fS, fill=(0,0,0,255))

img.convert("RGBA").save("render2.png")
raw = img.convert("RGBA").tobytes()
print("render bytes:", len(raw))
open("render2.raw","wb").write(raw)

# 写帧缓冲
n = -1
try:
    with open("/dev/fb0","wb") as f:
        n = f.write(raw)
except Exception as e:
    print("fb write fail:", e)
print("wrote:", n)

# 回采
try:
    with open("/dev/fb0","rb") as f:
        cap = f.read(len(raw))
    print("captured:", len(cap))
    print("sha equal:", hashlib.sha256(raw).hexdigest()==hashlib.sha256(cap).hexdigest())
    open("captured2.raw","wb").write(cap)
    Image.frombytes("RGBA",(W,H),cap).convert("RGB").save("captured2.png")
except Exception as e:
    print("fb read fail:", e)
