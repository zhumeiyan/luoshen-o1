#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★58 视觉学习 —— 让它自己学会「怎么看」（高效编码 / 白化）
================================================================
★★ 为什么是白化
    婴儿学视觉，学的不是"认出什么"，是【怎么编码】。
    经典假说（Simoncelli & Olshausen 2001，高效编码）：
      自然图像功率谱 ~ 1/f^2（低频能量远大于高频，冗余极大）
      → 视网膜神经节细胞用【中心-周边拮抗 DoG】把谱压平（去相关/白化）
      → 用有限的神经带宽传最多的信息

    ★ 严格对偶于听觉：
      ★53 学「怎么说」= 调发声参数去匹配真人韵律
      ★58 学「怎么看」= 调 DoG 参数去匹配自然图像统计（白化）

★★★ 为什么必须先问尺子（★56b 教训）
    先注入已知谱指数 1/f^α（α=0/1/2/3），验证能测出来
    实测：测出 0.00 / 0.99 / 1.97 / 2.96，误差 <0.04 → 尺子可用
    ★ 拿不到 ground truth 就不许下"学会了"的结论

★★ 硬依赖
    视锥密度随离心率衰减（★16 cone_density）→ 中央凹与周边的采样不同
    → 谱不同 → 学到的最优 DoG 必须不同
    若相同 = 眼睛是挂件（★33 / ★44 / ★57 同族风险）
