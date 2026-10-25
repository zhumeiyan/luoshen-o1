# -*- coding: utf-8 -*-
"""113 出图 + 上屏自检(渲染->写 fb0->真实采集->OCR 回读)"""
import os, sys, json, struct, subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
FIG = "/data/workspace/luoshen-o1/fig/113_learn_look.png"
os.makedirs(os.path.dirname(FIG), exist_ok=True)

r113 = json.load(open(os.path.join(OUT, "result113.json")))
r113b = json.load(open(os.path.join(OUT, "result113b.json")))
r113c2 = json.load(open(os.path.join(OUT, "result113c2.json")))

res = r113["res"]
sweep = r113b["sweep"]
ref = r113b["ref"]
pairs = r113c2["pairs"]

fig, ax = plt.subplots(2, 3, figsize=(16, 9))
fig.suptitle("113 · 在真实 I/O 上学会往哪看   (fb0 眼 / uinput 手 / 内核读回)", fontsize=13)

# ---- (0,0) 世界A ----
a = ax[0, 0]
keys = ["A:preset", "A:learned", "A:blind", "A:scrambled", "A:static"]
vals = [res[k]["acc"] for k in keys]
cols = ["#2c7fb8", "#d95f02", "#999999", "#cccccc", "#666666"]
a.bar([k.split(":")[1] for k in keys], vals, color=cols)
a.axhline(ref["blind"], ls="--", c="#999", lw=1, label=f"blind {ref['blind']:.3f}")
a.set_title("世界A 命中率 (过程中是否曾看到目标)")
a.set_ylim(0, max(vals) * 1.35 + 0.02)
for i, v in enumerate(vals):
    a.text(i, v + 0.012, f"{v:.3f}", ha="center", fontsize=9)
a.legend(fontsize=8)

# ---- (0,1) 世界B 迁移 ----
a = ax[0, 1]
keys = ["B:learned_retrain", "B:blind", "B:learned_frozen", "B:static", "B:preset"]
vals = [res[k]["acc"] for k in keys]
cols = ["#d95f02", "#999999", "#fdae61", "#666666", "#2c7fb8"]
a.bar([k.split(":")[1] for k in keys], vals, color=cols)
a.set_title("世界B (目标分布反转) —— 迁移的真正检验")
a.set_ylim(0, max(vals) * 1.35 + 0.02)
for i, v in enumerate(vals):
    a.text(i, v + 0.012, f"{v:.3f}", ha="center", fontsize=9)

# ---- (0,2) 训练量剂量扫描 ----
a = ax[0, 2]
xs = sorted(sweep.keys(), key=lambda k: int(k))
ys = [sweep[k]["acc"] for k in xs]
a.plot([int(k) for k in xs], ys, "o-", c="#d95f02", label="learned")
a.axhline(res["A:preset"]["acc"], ls="-", c="#2c7fb8", label=f"preset {res['A:preset']['acc']:.3f}")
a.axhline(ref["blind"], ls="--", c="#999", label=f"blind {ref['blind']:.3f}")
a.set_xscale("log")
a.set_xlabel("训练 trial 数 (log)")
a.set_ylabel("命中率")
a.set_title("剂量扫描: 训练量 ×50 也追不上 —— 平的")
a.legend(fontsize=8)

# ---- (1,0) 训练曲线 ----
a = ax[1, 0]
tc = np.asarray(r113["train_curve"], float)
k = 25
sm = np.convolve(tc, np.ones(k) / k, mode="valid")
a.plot(sm, c="#d95f02", lw=1.2)
a.set_xlabel("训练 trial"); a.set_ylabel("最小距离 (px)")
a.set_title(f"学习曲线 (ε 1.0→0.05)   {sm[0]:.0f} → {sm[-1]:.0f} px")

