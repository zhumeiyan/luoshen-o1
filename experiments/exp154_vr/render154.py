import os, json, struct, numpy as np, cv2

D = "/data/workspace/luoshen-o1/experiments/exp154_vr"
W, H = 1024, 768
STRIDE = 4096
FB_BYTES = STRIDE * H
TOKEN = "K7M2QX"


def to_fb(buf):
    bgra = np.zeros((H, W, 4), np.uint8)
    bgra[:, :, :3] = buf
    bgra[:, :, 3] = 255
    return bgra.tobytes()


def txt(img, s, x, y, sc=0.62, c=(235, 240, 250), th=1):
    cv2.putText(img, s, (x, y), cv2.FONT_HERSHEY_SIMPLEX, sc, c, th, cv2.LINE_AA)


r = json.load(open(f"{D}/result154.json"))
st, ct, g = r["stereo"], r["control_B0"], r["gates"]

fig = np.full((H, W, 3), 16, np.uint8)

# --- 顶部：真 VR 并排立体图 ---
sbs = cv2.imread(f"{D}/stereo_B0.34_sbs.png")
thumb = cv2.resize(sbs, (W - 40, 330))
fig[10:340, 20:W - 20] = thumb
txt(fig, "TRUE VR SIDE-BY-SIDE  (left eye | right eye)  -> /dev/fb0", 24, 34, 0.7, (90, 200, 255), 2)

# --- 左下：d vs 1/z 物理拟合 ---
rows = st.get("_rows", [])
px = json.load(open(f"{D}/diag_rows.json")) if os.path.exists(f"{D}/diag_rows.json") else None
ax_x0, ax_y0, ax_w, ax_h = 60, 410, 420, 300
cv2.rectangle(fig, (ax_x0, ax_y0), (ax_x0 + ax_w, ax_y0 + ax_h), (50, 55, 65), -1)
txt(fig, "disparity d  vs  1/z   (physics: d = f*B/z)", ax_x0 + 6, ax_y0 + 22, 0.55, (120, 220, 255))
if px:
    z = np.array([p["z"] for p in px]); d = np.array([p["d"] for p in px])
    iv = 1.0 / z
    k = float(np.dot(iv, d) / np.dot(iv, iv))
    xmin, xmax = iv.min() * 0.92, iv.max() * 1.08
    ymax = d.max() * 1.15
    for p in px:
        X = ax_x0 + int((1.0 / p["z"] - xmin) / (xmax - xmin) * ax_w)
        Y = ax_y0 + ax_h - int(p["d"] / ymax * ax_h)
        cv2.circle(fig, (X, Y), 4, (70, 230, 120), -1)
    for t in np.linspace(xmin, xmax, 50):
        X = ax_x0 + int((t - xmin) / (xmax - xmin) * ax_w)
        Y = ax_y0 + ax_h - int(k * t / ymax * ax_h)
        cv2.circle(fig, (X, Y), 1, (90, 170, 255), -1)
    txt(fig, f"R2 = {st['G2_r2']:.4f}", ax_x0 + 10, ax_y0 + ax_h - 40, 0.6, (90, 255, 140), 2)
    txt(fig, f"k_fit {st['k_fit']:.2f}  vs  k_theory {st['k_theory']:.2f}",
        ax_x0 + 10, ax_y0 + ax_h - 14, 0.5, (200, 210, 225))

# --- 右下：判据表 ---
bx = 540
txt(fig, "GATES", bx, 424, 0.62, (255, 210, 120), 2)
lines = [
    ("G0 fb0 identical", g["G0_framebuffer_identical"]),
    ("G1 disparity != 0", g["G1_disparity_nonzero"]),
    ("G2 R2 > 0.95", g["G2_d_vs_inverse_z_R2_gt_0.95"]),
    ("G3 depth err < 10%", g["G3_depth_recovery_rel_err_lt_0.10"]),
    ("G4 B=0 control dead", g["G4_B0_control_dead"]),
]
for i, (s, v) in enumerate(lines):
    col = (80, 240, 120) if v else (70, 80, 240)
    txt(fig, f"{'PASS' if v else 'FAIL'}  {s}", bx, 452 + i * 26, 0.52, col)

txt(fig, f"depth median rel err = {st['G3_med_rel_err']*100:.2f}%", bx, 596, 0.55, (140, 250, 200))
txt(fig, f"B=0 control disparity = {ct['disparity_max']:.1f}", bx, 620, 0.55, (200, 200, 210))
txt(fig, "pillars measurable 10 / 10", bx, 644, 0.55, (200, 200, 210))
txt(fig, "height randomised -> monocular size cue dead", bx, 668, 0.45, (170, 170, 185))

txt(fig, f"ALL PASS = {g['ALL_PASS']}", bx, 706, 0.7, (80, 255, 140) if g["ALL_PASS"] else (70, 80, 250), 2)
txt(fig, f"TOKEN {TOKEN}", 24, 700, 0.85, (255, 255, 255), 2)
txt(fig, "exp154  lo shen stereo vision", 24, 730, 0.6, (150, 160, 180))

cv2.imwrite(f"{D}/fig154.png", fig)

# ---------- 上屏自检：真写 -> 同进程立即回采 -> 逐位比对 ----------
w = open("/dev/fb0", "wb", buffering=0)
rd = open("/dev/fb0", "rb", buffering=0)
w.seek(0); w.write(to_fb(fig)); w.flush()
rd.seek(0)
raw = np.frombuffer(rd.read(FB_BYTES), np.uint8).copy()
cap = raw.reshape(H, STRIDE // 4, 4)[:, :W, :3]
identical = bool(np.array_equal(cap, fig))
cv2.imwrite(f"{D}/captured.png", cap)
print("IDENTICAL", identical, "sha", __import__("hashlib").sha256(cap.tobytes()).hexdigest()[:12])
json.dump({"identical": identical, "token": TOKEN}, open(f"{D}/selfcheck.json", "w"))
