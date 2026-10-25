# -*- coding: utf-8 -*-
"""096 主动视觉核心模块 —— 眼球在动，而不是在计算

自然科学依据（文献实测值，非本实验自造）：
  * 中央凹：锥密度在离心率 5° 处降到中央凹的 ~1/10；视力 10° 处降到 10-20%，30° 处 <5%
  * 皮层放大：1° 处 V1 表征约为 40° 处的 ~100 倍
  * 眼动三种：震颤 tremor 40-100Hz、漂移 drift、微跳视 microsaccade <1°，1-2 次/秒（另有 2-3Hz 报告）
  * 扫视 saccade：3-4 次/秒，持续 30-120ms，扫视期间视觉被抑制
  * 视网膜稳定（Riggs 1953 / Ditchburn & Ginsborg 1952）：图像完全固定在视网膜上 → 数秒内消失
    → 不动的眼睛是瞎的
  * 微眼动使实际视力比单纯按锥密度计算的理论值高 ~18%（波恩大学）

本模块把以上做成可测的东西：
  1. foveate()  中央凹渲染：中心清晰、周边模糊（分辨率随离心率下降）
  2. adapt()    适应：retinal slip = 0 → 感知衰减到 0
  3. 眼动策略：stabilized / tremor / drift / microsaccade / saccade / oracle(计算式)
"""
import os, subprocess, tempfile
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 768
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
DT = 0.1                      # 1 拍 = 100 ms
SIGMA_TABLE = [0.0, 0.8, 1.6, 3.0, 6.0, 12.0, 24.0, 48.0]   # 预计算模糊金字塔


# ---------------------------------------------------------------- 世界
def make_world(seed, n_digits=20, size=(W, H)):
    """白底黑字，随机撒 n_digits 个两位数字，返回 (灰度图, 真值表)"""
    rng = np.random.default_rng(seed)
    img = Image.new('L', size, 255)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(FONT_PATH, 40)
    except Exception:
        f = ImageFont.load_default()
    truth = []
    placed = []
    tries = 0
    while len(truth) < n_digits and tries < 600:
        tries += 1
        x = int(rng.integers(60, size[0] - 130))
        y = int(rng.integers(40, size[1] - 80))
        if any(abs(x - px) < 110 and abs(y - py) < 70 for px, py in placed):
            continue
        placed.append((x, y))
        v = int(rng.integers(10, 100))
        truth.append(dict(x=x, y=y, v=v))
        d.text((x, y), str(v), fill=0, font=f)
    return np.array(img, dtype=np.uint8), truth


# ---------------------------------------------------------------- 中央凹渲染
class Fovea:
    """分辨率随离心率下降的视网膜。预计算模糊金字塔，每拍只做加权混合。"""

    def __init__(self, img, e0=45.0, n_rings=12):
        self.img = img.astype(np.float32)
        self.e0 = e0
        # 预计算模糊金字塔
        self.pyr = [self.img] + [cv2.GaussianBlur(self.img, (0, 0), s)
                                 for s in SIGMA_TABLE[1:]]
        self.sig = np.array(SIGMA_TABLE)
        h, w = img.shape
        self.rings = np.linspace(0, max(h, w), n_rings + 1)

    def render(self, fx, fy, zoom=1.0, roll=0.0):
        """zoom>1 = 凑近看（中央凹变大，同样离心率下更清晰）"""
        h, w = self.img.shape
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dx, dy = xx - fx, yy - fy
        if roll:
            c, s = np.cos(roll), np.sin(roll)
            dx, dy = dx * c - dy * s, dx * s + dy * c
        r = np.hypot(dx, dy) / zoom
        # 每个环带应达到的模糊量：sigma 随离心率线性增（模拟视力随离心率下降）
        acc = np.zeros_like(self.img)
        wsum = np.zeros_like(self.img)
        for i in range(len(self.rings) - 1):
            r0, r1 = self.rings[i], self.rings[i + 1]
            rm = 0.5 * (r0 + r1)
            tgt = float(np.clip(rm / self.e0, 0.0, self.sig.max()))
            # 找最接近的预计算层（避免每拍重算高斯）
            k = int(np.argmin(np.abs(self.sig - tgt)))
            # 梯形权重：环带中心为 1，边缘羽化
            half = 0.5 * (r1 - r0)
            m = 1.0 - np.clip((np.abs(r - rm) - half * 0.2) / (half * 0.8 + 1e-6), 0, 1)
            acc += self.pyr[k] * m
            wsum += m
        out = acc / np.maximum(wsum, 1e-6)
        return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- 适应（不动就瞎）
class Retina:
    """感受器对恒定输入快速适应。retinal slip 刷新它。文献：完全稳定 → 数秒消失。"""

    def __init__(self, shape, tau_up=0.06, tau_dn=0.55, gain=6.0):
        self.a = np.zeros(shape, dtype=np.float32)   # 0=新鲜 1=完全适应
        self.prev = None
        self.tau_up = tau_up      # 无 slip 时适应上升速率
        self.tau_dn = tau_dn      # slip 刷新速率
        self.gain = gain

    def step(self, frame):
        f = frame.astype(np.float32)
        if self.prev is None:
            slip = np.ones_like(f)
        else:
            slip = np.abs(f - self.prev) / 255.0
        s = np.clip(slip * self.gain, 0.0, 1.0)
        self.a = np.clip(self.a + (1 - self.a) * self.tau_up * (1 - s)
                         - self.a * self.tau_dn * s, 0.0, 1.0)
        self.prev = f
        vis = np.clip(f * (1.0 - self.a), 0, 255).astype(np.uint8)
        return vis, float(self.a.mean())