# ---- (1,1) 引擎配对 ----
a = ax[1, 1]
names = list(pairs.keys())
ds = [pairs[k]["d"] for k in names]
los = [pairs[k]["lo"] for k in names]
his = [pairs[k]["hi"] for k in names]
y = np.arange(len(names))
a.errorbar(ds, y, xerr=[np.array(ds) - np.array(los), np.array(his) - np.array(ds)],
           fmt="o", c="#333", ecolor="#888", capsize=3)
a.axvline(0, c="r", lw=1)
a.set_yticks(y); a.set_yticklabels(names, fontsize=8)
a.set_title("引擎: 同种子配对差 (n=48) —— 全部跨 0")
a.set_xlabel("Δ 偏度")

# ---- (1,2) 可证伪自检 ----
a = ax[1, 2]
a.axis("off")
txt = [
    "可证伪性自检",
    "",
    f"眼  fb0 {r113['eye_falsifiable']}",
    f"   目标区 {r113['eye_on']:.5f} vs 空白 {r113['eye_off']:.5f}",
    f"   比值 {r113['eye_on']/max(r113['eye_off'],1e-9):.0f}×  (未饱和)",
    "",
    f"手  uinput {r113['hand_falsifiable']}",
    f"   通 读回 {tuple(r113['hand_on_readback'])}",
    f"   断 读回 {tuple(r113['hand_off_readback'])}  ← 可证伪",
    "",
    f"节点 {r113['hand_node']}",
    f"真实抓帧 {r113['n_grab']} 次",
]
a.text(0.03, 0.97, "\n".join(txt), va="top", fontsize=10, family="monospace")

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(FIG, dpi=110)
print("fig ->", FIG)

# ===========================================================================
# 上屏自检: 渲染 -> 写 fb0 -> 真实采集 -> OCR 回读
# ===========================================================================
CODE = "6KZ3QP"
lines = [
    "EO 113 SELFCHECK",
    f"CODE {CODE}",
    f"A PRESET  {res['A:preset']['acc']:.3f}",
    f"A LEARNED {res['A:learned']['acc']:.3f}",
    f"B PRESET  {res['B:preset']['acc']:.3f}",
    f"B RETRAIN {res['B:learned_retrain']['acc']:.3f}",
    f"SWEEP 5000 {sweep['5000']['acc']:.3f}",
    f"PAIR LP {pairs['learned-preset']['d']:+.4f}",
    f"EYE RATIO {r113['eye_on']/max(r113['eye_off'],1e-9):.0f}",
]
img = Image.new("RGB", (1024, 768), (255, 255, 255))
d = ImageDraw.Draw(img)
fp = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
try:
    font = ImageFont.truetype(fp, 34)
except Exception:
    font = ImageFont.load_default()
for i, s in enumerate(lines):
    d.text((40, 40 + i * 58), s, fill=(0, 0, 0), font=font)
rgba = np.array(img.convert("RGBA"))

fd = open("/dev/fb0", "r+b")
os.lseek(fd.fileno(), 0, os.SEEK_SET)
fd.write(rgba.tobytes())
os.lseek(fd.fileno(), 0, os.SEEK_SET)
raw = fd.read(1024 * 768 * 4)
fd.close()
arr = np.frombuffer(raw, dtype=np.uint8).reshape(768, 1024, 4)
Image.fromarray(arr[:, :, :3]).save(os.path.join(OUT, "captured113.png"))
print("captured ->", os.path.join(OUT, "captured113.png"))

txt = subprocess.run(["tesseract", os.path.join(OUT, "captured113.png"), "stdout"],
                     capture_output=True, text=True).stdout
hit = sum(1 for s in lines if s.split()[-1] in txt.replace(" ", ""))
print("OCR out:\n", txt[:600])
print(f"OCR hit {hit}/{len(lines)}  code_in={CODE in txt}")

json.dump(dict(code=CODE, lines=lines, ocr_hit=hit, n_lines=len(lines),
               code_found=CODE in txt),
          open(os.path.join(OUT, "selfcheck113.json"), "w"), ensure_ascii=False, indent=2)
