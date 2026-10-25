"""光电鼠标换能器 v2：补上真实失效机制。
关键修正 1: 传感器右移 d => 图像左移 d，鼠标位移 = -图像位移。
关键修正 2: 玻璃失效不是"没纹理"（方差非零互相关照样成立），
             而是 (a) 透明->返回效率 η 极低, 信号被固定噪声底淹没;
                  (b) 镜面->传感器饱和 clip, 纹理被削平。
"""
import numpy as np

# 表面参数: (返回效率 eta, 镜面眩光 glare, 纹理 std)
SURF = {
    'pad':    dict(eta=0.60, glare=0.00, tex=0.20),   # 鼠标垫（理想）
    'desk':   dict(eta=0.35, glare=0.00, tex=0.27),   # 木桌面
    'paper':  dict(eta=0.50, glare=0.00, tex=0.05),   # 纸：低对比但可用
    'glass':  dict(eta=0.04, glare=0.00, tex=0.02),   # 透明玻璃：光穿透
    'mirror': dict(eta=0.95, glare=0.90, tex=0.15),   # 镜面：眩光饱和
    'white':  dict(eta=0.80, glare=0.30, tex=0.01),   # 光面白板
}

def make_surface(kind, H=160, W=160, seed=0):
    rng = np.random.default_rng(seed)
    p = SURF[kind]
    f = rng.normal(0.5, p['tex'], (H, W))
    f = np.clip(f, 0, 1)
    return f, p

def cmos_frame(surf, p, cy, cx, win, led=1.0, noise_floor=0.01, rng=None):
    """照明 -> 漫反射(eta) -> 镜面眩光叠加 -> 像素积分 -> 饱和 clip -> 噪声底"""
    rng = rng or np.random.default_rng(1)
    H, W = surf.shape
    ys = (np.arange(win) + cy) % H
    xs = (np.arange(win) + cx) % W
    patch = surf[np.ix_(ys, xs)]
    sig = p['eta'] * led * patch              # 返回到传感器的漫反射
    sig = sig + p['glare'] * led              # 镜面眩光（均匀偏置）
    sat = np.mean(sig > 1.0)                  # 饱和像素比例
    frame = np.clip(sig, 0, 1.0)              # ADC 饱和
    frame = frame + rng.normal(0, noise_floor, frame.shape)
    return frame, float(sat)

def estimate_shift(f0, f1):
    win = f0.shape[0]
    a = f0 - f0.mean(); b = f1 - f1.mean()
    denom = np.sqrt((a**2).sum() * (b**2).sum())
    if denom < 1e-12:
        return None, 0.0
    cc = np.real(np.fft.ifft2(np.fft.fft2(a).conj() * np.fft.fft2(b))) / denom
    k = np.unravel_index(np.argmax(cc), cc.shape)
    dy = (k[0] + win//2) % win - win//2
    dx = (k[1] + win//2) % win - win//2
    return (int(dy), int(dx)), float(cc[k])

def measure(kind, true_mouse, win=18, noise_floor=0.01, led=1.0, seed=0):
    """true_mouse: 鼠标真实位移 (dy,dx)。图像位移是它的负值。"""
    surf, p = make_surface(kind, seed=seed)
    rng = np.random.default_rng(seed + 999)
    cy, cx = 60, 60
    f0, s0 = cmos_frame(surf, p, cy, cx, win, led, noise_floor, rng)
    f1, s1 = cmos_frame(surf, p, cy + true_mouse[0], cx + true_mouse[1],
                        win, led, noise_floor, rng)
    img, peak = estimate_shift(f0, f1)
    if img is None:
        return dict(ok=False, err=None, peak=0.0, sat=(s0+s1)/2)
    mouse = (-img[0], -img[1])                # 符号修正
    err = float(np.hypot(mouse[0]-true_mouse[0], mouse[1]-true_mouse[1]))
    return dict(ok=mouse == tuple(true_mouse), err=err, peak=peak,
                est=mouse, sat=(s0+s1)/2)

def batch(kind, true_mouse, n=40, **kw):
    rs = [measure(kind, true_mouse, seed=s, **kw) for s in range(n)]
    oks = [r['ok'] for r in rs]
    errs = [r['err'] for r in rs if r['err'] is not None]
    peaks = [r['peak'] for r in rs]
    sats = [r['sat'] for r in rs]
    return dict(kind=kind, acc=float(np.mean(oks)),
                err=float(np.mean(errs)) if errs else None,
                peak=float(np.mean(peaks)), sat=float(np.mean(sats)))
