"""光电鼠标换能器：LED/激光照明 -> CMOS 逐帧采集 -> 互相关求位移。
不抄任何驱动代码，只按物理原理重建：照明、表面反射、像素积分、互相关峰值。"""
import numpy as np

def make_surface(kind, H=128, W=128, rng=None):
    """表面微观形貌/反射率场"""
    rng = rng or np.random.default_rng(0)
    if kind == 'desk':        # 木质桌面：宽带粗糙纹理
        f = rng.random((H, W))
        f = f + 0.5*rng.random((H//4, W//4)).repeat(4, 0).repeat(4, 1)[:H, :W]
    elif kind == 'paper':     # 纸：细密但低对比
        f = rng.normal(0.5, 0.05, (H, W))
    elif kind == 'glass':     # 玻璃：近乎均匀 + 极稀疏缺陷
        f = np.full((H, W), 0.5)
        f += rng.normal(0, 0.004, (H, W))
        for _ in range(6):
            y, x = rng.integers(0, H), rng.integers(0, W)
            f[y, x] += 0.05
    elif kind == 'mirror':    # 镜面：完美均匀，零纹理
        f = np.full((H, W), 0.5)
    elif kind == 'pad':       # 鼠标垫：强高频纹理（理想）
        f = rng.random((H, W)) * 0.6 + 0.2*rng.random((H, W))
    else:
        raise ValueError(kind)
    return np.clip(f, 0, 1)

def cmos_frame(surf, cy, cx, win, led=1.0, dark=0.0, noise=0.0, rng=None):
    """CMOS 采集一帧：照明 -> 反射 -> 像素积分 -> 暗电流 + 读出噪声"""
    rng = rng or np.random.default_rng(1)
    H, W = surf.shape
    ys = (np.arange(win) + cy) % H
    xs = (np.arange(win) + cx) % W
    patch = surf[np.ix_(ys, xs)]
    frame = led * patch + dark
    if noise > 0:
        frame = frame + rng.normal(0, noise, frame.shape)
    return np.clip(frame, 0, 1)

def estimate_shift(f0, f1, max_shift=None):
    """互相关峰值定位：FFT 计算归一化互相关，取峰值偏移（周期性，支持负位移）"""
    win = f0.shape[0]
    a = f0 - f0.mean()
    b = f1 - f1.mean()
    denom = np.sqrt((a**2).sum() * (b**2).sum())
    if denom < 1e-12:
        return None, 0.0      # 零方差 => 互相关无定义（玻璃/镜面）
    F = np.fft.fft2(a)
    G = np.fft.fft2(b)
    cc = np.real(np.fft.ifft2(F.conj() * G)) / denom
    k = np.unravel_index(np.argmax(cc), cc.shape)
    dy = (k[0] + win//2) % win - win//2
    dx = (k[1] + win//2) % win - win//2
    peak = cc[k]
    return (int(dy), int(dx)), float(peak)

def run_trial(kind, true_shift, win=18, noise=0.0, led=1.0, seed=0):
    rng = np.random.default_rng(seed)
    surf = make_surface(kind, rng=np.random.default_rng(seed))
    cy, cx = 40, 40
    f0 = cmos_frame(surf, cy, cx, win, led=led, noise=noise, rng=rng)
    f1 = cmos_frame(surf, cy + true_shift[0], cx + true_shift[1], win,
                    led=led, noise=noise, rng=rng)
    est, peak = estimate_shift(f0, f1)
    if est is None:
        return {'ok': False, 'peak': 0.0, 'err': None}
    err = np.hypot(est[0] - true_shift[0], est[1] - true_shift[1])
    return {'ok': est == tuple(true_shift), 'peak': peak, 'err': float(err),
            'est': est, 'true': tuple(true_shift)}
