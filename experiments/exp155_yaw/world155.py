"""
圆形房间 + 磁纹场 —— 分离「旋转(积分)」与「绝对朝向(磁场)」。

为什么必须是圆形：
  矩形网格的墙角/边长会泄漏绝对朝向 —— 那等于偷偷给了罗盘，
  「无磁场则盲」永远测不出来。圆心出发射线到墙距离恒为 R，
  所以墙高各列完全相同 -> 画面严格旋转对称（预检实测差 0.0）。

为什么磁纹不是「墙上一条带」：
  一条带在朝向大时会移出视野就失效（预检实测 ok=False）。
  真实的磁场是场 —— 候鸟朝哪都能感到。所以做成遍布全墙的周期竖纹，
  相位编码朝向：处处可读，但带周期模糊（模 2pi/N）。

  这正是生物的真实结构：
    半规管(旋转) = 积分，短期准、长期漂；
    磁感受(磁场) = 绝对参考，误差有界，但周期模糊；
    两者互补 —— 积分解模糊，磁场校正漂移。
"""
import numpy as np

W, H = 1024, 768
STRIDE = 4096
FB_BYTES = STRIDE * H

R_WALL = 6.0
FOV_K = 0.66
N_STRIPES = 12                    # 磁纹条数
P = 2.0 * np.pi / N_STRIPES       # 相位周期 ≈ 0.5236 rad ≈ 30°
DUTY = 0.34                       # 亮纹占空比

WALL_BASE = (150, 150, 165)
STRIPE_COL = (60, 210, 220)


def cam_of_col(i):
    return 2.0 * i / W - 1.0


def dir_angle(a, cam):
    return a + np.arctan(FOV_K * cam)


def _wall_rows():
    lh = int(H / R_WALL)
    y0 = max(0, H // 2 - lh // 2)
    y1 = min(H, H // 2 + lh // 2)
    return y0, y1


def render(px, py, pa, magnet=True):
    buf = np.zeros((H, W, 3), dtype=np.uint8)
    buf[: H // 2] = (24, 24, 34)
    buf[H // 2 :] = (46, 40, 36)
    y0, y1 = _wall_rows()
    buf[y0:y1, :] = WALL_BASE
    if not magnet:
        return buf
    cols = np.arange(W)
    theta = dir_angle(pa, cam_of_col(cols))
    ph = np.mod(theta, P)
    m = ph < P * DUTY
    if m.any():
        buf[y0:y1, m] = STRIPE_COL
    return buf


def decode_phase_from_view(buf):
    """从画面读磁纹相位 —— 处处可读，但只给出 a mod P（周期模糊）。
       返回 (ok, [各可见亮纹给出的相位估计])。

       相位偏移必须算对：亮纹定义为 ph < P*DUTY，其中心相位是 P*DUTY/2，
       不是 0。漏掉这一项，解码误差会等于一个整周期（预检实测 max=0.4348≈P）。
    """
    band = (buf[:, :, 1].astype(np.int16) > 180) & (buf[:, :, 2].astype(np.int16) > 180) \
         & (buf[:, :, 0].astype(np.int16) < 120)
    xs = np.where(band.any(axis=0))[0]
    if len(xs) == 0:
        return False, []
    gaps = np.where(np.diff(xs) > 1)[0]
    segs = np.split(xs, gaps + 1)
    ests = []
    for seg in segs:
        if len(seg) < 3:
            continue
        # 触及屏幕边缘的亮纹被裁切，质心系统性偏移 -> 相位读数不可靠。
        # （147 号「远处柱子被边缘裁切导致质心测到残片」同病第三次复发）
        if seg[0] <= 2 or seg[-1] >= W - 3:
            continue
        i_star = float(np.median(seg))
        cam = cam_of_col(i_star)
        a_mod = float(np.mod(P * DUTY / 2.0 - np.arctan(FOV_K * cam), P))
        ests.append(a_mod)
    return (len(ests) > 0), ests


def resolve(a_dead, a_mod):
    """用积分值解磁纹的周期模糊：取与之最近的相位分支。"""
    k = np.round((a_dead - a_mod) / P)
    return a_mod + k * P


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def to_fb_bytes(buf):
    bgra = np.zeros((H, W, 4), dtype=np.uint8)
    bgra[:, :, 0] = buf[:, :, 2]
    bgra[:, :, 1] = buf[:, :, 1]
    bgra[:, :, 2] = buf[:, :, 0]
    bgra[:, :, 3] = 255
    return bgra.tobytes()


def fb_bytes_to_rgb(raw):
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(H, STRIDE // 4, 4)
    bgr = arr[:, :W, :3]
    out = np.empty((H, W, 3), dtype=np.uint8)
    out[:, :, 0] = bgr[:, :, 2]
    out[:, :, 1] = bgr[:, :, 1]
    out[:, :, 2] = bgr[:, :, 0]
    return out