# ---------------------------------------------------------------- 眼动策略
def policy_positions(mode, steps, rng, img_shape, truth=None, cur=(W // 2, H // 2)):
    """返回每拍的注视点序列。oracle 是唯一'需要计算'的策略。"""
    h, w = img_shape
    cx, cy = cur
    pos = []
    fx, fy = float(cx), float(cy)

    if mode == 'stabilized':                       # 完全不动（视网膜稳定）
        for _ in range(steps):
            pos.append((fx, fy))

    elif mode == 'tremor':                         # 震颤 40-100Hz：每拍极小幅
        for _ in range(steps):
            pos.append((fx + rng.normal(0, 0.8), fy + rng.normal(0, 0.8)))

    elif mode == 'drift':                          # 漂移：随机游走
        for _ in range(steps):
            fx += rng.normal(0, 1.6); fy += rng.normal(0, 1.6)
            fx = np.clip(fx, 20, w - 20); fy = np.clip(fy, 20, h - 20)
            pos.append((fx, fy))

    elif mode == 'microsaccade':                   # 微跳视 <1°，约 2-3 次/秒
        # 1024px 按 60° 视野估 → 1° ≈ 17px，故 <1° 取 6-16px
        for t in range(steps):
            if t % 4 == 3:
                ang = rng.uniform(0, 2 * np.pi); amp = rng.uniform(6, 16)
                fx += amp * np.cos(ang); fy += amp * np.sin(ang)
                fx = np.clip(fx, 20, w - 20); fy = np.clip(fy, 20, h - 20)
            pos.append((fx, fy))

    elif mode == 'saccade':                        # 扫视 3-4 次/秒，大跳，纯随机（不计算）
        for t in range(steps):
            if t % 3 == 2:
                fx = rng.uniform(40, w - 40); fy = rng.uniform(40, h - 40)
            pos.append((fx, fy))

    elif mode == 'oracle':                         # 计算式：扫全图找信息量最大的块
        # 代价：先做一次全图低分辨率扫描，算每块局部方差（边缘/纹理密度）
        small = cv2.resize(_img_cache['img'], (64, 48)).astype(np.float32)
        lap = cv2.Laplacian(small, cv2.CV_32F)
        blocks = []
        bs = 16
        for by in range(0, 48, bs):
            for bx in range(0, 64, bs):
                blocks.append((float(np.abs(lap[by:by + bs, bx:by + bs]).mean()),
                               bx * w / 64.0 + bs * w / 128.0,
                               by * h / 48.0 + bs * h / 96.0))
        blocks.sort(reverse=True)
        targets = [(b[1], b[2]) for b in blocks[:steps // 3 + 1]]
        ti = 0
        for t in range(steps):
            if t % 3 == 2:
                fx, fy = targets[ti % len(targets)]; ti += 1
            pos.append((fx, fy))

    elif mode == 'cheat':                          # 上界：直接依次看真值位置
        tg = [(t['x'], t['y']) for t in (truth or [])] or [(w / 2, h / 2)]
        ti = 0
        for t in range(steps):
            if t % 3 == 2:
                fx, fy = tg[ti % len(tg)]
                fx += 30; fy += 18               # 数字中心
                ti += 1
            pos.append((fx, fy))
    else:
        raise ValueError(mode)
    return pos


_img_cache = {}


def set_world(img):
    _img_cache['img'] = img


# ---------------------------------------------------------------- OCR 硬指标
def ocr_digits(img):
    """返回图中读到的两位数字集合"""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        p = f.name
    Image.fromarray(img).save(p)
    try:
        out = subprocess.run(
            ['tesseract', p, 'stdout', '--psm', '11', '-l', 'eng',
             '-c', 'tessedit_char_whitelist=0123456789'],
            capture_output=True, text=True, timeout=30).stdout
    except Exception:
        out = ''
    finally:
        os.unlink(p)
    return set(w for w in out.split() if len(w) == 2)


def run_trial(img, truth, mode, steps=60, seed=0, zoom=1.0, roll=0.0):
    """跑一次眼动试验，返回：瞬时可见量、累积看见量、OCR 读对的数字数"""
    rng = np.random.default_rng(seed)
    set_world(img)
    fov = Fovea(img)
    ret = Retina(img.shape)
    pos = policy_positions(mode, steps, rng, img.shape, truth=truth)
    mem = np.zeros_like(img)
    last_vis = None
    a_last = 0.0
    for t, (fx, fy) in enumerate(pos):
        frame = fov.render(fx, fy, zoom=zoom, roll=roll)
        vis, a = ret.step(frame)
        mem = np.maximum(mem, vis)          # 扫视整合：看见过就记住
        last_vis = vis
        a_last = a
    truth_set = set(str(t['v']) for t in truth)
    read_now = ocr_digits(last_vis) & truth_set
    read_mem = ocr_digits(mem) & truth_set
    # 可见信息量：用"清晰像素占比"做客观度量（适应后变白 → 信息归零）
    info_now = float((last_vis < 200).mean())
    info_mem = float((mem < 200).mean())
    return dict(mode=mode, seed=seed,
                read_now=len(read_now), read_mem=len(read_mem),
                info_now=info_now, info_mem=info_mem,
                adapt=float(a_last), n_truth=len(truth_set))
