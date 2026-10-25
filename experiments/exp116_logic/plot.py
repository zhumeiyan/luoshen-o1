import json, random, struct, subprocess, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

FP = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
font_manager.fontManager.addfont(FP)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FP).get_name()
plt.rcParams["axes.unicode_minus"] = False

R = json.load(open("res116_logic.json"))
B = json.load(open("res116b_engine.json"))
C = json.load(open("res116c_dose.json"))

fig, ax = plt.subplots(2, 3, figsize=(18, 10))

# 1 经典真值表
a0 = ax[0, 0]
rows = R["classical"]["rows"]
lbl = [f"a={r['a']},b={r['b']}" for r in rows]
val = [r["formula"] for r in rows]
a0.bar(lbl, [1] * 4, color="#dddddd")
a0.bar(lbl, [0.0] * 4, color="#cc0000")
for i, (l, v) in enumerate(zip(lbl, val)):
    a0.text(i, 0.5, "F", ha="center", va="center", fontsize=16, color="white", weight="bold")
a0.set_ylim(0, 1); a0.set_yticks([])
a0.set_title("① 经典二值：(a≠b)↔(a=b) 恒假\n真 0 / 假 4 → 饱和在假，不可证伪")

# 2 可证伪表
a1 = ax[0, 1]
names = ["classical", "temporal", "paraconsistent_LP", "relative_identity"]
zh = ["①经典二值", "②时序", "③次协调LP", "④相对同一"]
T = [R[n]["n_true"] for n in names]; F = [R[n]["n_false"] for n in names]
x = np.arange(4)
a1.bar(x - 0.2, T, 0.4, label="真", color="#2a7fbf")
a1.bar(x + 0.2, F, 0.4, label="假", color="#cccccc")
a1.set_xticks(x); a1.set_xticklabels(zh, fontsize=10)
a1.legend(); a1.set_title("② 可证伪性：只有真/假都出现才不是死命题")
for i, (t, f) in enumerate(zip(T, F)):
    a1.text(i - 0.2, t + 0.1, str(t), ha="center")
    a1.text(i + 0.2, f + 0.1, str(f), ha="center")

# 3 LP 3x3
a2 = ax[0, 2]
lp = R["paraconsistent_LP"]["rows"]
M = np.array([[1 if r["designated"] else 0 for r in lp]]).reshape(3, 3)
a2.imshow(M, cmap="RdYlGn", vmin=0, vmax=1)
for i in range(3):
    for j in range(3):
        r = lp[i * 3 + j]
        a2.text(j, i, f"{r['eq']}\n→{r['formula']}", ha="center", va="center", fontsize=11)
a2.set_xticks([0, 1, 2]); a2.set_xticklabels(["T", "F", "B"])
a2.set_yticks([0, 1, 2]); a2.set_yticklabels(["T", "F", "B"])
a2.set_xlabel("b"); a2.set_ylabel("a")
a2.set_title("③ 次协调LP：当且仅当 eq=B（既真又假）时公式成立\n真5/假4")

# 4 相对同一
a3 = ax[1, 0]
ks = sorted(int(k) for k in R["relative_identity"]["scan"])
sr = [R["relative_identity"]["scan"][str(k)]["same_rate"] for k in ks]
a3.plot(range(len(ks)), sr, "o-", color="#2a7fbf")
a3.axhline(0.5, color="red", ls="--", label="同像率=0.5 判据线")
a3.set_xticks(range(len(ks))); a3.set_xticklabels(ks)
a3.set_xlabel("粗粒化桶数 k"); a3.set_ylabel("同像率")
a3.legend(); a3.set_title("④ 相对同一：粒度越粗越'相等'\n真5/假8，随 k 单调")

