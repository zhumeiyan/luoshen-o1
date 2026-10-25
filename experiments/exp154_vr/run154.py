"""
154 —— 真 VR 的第一人称双目世界：并排立体 (side-by-side) 写进 /dev/fb0。

为什么只补"双目视差"这一件事：
  商业 VR 游戏里属于人类的部分（头显光学、透镜畸变、6DoF 前庭匹配、手柄人体工学）
  她都没有对应器官。真正属于她的只有三件：第一人称、3D 空间、可相倚交互。
  153 号已证伪后两件中的交互；本轮补第一件里 VR 独有的：**立体视觉**。

物理判据（不是我定的规则，是针孔几何）：
    视差 d = f * B / z        （f 焦距，B 瞳距，z 深度）
所以：
  G2  d 必须对 1/z 过原点线性 —— 这是物理定律，拟合不出来就说明渲染是假的
  G3  由 d 反推 z = fB/d，相对误差要小
  G4  B=0 阴性对照：左右逐位相同，视差恒 0，深度必然不可恢复
     —— 判据必须能同时产生真和假，否则只是装饰

单目陷阱：柱子高度随机化，让"越远越小"这个单目大小线索失效，
         于是只有视差能恢复深度。
"""
import os, json, struct, threading, time
import numpy as np
import cv2

W, H = 1024, 768
STRIDE = 4096
FB_BYTES = STRIDE * H
EW = W // 2          # 每只眼宽 512
CX = EW // 2         # 单眼画面中心 256
CY = H // 2
FOV_DEG = 75.0
F = (EW / 2.0) / np.tan(np.radians(FOV_DEG) / 2.0)   # 焦距(像素)
EYE_H = 0.5          # 相机高度
BASE_DEFAULT = 0.34  # 瞳距(世界单位)

RNG = np.random.default_rng(20261019)

# ---------- 世界：柱子 ----------
N_PILLARS = 10


def make_world():
    """
    154b 修摆放：按"屏幕走廊"反推世界 x。
      直接随机世界 x 会让柱子互相遮挡 / 被屏幕边缘裁切 -> 质心测到残片 -> 视差错。
      （诊断：z=1.65 误差 0.2%、z=2.12 误差 -0.7%，而远处全错 -> 物理对，摆放弃错）
    做法：先固定每根柱子投影中心的屏幕位置 uc_i（等间隔、留边距），
          再由 x = (uc_i - CX) * z / F 反解世界 x。
          只要最大投影宽度 < 走廊间隔，就保证互不遮挡、且完整在屏内。
    """
    ps = []
    hues = np.linspace(0, 179, N_PILLARS, endpoint=False).astype(int)
    RNG.shuffle(hues)
    margin = 70
    ucs = np.linspace(margin, EW - margin, N_PILLARS)   # 屏幕走廊中心
    zs = RNG.uniform(3.0, 8.5, N_PILLARS)
    for i in range(N_PILLARS):
        z = float(zs[i])
        uc = float(ucs[i])
        x = (uc - CX) * z / F
        ps.append({
            "x": float(x),
            "z": z,
            "w": float(RNG.uniform(0.10, 0.18)),  # 窄柱：保证投影宽 < 走廊间隔
            "h": float(RNG.uniform(0.8, 2.0)),    # 随机高度：杀掉单目大小线索
            "hue": int(hues[i]),
            "uc_target": uc,
        })
    return ps


def hsv_color(hue):
    c = cv2.cvtColor(np.uint8([[[hue, 235, 245]]]), cv2.COLOR_HSV2BGR)[0, 0]
    return int(c[0]), int(c[1]), int(c[2])


def render_eye(pillars, cam_x):
    """真针孔投影 + 画家算法。返回 (H, EW, 3) BGR"""
    img = np.zeros((H, EW, 3), np.uint8)
    # 天空 / 地面
    img[:CY] = (90, 70, 55)
    img[CY:] = (45, 50, 58)
    cv2.line(img, (0, CY), (EW, CY), (70, 80, 92), 1)

    order = sorted(range(len(pillars)), key=lambda i: -pillars[i]["z"])  # 远先画
    for i in order:
        p = pillars[i]
        Z = p["z"]
        if Z <= 0.05:
            continue
        Xl = p["x"] - p["w"] - cam_x
        Xr = p["x"] + p["w"] - cam_x
        ul = int(round(F * Xl / Z + CX))
        ur = int(round(F * Xr / Z + CX))
        vbot = int(round(CY - F * (0.0 - EYE_H) / Z))
        vtop = int(round(CY - F * (p["h"] - EYE_H) / Z))
        if ur <= ul:
            continue
        ul = max(0, min(EW - 1, ul)); ur = max(1, min(EW, ur))
        vtop = max(0, min(H - 1, vtop)); vbot = max(1, min(H, vbot))
        if vbot <= vtop:
            continue
        col = hsv_color(p["hue"])
        cv2.rectangle(img, (ul, vtop), (ur - 1, vbot - 1), col, -1)
    return img


def render_sbs(pillars, base):
    """并排：左半=左眼(-B/2)，右半=右眼(+B/2)"""
    L = render_eye(pillars, -base / 2.0)
    R = render_eye(pillars, +base / 2.0)
    sbs = np.zeros((H, W, 3), np.uint8)
    sbs[:, :EW] = L
    sbs[:, EW:] = R
    return sbs, L, R


