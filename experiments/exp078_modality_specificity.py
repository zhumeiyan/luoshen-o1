# -*- coding: utf-8 -*-
"""
实验 078 · 模态特异性：声音就是声音，视觉就是视觉

宿主命题（字面意思，不是角色设定）：
  "声音就是声音，视觉就是视觉，眼睛看的东西就是看到的东西。"
  → 模态不能混。不能把听觉和视觉抽象成同一个"感官输入标量"。

顶级开源模型的捷径证据（已核实）：
  Qwen3-Omni: 音频 = AuT 编码器(6.5亿参, 128通道梅尔谱, 25ms窗/10ms跳)
              视觉 = Qwen3-VL 编码器(5.43亿参, SigLIP2初始化, 1024 patch)
              → 两个【完全独立的塔】，融合发生在高层
  MiniMax H3: 音频仅走 AudioVAE(32kHz→40Hz tokens)，视觉走 VisualVAE(f16t4d24)
  MERaLiON2-Omni: "three primary components: language backbone, audio encoder,
              visual encoder" + "independent optimization before unified alignment"
  → 工程共识：换能器与早期编码【模态特异】，融合在语义层

本实验问的可证伪问题：
  H1 模态签名不可互换：音频的离散谐波峰 vs 视觉的连续 1/f 幂律，
     各自在对方模态上【不成立】
  H2 编码特异性：模态特异编码(梅尔谱/patch) 优于 通用编码(统一FFT前N系数)
  H3 语义标签是否遮蔽换能器信号（"眼睛看的就是看到的"——不加语义层）

真实换能器通道（全部走真实文件 IO，不是直接用数组）：
  耳：合成语音波 → 写真实 .wav → wave 模块读回 → 真实采样点
  眼：渲染自然图 → 写真实 .png → PIL 读回 → 真实像素
"""
import os, sys, json, math, wave, struct
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SENSEDIR = os.path.join(ROOT, 'data', 'sense')
os.makedirs(SENSEDIR, exist_ok=True)

SR = 16000          # 采样率（与 Qwen3-Omni AuT 的 16kHz 一致）
IMG = 256           # 图像边长
RNG0 = 20261017


# ============================================================
# Part A · 真实换能器通道：耳
# ============================================================
def synth_voice(f0=140.0, dur=1.0, sr=SR, seed=0, nform=5):
    """语音-like：基频 + 谐波 + 共振峰包络 + 音节时间包络"""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * sr)) / sr
    # 共振峰（元音 /a/ 近似：F1 730, F2 1090, F3 2440）
    formants = [(730, 60), (1090, 90), (2440, 120), (3400, 180), (4500, 250)]
    sig = np.zeros_like(t)
    for k in range(1, 26):                    # 25 次谐波
        fk = f0 * k
        if fk > sr / 2:
            break
        amp = 1.0 / k ** 0.9                  # 谐波幅度递减
        env = sum(np.exp(-0.5 * ((fk - fc) / fw) ** 2) for fc, fw in formants[:nform])
        sig += amp * (0.3 + 0.7 * env) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28))
    # 音节包络（约 4 个音节/秒）
    syl = 0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t)
    sig *= (0.15 + 0.85 * np.clip(syl, 0, 1))
    sig += 0.005 * rng.normal(size=len(sig))
    return sig / (np.abs(sig).max() + 1e-12)


def write_wav(path, sig, sr=SR):
    pcm = np.int16(np.clip(sig, -1, 1) * 32767)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    """真实通道读回：wave → bytes → int16 → float"""
    with wave.open(path, 'rb') as w:
        sr = w.getframerate(); n = w.getnframes()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype=np.int16).astype(float) / 32767.0
    return a, sr