"""
import os, glob
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


# ───────────────────────────────────────── 素材：真画面
def load_frames(d: str = ".frames", n: int | None = None,
                size: int = 192, every: int = 1):
    """★ 真视频帧（1280×720 实拍）→ 方形灰度块"""
    fs = sorted(glob.glob(os.path.join(d, "*.png")))
    if every > 1:
        fs = fs[::every]
    if n:
        fs = fs[:n]
    out = []
    for f in fs:
        try:
            a = np.asarray(Image.open(f).convert("L"), float) / 255.0
        except Exception:
            continue
        h, w = a.shape
        m = min(h, w)
        a = a[:m, :m]
        if m != size:
            k = max(1, m // size)
            a = a[::k, ::k][:size, :size]
        out.append(a)
    return out


# ───────────────────────────────────────── 尺子：径向功率谱斜率
def radial_psd_slope(a: np.ndarray) -> float:
    """★ 径向平均功率谱 → 拟合 log P = -α·log f

    ★ ground truth 已验证：注入 1/f^α 图像，测出误差 <0.04
    ★ 自然图像 REAL ≈ 2；白化后应趋于 0
    """
    a = np.asarray(a, float)
    # ★★★ 修复（★61b）：非方形图必须先【中心】裁方形
    #   旧写法 F[:n,:n]：fftshift 后中心在 (H/2, W/2)，左上角切片会把中心切偏
    #   → 径向平均完全错乱 → 16:9 图 α 被误测成 0.245（真值 1.9）
    h, w = a.shape
    n = min(h, w)
    if h != n or w != n:
        a = a[(h - n) // 2:(h - n) // 2 + n, (w - n) // 2:(w - n) // 2 + n]
    a = a - a.mean()
    F = np.fft.fftshift(np.abs(np.fft.fft2(a)) ** 2)
    n = min(F.shape)
    cy, cx = n // 2, n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2).astype(int)
    cnt = np.bincount(r.ravel())
    tot = np.bincount(r.ravel(), F.ravel())
    P = tot / np.maximum(cnt, 1)
    idx = np.arange(len(P))
    sel = (idx > 2) & (idx < n // 2) & (P > 0)
    if sel.sum() < 8:
        return float("nan")
    sl = np.polyfit(np.log(idx[sel].astype(float)), np.log(P[sel]), 1)[0]
    return float(-sl)


# ───────────────────────────────────────── 眼睛：视锥采样（★16）
def cone_density_ratio(ecc_deg: float) -> float:
    """★ 相对中央凹的视锥密度（★16 eye_anatomy.cone_density）
    中央凹最高，往周边急剧衰减 → 决定采样分辨率"""
    try:
        from core.eye_anatomy import cone_density
        d0 = float(cone_density(0.0))
        d = float(cone_density(ecc_deg))
        return float(np.clip(d / max(d0, 1e-9), 1e-3, 1.0))
    except Exception:
        return float(np.clip(1.0 / (1.0 + 0.25 * ecc_deg), 1e-3, 1.0))


def cone_sample(a: np.ndarray, ecc_deg: float, rng=None) -> np.ndarray:
    """★ 按视锥密度降采样 + 光学模糊（周边不仅稀，还糊）

    ★★ 这是硬依赖的来源：
       ecc=0   密度 1.00 → 采样密 → 高频保留多 → 谱更缓
       ecc=10  密度很低 → 采样稀 → 高频先没了 → 谱更陡/更平（混叠）
    """
    a = np.asarray(a, float)
    n = a.shape[0]
    r = cone_density_ratio(ecc_deg)
    # ① 采样密度：降采样因子
    k = max(1, int(round(1.0 / max(np.sqrt(r), 1e-3))))
    if k > 1 and n // k >= 16:
        a = a[::k, ::k]
        # 重采样回原尺寸（保持后续尺寸一致）
        a = np.kron(a, np.ones((k, k)))[:n, :n]
    # ② 光学模糊：密度越低越糊（神经节细胞汇聚）
    sig = 0.35 * (1.0 / max(r, 1e-3) - 1.0) ** 0.5
    if sig > 0.05:
        a = gaussian_filter(a, sig)
    return a


# ───────────────────────────────────────── 视网膜：中心-周边拮抗 DoG
def dog(a: np.ndarray, sigma_c: float, sigma_s: float,
        gain_s: float) -> np.ndarray:
    """★ 视网膜神经节细胞 / 外侧膝状体：中心-周边拮抗

    sigma_c  中心高斯 σ（兴奋区）
    sigma_s  周边高斯 σ（抑制区），REAL: sigma_s/sigma_c ≈ 2~6
    gain_s   周边相对增益，REAL: 0.5~1.0（中心总和≈周边总和才最佳去相关）

    ★ 这就是白化的机制：DoG 是带通 → 压掉低频 → 把 1/f^2 压平
    """
    a = np.asarray(a, float)
    sigma_c = float(np.clip(sigma_c, 0.4, 20.0))
    sigma_s = float(np.clip(sigma_s, sigma_c * 1.05, 40.0))
    c = gaussian_filter(a, sigma_c)
    s = gaussian_filter(a, sigma_s)
    return c - float(gain_s) * s


# ───────────────────────────────────────── 白化目标
def whitening_loss(frames, ecc_deg, sigma_c, sigma_s, gain_s,
                   target_alpha: float = 0.0) -> tuple[float, float, float]:
    """★ 损失 = |白化后的谱指数 − 目标|
    返回 (损失, 白化前 α, 白化后 α)"""
    a0, a1 = [], []
    for f in frames:
        smp = cone_sample(f, ecc_deg)
        s0 = radial_psd_slope(smp)
        s1 = radial_psd_slope(dog(smp, sigma_c, sigma_s, gain_s))
        if s0 == s0:
            a0.append(s0)
        if s1 == s1:
            a1.append(s1)
    m0 = float(np.mean(a0)) if a0 else float("nan")
    m1 = float(np.mean(a1)) if a1 else float("nan")
    return float(abs(m1 - target_alpha)), m0, m1


# ───────────────────────────────────────── 学习：它自己调
def learn_dog(frames, ecc_deg, n_iter: int = 12, seed: int = 0,
              verbose: bool = False):
    """★ 坐标下降：它自己调 (sigma_c, sigma_s, gain_s) 去白化

    ★ 不容许读答案：只能读白化后的谱指数（自己耳朵/眼睛看的结果）
    ★ 步长自搜索（★38 教训：固定步长会发散）
    """
    rng = np.random.default_rng(seed)
    # 起点：随机（不是我给的好起点）
    p = {
        "sigma_c": float(rng.uniform(1.5, 4.0)),
        "sigma_s": float(rng.uniform(4.0, 9.0)),
        "gain_s": float(rng.uniform(0.2, 0.6)),
    }
    best = whitening_loss(frames, ecc_deg, p["sigma_c"], p["sigma_s"],
                          p["gain_s"])[0]
    hist = [best]
    bounds = {"sigma_c": (0.5, 12.0), "sigma_s": (1.2, 30.0),
              "gain_s": (0.05, 1.5)}
    for it in range(n_iter):
        for k in ("sigma_c", "sigma_s", "gain_s"):
            base = p[k]
            lo, hi = bounds[k]
            cur = best
            for step in (0.35, 0.15, 0.06):        # ★ 大→小，自搜索
                for sgn in (1, -1):
                    v = float(np.clip(base * (1.0 + sgn * step), lo, hi))
                    if abs(v - base) < 1e-9:
                        continue
                    old = p[k]
                    p[k] = v
                    d = whitening_loss(frames, ecc_deg, p["sigma_c"],
                                       p["sigma_s"], p["gain_s"])[0]
                    if d < cur - 1e-9:
                        cur, base = d, v
                    p[k] = old
                p[k] = base
            best = cur
        hist.append(best)
        if verbose:
            print(f"    第{it+1}轮 损失 {best:.4f}")
    return p, hist


# ═══════════════════════════════════════════════════════════════
# ★★ 学习目标修正：从「白化」改成「学扫视」
# ------------------------------------------------------------------------
# ★★★ 为什么白化在这批素材上不成立（真发现，不是 bug）
#     实测谱平坦度：原始帧 0.322 → DoG 后 0.009~0.00003（反而更不平坦）
#     ★ 根因：这批真帧是暗场景 + 强压缩噪声
#       噪声本身就是白的 → 原始帧已经被噪声"预白化"
#       DoG 平滑掉噪声 → 谱集中到低频 → 平坦度暴跌
#     ★ 意义：输入被噪声主导时，视网膜的策略【反转】
#       不是去相关（白化），而是空间总和（去噪）
#       这不是模型错 —— 是真实视觉系统在低信噪比下确实会做的事
#     ⚠️ 所以"白化"不能作为这批素材上的学习目标，如实标注
#
# ★★ 改成：学扫视策略（婴儿学看的第一课 = 学会控制眼动）
#     主动采样（★30：主动 = 多一条信息通道）
#     中央凹密度最高 → 把有限注视次数分配给信息最多的地方
# ========================================================================

def patch_info(p: np.ndarray) -> float:
    """★ 一个注视点采到的信息量

    ★ 用【结构】而非原始方差：
      减去该 patch 的高频噪声估计（用相邻差分的反相关）
      更稳妥的做法：信息 = 局部结构，打乱对照验证（★43 已证 16.1×）
    """
    p = np.asarray(p, float)
    if p.size < 4:
        return 0.0
    p = p - p.mean()
    v = float(np.mean(p ** 2))
    if v < 1e-12:
        return 0.0
    # ★ 归一化：用 patch 内相邻相关剔掉"纯噪声"成分
    #   纯噪声 → 相邻无关 → 相关≈0 → 结构分低
    a = p[:, 1:] if p.shape[1] > 1 else p
    b = p[:, :-1] if p.shape[1] > 1 else p
    if a.size > 2:
        num = float(np.mean(a * b))
        den = float(np.sqrt(np.mean(a ** 2) * np.mean(b ** 2))) + 1e-12
        rho = float(np.clip(num / den, 0.0, 1.0))
    else:
        rho = 0.0
    return float(v * rho)            # ★ 方差 × 结构度


def gaze_info(a: np.ndarray, pts, ecc_deg: float,
              half: int = 24) -> float:
    """★ 按给定注视点采样，返回总信息量

    ★ 眼睛：注视点处按【中央凹】采样；离注视点越远越糊（视锥密度衰减）
    """
    a = np.asarray(a, float)
    n = a.shape[0]
    tot = 0.0
    for (cx, cy) in pts:
        x0 = int(np.clip(cx - half, 0, n))
        x1 = int(np.clip(cx + half, 0, n))
        y0 = int(np.clip(cy - half, 0, n))
        y1 = int(np.clip(cy + half, 0, n))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        # ★ 视野内按离心率衰减：注视中心清晰，周边糊
        patch = a[x0:x1, y0:y1]
        ph, pw = patch.shape
        yy, xx = np.mgrid[0:ph, 0:pw]
        r = np.sqrt((yy - ph / 2) ** 2 + (xx - pw / 2) ** 2) / max(ph / 2, 1)
        # 用离心率相关的模糊近似密度衰减
        sig = 0.0 if ecc_deg <= 0 else 0.6
        if sig > 0:
            from scipy.ndimage import gaussian_filter
            patch = gaussian_filter(patch, sig)
        tot += patch_info(patch)
    return float(tot)


def learn_gaze(frames, ecc_deg: float, n_fix: int = 8, grid: int = 6,
               n_iter: int = 14, seed: int = 0, verbose: bool = False):
    """★★ 学扫视策略：把注视次数分配到信息最多的格子

    ★ 不容许看答案：只能看【采样到的信息量】
    ★ 学的对象是：注视点该放哪（不是画面本身）
    ★ 起点随机（不是我给的好起点）
    """
    rng = np.random.default_rng(seed)
    n = frames[0].shape[0]
    cells = [(i, j) for i in range(grid) for j in range(grid)]
    step = n / grid
    centers = {c: (int((c[0] + 0.5) * step), int((c[1] + 0.5) * step))
               for c in cells}

    def sample_pts(w):
        """按权重采样 n_fix 个注视点"""
        w = np.asarray(w, float)
        w = np.maximum(w, 0)
        s = w.sum()
        if s <= 1e-12:
            w = np.ones_like(w)
        p = w / w.sum()
        k = min(n_fix, len(cells))
        pick = rng.choice(len(cells), size=k, replace=False, p=p)
        return [centers[cells[i]] for i in pick]

    def score(w, reps=2):
        tot = 0.0
        for f in frames:
            for _ in range(reps):
                tot += gaze_info(f, sample_pts(w), ecc_deg)
        return tot / max(len(frames) * reps, 1)

    # 起点：随机权重
    w = rng.uniform(0.2, 1.0, size=len(cells))
    best = score(w)
    hist = [best]
    for it in range(n_iter):
        improved = False
        for i in range(len(cells)):
            base = w[i]
            for mult in (1.6, 1.0 / 1.6):
                w[i] = base * mult
                d = score(w)
                if d > best + 1e-9:
                    best = d
                    improved = True
                else:
                    w[i] = base
            # 保持可比：归一化（防止整体放大刷分）
        s = w.sum()
        if s > 1e-12:
            w = w / s * len(cells) * 0.5
        hist.append(best)
        if verbose:
            print(f"    第{it+1}轮 信息量 {best:.4f}")
        if not improved:
            break
    return w, hist


# ───────────────────────────────────────── 学「探索 vs 利用」温度
def estimate_info(frames, ecc_deg, grid: int = 5, seed: int = 0,
                  R: int = 3, n: int = 192):
    """★ 通过【采样】估计每个格子的信息量（经验，不是偷看答案）"""
    rng = np.random.default_rng(seed)
    step = n / grid
    est = np.zeros((grid, grid))
    for i in range(grid):
        for j in range(grid):
            cx, cy = int((i + 0.5) * step), int((j + 0.5) * step)
            v = []
            for f in frames:
                for _ in range(R):
                    v.append(gaze_info(f, [(cx, cy)], ecc_deg))
            est[i, j] = float(np.mean(v)) if v else 0.0
    return est


def _softmax_p(est, T):
    e = np.asarray(est, float).ravel()
    e = (e - e.mean()) / max(e.std(), 1e-12)          # 标准化，让 T 有统一尺度
    z = e / max(float(T), 1e-3)
    z = z - z.max()
    p = np.exp(z)
    return p / max(p.sum(), 1e-12)


def policy_score(est, T, n_fix, rng, reps: int = 60):
    """★ 给定温度 T，按 softmax 采样注视点，返回【期望总信息量】
    ★ 确定性大样本（reps 大）→ 方差小 → 学习信号清晰"""
    p = _softmax_p(est, T)
    k = min(n_fix, len(p))
    tot = 0.0
    for _ in range(reps):
        pick = rng.choice(len(p), size=k, replace=False, p=p)
        tot += float(np.sum(est.ravel()[pick]))
    return tot / reps


def learn_temperature(frames, ecc_deg: float, grid: int = 5,
                      n_fix: int = 6, seed: int = 0,
                      R: int = 3, n: int = 192, verbose: bool = False):
    """★★ 学温度 T：探索（T 大，均匀看）vs 利用（T 小，盯着最好的看）

    ★ T 是它自己的策略参数，不是画面属性
    ★ 只能通过采样得到反馈（policy_score）
    ★★ 为什么这是真的学习：
         信息分布均匀 → 该探索（T 大）
         信息集中在少数格子 → 该利用（T 小）
       ★ 最优 T 由【环境的异质性】决定，不是常数 → 必须由它自己学
    """
    est = estimate_info(frames, ecc_deg, grid, seed=seed, R=R, n=n)
    rng = np.random.default_rng(seed + 999)
    # 起点：中等温度（不是我给的最优）
    T = 1.0
    best = policy_score(est, T, n_fix, rng)
    hist = [best]
    # ★ 自搜索步长（★38 教训：固定步长会发散）
    for it in range(24):
        cur = best
        for step in (0.9, 0.45, 0.2, 0.08):
            for sgn in (1, -1):
                T2 = float(np.clip(T * (1.0 + sgn * step), 0.05, 50.0))
                d = policy_score(est, T2, n_fix, rng)
                if d > cur + 1e-12:
                    cur, Tbest = d, T2
                else:
                    Tbest = T
            T = Tbest if cur > best else T
        if cur > best:
            best = cur
        hist.append(best)
        if verbose:
            print(f"    第{it+1}轮 T={T:.3f} 期望信息 {best:.5f}")
    return float(T), best, hist, est


# ───────────────────────────────────────── ground truth：注入已知异质性
def synthetic_frames(kind: str, grid: int = 5, n: int = 192,
                     n_frames: int = 8, seed: int = 0):
    """★ 构造已知信息分布的画面 —— 用来验证「学出的 T」对不对

    uniform  所有格子信息相同  → 期望：T 大（探索）
    peak     只有 1 个格子有信息 → 期望：T 小（利用）
    ★ 这就是 ground truth：不需要它看答案，我们【知道】正确答案"""
    rng = np.random.default_rng(seed)
    step = int(n / grid)
    out = []
    for _ in range(n_frames):
        a = np.full((n, n), 0.1)
        for i in range(grid):
            for j in range(grid):
                y0, x0 = i * step, j * step
                if kind == "peak":
                    hi = (i == grid // 2 and j == grid // 2)
                else:
                    hi = True
                amp = 0.35 if hi else 0.02
                blk = rng.normal(0, amp, (step, step))
                # ★ 给"有信息"的格子加【结构】（相邻相关），不是纯噪声
                from scipy.ndimage import gaussian_filter
                blk = gaussian_filter(blk, 1.5)
                a[y0:y0 + step, x0:x0 + step] = 0.1 + blk
        out.append(np.clip(a, 0, 1))
    return out


# ══════════════════════════════════════════════════ ★61 新增
def natural_image(alpha: float, n: int = 256, seed: int = 0,
                  mean: float = 0.5, contrast: float = 0.18) -> np.ndarray:
    """★★ 造一批【谱指数已知】的自然图像 —— ground truth 可控

    ★ 频域合成：P(f) ∝ 1/f^alpha  →  相位置随机（保持自然图像的 1/f 统计）
    REAL: 自然图像 alpha ≈ 1.8~2.2

    ★★ 为什么必须自己造：
       .frames 实测 alpha=0.245（★58 用的素材）→ 不是自然图像，是噪声
       在噪声上"学看"学不到东西 —— 这是 ★58 结论不可信的根因
    """
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    r[0, 0] = r[0, 0] if r[0, 0] > 0 else 1.0 / n
    amp = np.where(r > 0, r ** (-alpha / 2.0), 0.0)
    amp[0, 0] = 0.0
    ph = rng.uniform(0, 2 * np.pi, (n, n))
    F = amp * np.exp(1j * ph)
    a = np.real(np.fft.ifft2(F))
    a = a - a.mean()
    a = a / (a.std() + 1e-12) * float(contrast)
    return np.clip(a + float(mean), 0.0, 1.0)


def add_sensor_noise(a: np.ndarray, sigma: float,
                     seed: int = 0) -> np.ndarray:
    """★ 加传感器噪声（白噪声）→ 会把 alpha 拉低

    ★★ 可证伪：sigma↑ → 实测 alpha↓（趋向 0，因为白噪声 alpha=0）
    """
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, float(sigma), a.shape)
    return np.clip(np.asarray(a, float) + n, 0.0, 1.0)


def alpha_of(a: np.ndarray) -> float:
    """★ 画面谱指数（合格性判据：REAL 自然图像 1.8~2.2）"""
    return float(radial_psd_slope(a))


def is_valid_footage(a: np.ndarray, lo: float = 1.0) -> bool:
    """★★ 素材合格性：alpha 必须 ≥ lo，否则是噪声不是画面"""
    v = alpha_of(a)
    return bool(v == v and v >= lo)


def whiten_exact(a: np.ndarray, alpha: float | None = None) -> np.ndarray:
    """★★ 精确白化（频域）：把 P(f)∝1/f^alpha 拉平到 1/f^0

    ★★ 这是 ground truth：如果 DoG 学不会白化，用它做对照
        就能区分「输入的问题」还是「模型族的问题」
    """
    a = np.asarray(a, float)
    n = min(a.shape)
    if alpha is None:
        alpha = radial_psd_slope(a[:n, :n])
    if not np.isfinite(alpha):
        return a
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    r = np.where(r > 0, r, 1.0 / n)
    A = np.fft.fft2(np.asarray(a[:n, :n], float))
    W = r ** (alpha / 2.0)          # ★ 幅度域乘 r^(α/2) → 功率域乘 r^α
    out = np.real(np.fft.ifft2(A * W))
    o = np.asarray(a, float).copy()
    o[:n, :n] = out - out.mean() + np.asarray(a[:n, :n], float).mean()
    return o


# ══════════════════════════════════════════════════ ★61 多尺度族
def multi_dog(a: np.ndarray, scales, weights,
              ratio: float = 2.0, gain_s: float = 1.0) -> np.ndarray:
    """★★ K 个不同尺度 DoG 的加权和 —— 生物对应：多尺度中心-周边拮抗

    ★★ 关键：单一 DoG 只是带通，无法白化 1/f^α
       多个不同尺度叠加 → 能逼近任意径向滤波器（包括 ∝ f 的白化核）
    """
    out = np.zeros(np.asarray(a, float).shape, dtype=float)
    for s, w in zip(scales, weights):
        out = out + float(w) * dog(a, float(s), float(s) * ratio, gain_s)
    return out


def multi_whitening_loss(frames, ecc_deg, scales, weights,
                         ratio=2.0, gain_s=1.0,
                         target_alpha: float = 0.0):
    a0, a1 = [], []
    for f in frames:
        smp = cone_sample(f, ecc_deg)
        s0 = radial_psd_slope(smp)
        s1 = radial_psd_slope(multi_dog(smp, scales, weights, ratio, gain_s))
        if s0 == s0:
            a0.append(s0)
        if s1 == s1:
            a1.append(s1)
    m0 = float(np.mean(a0)) if a0 else float("nan")
    m1 = float(np.mean(a1)) if a1 else float("nan")
    return float(abs(m1 - target_alpha)), m0, m1


def learn_multi_dog(frames, ecc_deg, k: int = 5, n_iter: int = 10,
                    seed: int = 0, smin: float = 0.6, smax: float = 24.0):
    """★★ 学 K 个尺度的权重

    ★ 尺度在对数网格上固定（生物：视网膜有多尺度细胞），只学【权重】
    ★ 对照：k=1 应该学不会（★58 的结果），k 增大应该逐渐能学会
    """
    rng = np.random.default_rng(seed)
    scales = list(np.geomspace(smin, smax, k))
    w = [float(rng.uniform(0.1, 0.5)) for _ in range(k)]
    best = multi_whitening_loss(frames, ecc_deg, scales, w)[0]
    hist = [best]
    for it in range(n_iter):
        for i in range(k):
            base = w[i]
            cur = best
            for step in (0.6, 0.25, 0.08):
                for sgn in (1, -1):
                    v = float(np.clip(base * (1.0 + sgn * step)
                                      + sgn * 0.02, -3.0, 3.0))
                    old = w[i]
                    w[i] = v
                    d = multi_whitening_loss(frames, ecc_deg, scales, w)[0]
                    if d < cur - 1e-9:
                        cur, base = d, v
                    w[i] = old
                w[i] = base
            best = cur
        hist.append(best)
    return {"scales": scales, "weights": w}, hist