def to_fb_bytes(buf):
    bgra = np.zeros((H, W, 4), np.uint8)
    bgra[:, :, 0] = buf[:, :, 0]
    bgra[:, :, 1] = buf[:, :, 1]
    bgra[:, :, 2] = buf[:, :, 2]
    bgra[:, :, 3] = 255
    return bgra.tobytes()


class Display:
    def __init__(self):
        self.w = open("/dev/fb0", "wb", buffering=0)
        self.r = open("/dev/fb0", "rb", buffering=0)

    def show(self, buf):
        self.w.seek(0); self.w.write(to_fb_bytes(buf)); self.w.flush()

    def read(self):
        self.r.seek(0)
        raw = np.frombuffer(self.r.read(FB_BYTES), np.uint8).copy()
        return raw.reshape(H, STRIDE // 4, 4)[:, :W, :3]   # BGRA -> BGR


def measure_centroid(img, hue):
    """真测量：从读回的像素里按颜色找质心。不是查表给的答案。"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lo = np.array([max(0, hue - 6), 150, 120], np.uint8)
    hi = np.array([min(179, hue + 6), 255, 255], np.uint8)
    m = cv2.inRange(hsv, lo, hi)
    ys, xs = np.nonzero(m)
    if len(xs) < 20:
        return None
    return float(xs.mean())


def run_arm(disp, pillars, base, tag):
    sbs, L, R = render_sbs(pillars, base)
    disp.show(sbs)
    got = disp.read()                      # 她真读回
    identical = bool(np.array_equal(got, sbs))

    gotL = got[:, :EW]
    gotR = got[:, EW:]

    rows = []
    for p in pillars:
        uL = measure_centroid(gotL, p["hue"])
        uR = measure_centroid(gotR, p["hue"])
        if uL is None or uR is None:
            continue
        rows.append({"z": p["z"], "d": uL - uR, "uL": uL, "uR": uR})
    return {"tag": tag, "base": base, "identical": identical,
            "L": L, "R": R, "sbs": sbs, "rows": rows}


def analyse(arm):
    rows = arm["rows"]
    if len(rows) < 4:
        return {"n": len(rows), "ok": False, "err": "too few measurable pillars"}
    z = np.array([r["z"] for r in rows])
    d = np.array([r["d"] for r in rows])
    invz = 1.0 / z

    # G1 视差非零
    nonzero = bool(np.all(np.abs(d) > 0.5))

    # G2 过原点线性回归 d = k * (1/z)，物理上 k 应等于 f*B
    k = float(np.dot(invz, d) / np.dot(invz, invz))
    pred = k * invz
    ss_res = float(np.sum((d - pred) ** 2))
    ss_tot = float(np.sum((d - d.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-9 else 0.0

    # G3 由视差反推深度
    est = np.where(np.abs(d) > 0.5, k / np.abs(d), np.nan)
    rel = np.abs(est - z) / z
    rel = rel[~np.isnan(rel)]
    med_rel = float(np.median(rel)) if rel.size else float("nan")

    # 单目对照：只用左图投影像素高度 h_px = F*h/Z，但 h 随机 -> 估不出
    # （柱子高度随机，故单目大小线索无判别力，此处理论上不可恢复，实测留作对照）

    return {"n": int(len(rows)), "ok": True,
            "disparity_min": float(np.min(np.abs(d))),
            "disparity_max": float(np.max(np.abs(d))),
            "G1_nonzero": nonzero,
            "k_fit": k, "k_theory": float(F * arm["base"]),
            "G2_r2": float(r2),
            "G3_med_rel_err": med_rel}


def main():
    disp = Display()
    pillars = make_world()

    out = {}
    arms = [("stereo_B0.34", BASE_DEFAULT), ("control_B0", 0.0)]
    for tag, b in arms:
        arm = run_arm(disp, pillars, b, tag)
        arm["analysis"] = analyse(arm)
        out[tag] = arm
        cv2.imwrite(f"/data/workspace/luoshen-o1/experiments/exp154_vr/{tag}_sbs.png", arm["sbs"])

    st = out["stereo_B0.34"]["analysis"]
    ct = out["control_B0"]["analysis"]

    gates = {
        "G0_framebuffer_identical": bool(out["stereo_B0.34"]["identical"]
                                         and out["control_B0"]["identical"]),
        "G1_disparity_nonzero": bool(st.get("G1_nonzero", False)),
        "G2_d_vs_inverse_z_R2_gt_0.95": bool(st.get("G2_r2", 0) > 0.95),
        "G3_depth_recovery_rel_err_lt_0.10": bool(st.get("G3_med_rel_err", 9) < 0.10),
        "G4_B0_control_dead": bool((not ct.get("G1_nonzero", True))
                                   or ct.get("G2_r2", 1) < 0.5),
    }
    gates["ALL_PASS"] = all(gates.values())

    res = {
        "F_px": float(F), "base": BASE_DEFAULT,
        "stereo": st, "control_B0": ct,
        "gates": gates,
        "pillars": [{"z": p["z"], "h": p["h"], "x": p["x"]} for p in pillars],
    }
    with open("/data/workspace/luoshen-o1/experiments/exp154_vr/result154.json", "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    print(json.dumps({"stereo": st, "control": ct, "gates": gates}, indent=2, ensure_ascii=False))
    return 0 if gates["ALL_PASS"] else 1


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(sys_exit)