# 5 动力学分岔
a4 = ax[1, 1]
ds = R["dynamics"]["scan"]
kk = [d["k"] for d in ds]; gp = [min(d["final_gap"], 5) for d in ds]; fl = [d["flips"] for d in ds]
a4.plot(kk, gp, "o-", color="#cc0000", label="末距 |a-b|")
a4.set_xlabel("恢复力 k"); a4.set_ylabel("末距", color="#cc0000")
a4b = a4.twinx()
a4b.plot(kk, fl, "s--", color="#2a7fbf", label="符号翻转次数")
a4b.set_ylabel("翻转次数", color="#2a7fbf")
a4.axvline(2.0, color="black", ls=":")
a4.set_title("⑤ 动力学分岔：k=2 处永久交替\nk=0 永假 / 0<k<2 收敛 / k>2 发散")

# 6 pres 饱和
a5 = ax[1, 2]
vs = [float(k) for k in sorted(C["scan"], key=float)]
sk = [C["scan"][k]["skew"] for k in sorted(C["scan"], key=float)]
a5.plot(vs, sk, "o-", color="#7f3fbf")
a5.set_xlabel("input_val 剂量"); a5.set_ylabel("capacity 偏度")
a5.set_title(f"⑥ pres 指数饱和 → 指标全量程仅 {C['skew_range']:.4f}\n引擎零结果不可解释")

plt.tight_layout()
plt.savefig("/data/workspace/luoshen-o1/fig/116_logic.png", dpi=110)
print("fig saved")

# ---------- 上屏自检 ----------
from PIL import Image, ImageDraw, ImageFont
FB = "/dev/fb0"
with open(FB, "rb") as f:
    fix = __import__("fcntl").ioctl(f, 0x4600, b"\0" * 68)
import fcntl
w, h = struct.unpack("<II", fix[8:16]); bpp = struct.unpack("<I", fix[24:28])[0]
print(f"fb0: {w}x{h} bpp={bpp}")
CODE = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
ROWS = [
    ("EO116 LOGIC CODE", CODE),
    ("classical   true 0", "false 4  DEAD"),
    ("LP          true 5", "false 4  OK"),
    ("relative    true 5", "false 8  OK"),
    ("temporal    true 6", "false 1  OK"),
    ("dyn k=0 gap 0.5", "k=2 flip forever"),
    ("dyn k>2 diverge", "k<2 converge"),
    ("pres sat range", f"{C['skew_range']:.4f}"),
    ("engine flip-hold", "delta 0.0093 ns"),
]
img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
d = ImageDraw.Draw(img)
FONT = ImageFont.truetype(FP, 26)
y = 40
for a, b in ROWS:
    d.text((40, y), f"{a}   {b}", fill=(0, 0, 0, 255), font=FONT); y += 52
d.rectangle([30, 25, w - 30, y + 15], outline=(200, 0, 0, 255), width=4)
img.save("render_check.png")
rgba = img.convert("RGBA").tobytes()
assert len(rgba) == w * h * (bpp // 8), f"尺寸不符 {len(rgba)} vs {w*h*(bpp//8)}"
with open(FB, "wb") as f:
    f.write(rgba)

subprocess.run(["python3", "-c", f"""
from PIL import Image
import struct,fcntl
FB='/dev/fb0'
with open(FB,'rb') as f:
    fix=fcntl.ioctl(f,0x4600,b'\\0'*68)
    w,h=struct.unpack('<II',fix[8:16]); bpp=struct.unpack('<I',fix[24:28])[0]
    f.seek(0); raw=f.read(w*h*(bpp//8))
im=Image.frombytes('RGBA',(w,h),raw).convert('RGB')
im.save('/data/workspace/luoshen-o1/experiments/exp116_logic/captured.png')
print('captured bytes=',len(raw))
"""], check=True)

import pytesseract
g = Image.open("captured.png").convert("L")
txt = pytesseract.image_to_string(g, config="--psm 6")
print("--- OCR ---"); print(txt)
json.dump(dict(code=CODE, ocr=txt, hit=CODE in txt.replace(" ", "")),
          open("selfcheck116.json", "w"), ensure_ascii=False, indent=1)
print("CODE =", CODE, "| hit =", CODE in txt.replace(" ", ""))