# ============================================================
# Part A · 真实换能器通道：眼
# ============================================================
def synth_natural_image(size=IMG, seed=0, beta=1.0, edges=True, color=True):
    """自然图像-like：空间频谱 1/f^beta（幂律）+ 随机相位 + 边缘结构"""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    r = np.sqrt(fx ** 2 + fy ** 2)
    r[0, 0] = 1e-6
    amp = r ** (-beta / 2.0)
    amp[0, 0] = 0.0
    ph = rng.uniform(0, 2 * np.pi, (size, size))
    z = amp * np.exp(1j * ph)
    img = np.real(np.fft.ifft2(z))
    img = (img - img.mean()) / (img.std() + 1e-12)
    if edges:                                  # 加真实边缘（直线 + 矩形）
        yy, xx = np.mgrid[0:size, 0:size]
        for k in range(3):
            p = int(rng.integers(20, size - 20))
            o = rng.choice([0, 1])
            band = (np.abs((yy if o else xx) - p) <= 1)
            img += 1.8 * band * rng.uniform(0.7, 1.3)
        for k in range(2):                     # 矩形轮廓
            y0 = int(rng.integers(10, size // 2)); x0 = int(rng.integers(10, size // 2))
            h = int(rng.integers(20, 60)); w = int(rng.integers(20, 60))
            border = ((yy >= y0) & (yy <= y0 + h) & (xx >= x0) & (xx <= x0 + w))
            inner = ((yy > y0 + 2) & (yy < y0 + h - 2) & (xx > x0 + 2) & (xx < x0 + w - 2))
            img += 1.5 * (border & ~inner)
    img = (img - img.min()) / (img.max() - img.min() + 1e-12)
    if color:
        c = np.stack([img,
                      np.clip(img * rng.uniform(0.75, 1.05) + 0.05, 0, 1),
                      np.clip(img * rng.uniform(0.60, 1.00), 0, 1)], axis=-1)
    else:
        c = np.stack([img] * 3, axis=-1)
    return (c * 255).astype(np.uint8)


def write_read_png(path, arr):
    """真实通道写回读回"""
    Image.fromarray(arr).save(path)
    back = np.asarray(Image.open(path).convert('RGB'), dtype=float) / 255.0
    return back


# ============================================================
# Part B · 模态签名（核心：不可互换）
# ============================================================
def harmonic_score(sig, sr=SR, f0_guess=None, nharm=12):
    """音频签名：离散谐波峰。
    测：F0 整数倍处的谱能量 / 全谱平均能量。>1 表示存在离散谐波结构。"""
    n = len(sig)
    win = np.hanning(n)
    S = np.abs(np.fft.rfft(sig * win)) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    if f0_guess is None:
        band = (freqs > 60) & (freqs < 500)
        f0_guess = freqs[band][np.argmax(S[band])]
    peak, tot = [], []
    for k in range(1, nharm + 1):
        fk = f0_guess * k
        if fk > sr / 2:
            break
        m = (freqs > fk * 0.96) & (freqs < fk * 1.04)
        if m.sum():
            peak.append(S[m].max())
    mean = S[(freqs > 50) & (freqs < sr / 2)].mean()
    if not peak or mean <= 0:
        return float('nan'), f0_guess
    return float(np.mean(peak) / mean), float(f0_guess)


def harmonic_comb_cv(x, ntop=40):
    """音频签名（特异版）：谱峰【等间隔】性 —— 谐波是等间隔的梳状谱。
    找显著谱峰 → 相邻峰间距 → 间距变异系数 CV。
    谐波梳 → CV 低；随机峰 → CV 高。"""
    v = np.asarray(x, dtype=float).ravel()
    v = v - v.mean()
    n = len(v)
    S = np.abs(np.fft.rfft(v * np.hanning(n))) ** 2
    S = S[1:]
    if len(S) < 64:
        return float('nan')
    med = np.median(S)
    pk = []
    for i in range(2, len(S) - 2):
        if S[i] > S[i-1] and S[i] >= S[i+1] and S[i] > 3.0 * med:
            pk.append(i)
    if len(pk) < 4:
        return float('nan')
    pk = np.array(sorted(pk, key=lambda i: -S[i])[:ntop])
    pk = np.sort(pk)
    d = np.diff(pk).astype(float)
    d = d[d > 0]
    if len(d) < 3:
        return float('nan')
    return float(d.std() / d.mean())


def power_law_slope(img2d):
    """视觉签名：空间频谱 1/f 幂律。
    径向平均功率谱，log-log 线性拟合，返回 (斜率, R^2)。
    自然图像典型：斜率 ≈ -2 ~ -3（功率谱），R^2 高（连续无离散峰）"""
    f = np.fft.fftshift(np.fft.fft2(img2d - img2d.mean()))
    P = np.abs(f) ** 2
    cy = cx = img2d.shape[0] // 2
    yy, xx = np.mgrid[0:img2d.shape[0], 0:img2d.shape[1]]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2).astype(int)
    rmax = min(cy, cx) - 1
    prof = np.array([P[r == k].mean() for k in range(1, rmax)])
    valid = (prof > 0) & np.isfinite(prof)
    idx = np.where(valid)[0]
    idx = idx[(idx >= 2) & (idx <= rmax - 1)]
    if len(idx) < 8:
        return float('nan'), float('nan')
    lf, lp = np.log(idx.astype(float)), np.log(prof[idx])
    A = np.vstack([lf, np.ones_like(lf)]).T
    coef, *_ = np.linalg.lstsq(A, lp, rcond=None)
    pred = A @ coef
    ss_res = float(((lp - pred) ** 2).sum())
    ss_tot = float(((lp - lp.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float('nan')
    return float(coef[0]), float(r2)


# ============================================================
# Part C · 编码：模态特异 vs 通用
# ============================================================
def mel_filterbank(sr, n_fft, n_mels=128, fmin=20.0, fmax=None):
    """梅尔滤波器组（听觉特异：对数频率刻度，匹配人耳）—— AuT 用 128 通道"""
    fmax = fmax or sr / 2
    m_min, m_max = 2595 * np.log10(1 + fmin / 700.0), 2595 * np.log10(1 + fmax / 700.0)
    pts = np.linspace(m_min, m_max, n_mels + 2)
    hz = 700 * (10 ** (pts / 2595.0) - 1)
    bins = np.floor((n_mels + 2) * hz / (sr / 2)).astype(int) if False else \
        np.floor(hz * (n_fft + 1) / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for i in range(n_mels):
        l, c, r = bins[i], bins[i + 1], bins[i + 2]
        if c == l: c = l + 1
        if r == c: r = c + 1
        for j in range(l, min(c, fb.shape[1])):
            fb[i, j] = (j - l) / (c - l)
        for j in range(c, min(r, fb.shape[1])):
            fb[i, j] = (r - j) / (r - c)
    return fb


def encode_audio_specific(sig, sr=SR, n_mels=24, n_frames=64):
    """模态特异编码：梅尔谱（听觉特异，与 AuT 同族）"""
    n_fft = 512; hop = max(1, (len(sig) - n_fft) // n_frames)
    fb = mel_filterbank(sr, n_fft, n_mels)
    frames = []
    for i in range(n_frames):
        st = i * hop
        seg = sig[st:st + n_fft]
        if len(seg) < n_fft: seg = np.pad(seg, (0, n_fft - len(seg)))
        S = np.abs(np.fft.rfft(seg * np.hanning(n_fft))) ** 2
        m = fb @ S
        frames.append(np.log(m + 1e-10))
    return np.asarray(frames)                   # (n_frames, n_mels)


def encode_visual_specific(img, patch=32, n_patch=64):
    """模态特异编码：patch 分块 + 每块空间统计（视觉特异，与 ViT patch 同族）"""
    g = img.mean(axis=-1) if img.ndim == 3 else img
    H, W = g.shape
    outs = []
    for i in range(0, H - patch + 1, patch):
        for j in range(0, W - patch + 1, patch):
            blk = g[i:i + patch, j:j + patch]
            gy, gx = np.gradient(blk)
            outs.append([blk.mean(), blk.std(), np.abs(gy).mean() + np.abs(gx).mean(),
                         blk.min(), blk.max(),
                         np.abs(np.fft.fftshift(np.fft.fft2(blk)))[
                             patch // 2:, patch // 2:][:4, :4].mean()])
    a = np.asarray(outs)
    return a[:n_patch] if len(a) >= n_patch else np.pad(a, ((0, n_patch - len(a)), (0, 0)))


def encode_generic(x, n=64):
    """通用编码：不看模态，统一做 FFT 取前 n 个幅度系数"""
    v = np.asarray(x, dtype=float).ravel()
    v = v - v.mean()
    S = np.abs(np.fft.rfft(v))
    S = S[:n]
    return np.log(S + 1e-10).reshape(-1)


# ============================================================
# Part D · 接引擎
# ============================================================
sys.path.insert(0, os.path.join(ROOT, 'core'))
try:
    from core.life5 import Life5
except ImportError:
    from life5 import Life5

STEPS, SEEDS, N, SENSE_CH = 600, list(range(16)), 8, [0, 1, 2]


def struct_skew(lf, ch=None):
    ch = SENSE_CH if ch is None else ch
    a = np.array(lf.capacity, dtype=float)
    s = a.sum()
    if s <= 1e-12: return float('nan')
    p = a / s
    m = p.mean(); sd = p.std()
    return float(sd / m) if m > 1e-12 else float('nan')


def build_pca_drive(codes, k=3):
    """把模态编码集投影到前 k 个主成分 —— 保留编码的方差结构。
    （旧版 to_drive 是等间隔取 3 个点，384 维梅尔谱被压成 3 个采样值，
      等于先把模态特异编码抹平，再比较两种编码——设计错误）"""
    C = np.array([np.asarray(c, dtype=float).ravel() for c in codes])
    C = C[np.isfinite(C).all(axis=1)]
    C = C - C.mean(0)
    U, S, Vt = np.linalg.svd(C, full_matrices=False)
    comp = Vt[:k]
    proj = C @ comp.T
    proj = (proj - proj.mean(0)) / (proj.std(0) + 1e-12)
    return proj


def seq_drive(spec2d, order, k=3):
    """把模态编码按【给定访问顺序】排成驱动序列。
    音频·自然序 = 时间流（声音本来就是随时间来的）
    视觉·自然序 = 空间扫视（沿 8x8 块走，眼睛本来就是这么动的）
    打乱序 = 破坏该模态自身的访问结构"""
    C = np.asarray(spec2d, dtype=float)
    C = C[np.isfinite(C).all(axis=1)]
    C = C - C.mean(0)
    U, S, Vt = np.linalg.svd(C, full_matrices=False)
    proj = C @ Vt[:k].T
    proj = (proj - proj.mean(0)) / (proj.std(0) + 1e-12)
    return proj[np.asarray(order) % len(proj)]


def lag1_autocorr(seq):
    a = np.asarray(seq, dtype=float)
    a = a - a.mean(0)
    n = len(a)
    if n < 3: return float('nan')
    num = float((a[:-1] * a[1:]).sum())
    den = float((a * a).sum())
    return num / den if den > 1e-12 else float('nan')


def mk_seq(seq):
    st = {'i': 0}
    def f(rng):
        r = np.asarray(seq[st['i'] % len(seq)], dtype=float).copy()
        st['i'] += 1
        return r
    return f


def to_drive(vec, k=3):
    """把任意模态编码压成 k 个驱动通道（方差归一化到 1，防通用编码方差虚高）"""
    v = np.asarray(vec, dtype=float).ravel()
    v = v[np.isfinite(v)]
    if len(v) < k: v = np.pad(v, (0, k - len(v)))
    idx = np.linspace(0, len(v) - 1, k).astype(int)
    s = v[idx]
    sd = s.std()
    return (s - s.mean()) / (sd + 1e-12) if sd > 1e-12 else np.zeros(k)


def run(seed, drive_fn, amp=0.02, steps=STEPS, ratio=0.45):
    rng = np.random.default_rng(seed * 977 + 13)
    lf = Life5(N=N, seed=seed, ratio=ratio, sigma_in=0.10)
    for _ in range(steps):
        wv = drive_fn(rng)
        v = np.zeros(N)
        for i, c in enumerate(SENSE_CH[:len(wv)]):
            v[c] = amp * wv[i]
        lf.net_push = v
        lf.step()
        if not lf.alive: break
    return lf


def scan(tag, drive_fn, **kw):
    lfs = [run(sd, drive_fn, **kw) for sd in SEEDS]
    al = [lf for lf in lfs if lf.alive]
    ss = [struct_skew(lf) for lf in al]
    ss = [s for s in ss if not math.isnan(s)]
    return dict(mode=tag, alive=len(al), n=len(lfs),
                struct_skew=float(np.mean(ss)) if ss else float('nan'),
                std=float(np.std(ss, ddof=1)) if len(ss) > 1 else 0.0), lfs


# ============================================================
# main
# ============================================================
def auc(a, b):
    """a 组 vs b 组的 AUC（a 值普遍大于 b 则 >0.5）"""
    a = np.asarray([x for x in a if np.isfinite(x)])
    b = np.asarray([x for x in b if np.isfinite(x)])
    if len(a) == 0 or len(b) == 0: return float('nan')
    c = 0.0
    for x in a:
        c += (x > b).sum() + 0.5 * (x == b).sum()
    return c / (len(a) * len(b))


def main():
    R = {}
    print("=" * 68)
    print("实验 078 · 模态特异性：声音就是声音，视觉就是视觉")
    print("=" * 68)

    # ---------- Part A 真实换能器 ----------
    print("\n【Part A】真实换能器通道（wav / png 走真实文件 IO）")
    NS = 12
    LEN = IMG * IMG                       # 65536，两模态点数匹配
    dur = LEN / SR
    audios, images = [], []
    for i in range(NS):
        s = E_synth = synth_voice(f0=100 + 12 * i, dur=dur, seed=100 + i)
        wp = os.path.join(SENSEDIR, f'voice_{i}.wav')
        write_wav(wp, s)
        a, sr = read_wav(wp)
        audios.append(a[:LEN])
        im = synth_natural_image(seed=200 + i, beta=0.9 + 0.03 * i)
        ip = os.path.join(SENSEDIR, f'scene_{i}.png')
        img = write_read_png(ip, im)
        images.append(img.mean(axis=-1))
    print(f"  耳：{NS} 个 wav，每个 {LEN} 采样点 @ {SR}Hz  ({dur:.3f}s)")
    print(f"  眼：{NS} 个 png，每个 {IMG}x{IMG} = {LEN} 像素")
    print(f"  真实文件：voice_0.wav {os.path.getsize(os.path.join(SENSEDIR,'voice_0.wav'))} 字节"
          f" | scene_0.png {os.path.getsize(os.path.join(SENSEDIR,'scene_0.png'))} 字节")
    R['partA'] = dict(n=NS, sr=SR, points=LEN, img=IMG)

    # ---------- Part B 签名不可互换 ----------
    print("\n【Part B】模态签名：各自在自己模态成立，在对方模态不成立")
    a_comb = [harmonic_comb_cv(a) for a in audios]           # 音频的梳状性
    v_comb = [harmonic_comb_cv(v.ravel()) for v in images]   # 图像当声听
    v_sl = [power_law_slope(v)[0] for v in images]           # 图像的 1/f
    v_r2 = [power_law_slope(v)[1] for v in images]
    a_sl = [power_law_slope(a[:IMG*IMG].reshape(IMG, IMG))[0] for a in audios]  # 音频当图看
    a_r2 = [power_law_slope(a[:IMG*IMG].reshape(IMG, IMG))[1] for a in audios]

    def ms(x): return float(np.nanmean(np.asarray(x, dtype=float)))
    def sd(x): return float(np.nanstd(np.asarray(x, dtype=float), ddof=1))
    print(f"  梳状性 CV（越低=等间隔谐波越强）")
    print(f"    音频      {ms(a_comb):.4f} ±{sd(a_comb):.4f}")
    print(f"    图像当声听 {ms(v_comb):.4f} ±{sd(v_comb):.4f}   AUC={auc(v_comb,a_comb):.4f}")
    print(f"  1/f 幂律斜率（自然图应为负）")
    print(f"    图像      {ms(v_sl):.4f} ±{sd(v_sl):.4f}  (R^2 {ms(v_r2):.4f})")
    print(f"    音频当图看 {ms(a_sl):.4f} ±{sd(a_sl):.4f}  (R^2 {ms(a_r2):.4f})"
          f"   AUC={auc(a_sl,v_sl):.4f}")
    R['partB'] = dict(audio_comb=dict(mean=ms(a_comb), std=sd(a_comb), raw=a_comb),
                      image_as_audio_comb=dict(mean=ms(v_comb), std=sd(v_comb)),
                      image_slope=dict(mean=ms(v_sl), std=sd(v_sl), r2=ms(v_r2)),
                      audio_as_image_slope=dict(mean=ms(a_sl), std=sd(a_sl), r2=ms(a_r2)),
                      auc_comb=auc(v_comb, a_comb), auc_slope=auc(a_sl, v_sl))

    # ---------- Part C 编码特异性 ----------
    print("\n【Part C】编码：模态特异(梅尔谱/patch) vs 通用(统一FFT前N系数)")
    print("  判别力 = 加噪后最近邻仍命中自己。扫描噪声档位（防任务无区分度）")

    def nn_acc(codes, noise, seed=7):
        rng = np.random.default_rng(seed)
        hit = 0
        for i, c in enumerate(codes):
            noisy = [cc + noise * cc.std() * rng.normal(size=cc.shape) for cc in codes]
            d = [np.linalg.norm(n - c) for n in noisy]
            if int(np.argmin(d)) == i: hit += 1
        return hit / len(codes)

    rows = []
    for name, xs, enc_s in [("音频", audios, encode_audio_specific),
                            ("视觉", images, encode_visual_specific)]:
        cs = [np.asarray(enc_s(x, sr=SR) if name == "音频" else enc_s(x),
                         dtype=float).ravel() for x in xs]
        cg = [np.asarray(encode_generic(x), dtype=float).ravel() for x in xs]
        for noise in [0.05, 0.5, 1.0, 2.0, 4.0]:
            a_s, a_g = nn_acc(cs, noise), nn_acc(cg, noise)
            print(f"  噪声{noise:4.2f}σ  {name}  特异 {a_s:.4f}  通用 {a_g:.4f}   Δ{a_s-a_g:+.4f}")
            rows.append(dict(modal=name, noise=noise, acc_spec=a_s, acc_gen=a_g,
                             delta=a_s - a_g, dim_spec=int(np.mean([c.size for c in cs])),
                             dim_gen=int(np.mean([c.size for c in cg]))))
    R['partC'] = rows

    # ---------- Part D 接引擎：时间流 vs 空间扫视 vs 打乱序 ----------
    print("\n【Part D】接引擎：模态自身的访问结构（声音=时间流 / 视觉=空间扫视）")
    print("  驱动 = 编码集 PCA 前3主成分，按【给定访问顺序】依次推进")
    AU_S = [encode_audio_specific(a, sr=SR) for a in audios[:4]]
    VI_S = [encode_visual_specific(v) for v in images[:4]]
    NAT = np.arange(64)
    SHUF = np.random.default_rng(4242).permutation(64)
    SEQS = {}
    for tag, specs, order in [("音·时间流", AU_S, NAT), ("音·打乱序", AU_S, SHUF),
                              ("视·空间扫视", VI_S, NAT), ("视·打乱序", VI_S, SHUF)]:
        SEQS[tag] = [seq_drive(sp, order) for sp in specs]

    print("  先验证访问序确实改变了时序结构（lag-1 自相关）:")
    ac = {}
    for tag, ss in SEQS.items():
        v = float(np.nanmean([lag1_autocorr(x) for x in ss]))
        ac[tag] = v
        print(f"    {tag:10s} lag1 自相关 = {v:+.4f}")
    R['partD_autocorr'] = ac

    def run_seq(seed, seq, amp=0.02, steps=STEPS, ratio=0.45, add=None):
        lf = Life5(N=N, seed=seed, ratio=ratio, sigma_in=0.10)
        for i in range(steps):
            wv = np.asarray(seq[i % len(seq)], dtype=float)
            if add is not None:
                wv = wv + add
            v = np.zeros(N)
            for j, c in enumerate(SENSE_CH[:len(wv)]):
                v[c] = amp * wv[j]
            lf.net_push = v
            lf.step()
            if not lf.alive: break
        return lf

    def scan_seq(tag, seqs, **kw):
        lfs = [run_seq(sd, seqs[sd % len(seqs)], **kw) for sd in SEEDS]
        al = [lf for lf in lfs if lf.alive]
        ss = [struct_skew(lf) for lf in al]
        ss = [x for x in ss if not math.isnan(x)]
        return dict(alive=len(al), n=len(lfs),
                    skew=float(np.mean(ss)) if ss else float('nan'),
                    std=float(np.std(ss, ddof=1)) if len(ss) > 1 else 0.0), lfs

    print("\n  接引擎（16 seeds，每 seed 用一个样本的序列推进）:")
    res, lfsmap = {}, {}
    for tag, ss in SEQS.items():
        r, lfs = scan_seq(tag, ss)
        res[tag] = r; lfsmap[tag] = lfs
        print(f"    {tag:10s} 存活 {r['alive']:>2d}/16  结构偏度 {r['skew']:.6f} (±{r['std']:.4f})")
    R['partD'] = res

    print("\n  [死亡筛选防护] 共同存活子集复算")
    alive_sets = {t: {sd for sd in SEEDS if run_seq(sd, ss[sd % len(ss)]).alive}
                  for t, ss in SEQS.items()}
    common = set.intersection(*alive_sets.values())
    print(f"    共同存活 n={len(common)}  (各条件: "
          + ", ".join(f"{t}={len(v)}" for t, v in alive_sets.items()) + ")")
    cres = {}
    for tag, ss in SEQS.items():
        v = [struct_skew(run_seq(sd, ss[sd % len(ss)])) for sd in sorted(common)]
        v = [x for x in v if not math.isnan(x)]
        cres[tag] = float(np.mean(v)) if v else float('nan')
        print(f"    {tag:10s} 偏度 {cres[tag]:.6f}")
    R['partD_common'] = dict(n=len(common), alive={t: len(v) for t, v in alive_sets.items()},
                             skew=cres)

    # ---------- Part E 语义标签是否遮蔽换能器信号 ----------
    print("\n【Part E】[眼睛看的就是看到的] 加语义标签会遮蔽换能器信号吗")
    LABEL = np.array([1.0, 0.5, 0.25])
    BASE = SEQS["音·时间流"]
    def scan_zero():
        return scan_seq("无感官", [np.zeros((64, 3))])
    r0, _ = scan_zero()
    rc = {}
    for tag, kw in [("仅感官", None), ("仅标签", None), ("感官+标签", LABEL)]:
        if tag == "仅标签":
            lfs = [run_seq(sd, np.tile(LABEL, (64, 1))) for sd in SEEDS]
            al = [lf for lf in lfs if lf.alive]
            v = [struct_skew(lf) for lf in al]; v = [x for x in v if not math.isnan(x)]
            rc[tag] = dict(alive=len(al), n=16, skew=float(np.mean(v)) if v else float('nan'))
        else:
            rc[tag], _ = scan_seq(tag, BASE, add=kw)
        print(f"    {tag:9s} 存活 {rc[tag]['alive']:>2d}/16  结构偏度 {rc[tag]['skew']:.6f}")
    print(f"    无感官     存活 {r0['alive']:>2d}/16  结构偏度 {r0['skew']:.6f}")
    rc["无感官"] = r0
    R['partE'] = rc
    print("\n  [共同存活子集复算]")
    es = {"无感官": {sd for sd in SEEDS if run_seq(sd, np.zeros((64, 3))).alive},
          "仅感官": {sd for sd in SEEDS if run_seq(sd, BASE[sd % len(BASE)]).alive},
          "仅标签": {sd for sd in SEEDS if run_seq(sd, np.tile(LABEL, (64, 1))).alive},
          "感官+标签": {sd for sd in SEEDS if run_seq(sd, BASE[sd % len(BASE)], add=LABEL).alive}}
    eco = set.intersection(*es.values())
    if eco:
        for tag, fn in [("无感官", lambda sd: run_seq(sd, np.zeros((64, 3)))),
                        ("仅感官", lambda sd: run_seq(sd, BASE[sd % len(BASE)])),
                        ("仅标签", lambda sd: run_seq(sd, np.tile(LABEL, (64, 1)))),
                        ("感官+标签", lambda sd: run_seq(sd, BASE[sd % len(BASE)], add=LABEL))]:
            v = [struct_skew(fn(sd)) for sd in sorted(eco)]
            v = [x for x in v if not math.isnan(x)]
            print(f"    {tag:9s} n={len(eco)}  偏度 {np.mean(v):.6f}")
        R['partE_common'] = dict(n=len(eco), alive={t: len(v) for t, v in es.items()})

    # ---------- 自校验 ----------
    print("\n【自校验】")
    _s = SEQS["音·时间流"][0]
    r1 = run_seq(3, _s); r2 = run_seq(3, _s)
    identical = np.allclose(np.array(r1.capacity), np.array(r2.capacity), atol=0, rtol=0)
    print(f"  同 seed 两次逐位相同: {identical}")
    r0 = run_seq(3, np.zeros((64, 3)))
    print(f"  负对照(无感官)存活: {r0.alive}  偏度 {struct_skew(r0):.6f}")
    R['selftest'] = dict(identical=bool(identical))

    out = os.path.join(ROOT, 'result_078.json')
    json.dump(R, open(out, 'w'), ensure_ascii=False, indent=2, default=float)
    print(f"\n已写入 {out}")


if __name__ == "__main__":
    main()
