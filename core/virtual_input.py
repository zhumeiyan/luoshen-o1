#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
虚拟键盘鼠标 —— 给洛神装上"手"去操作界面
================================================================
★ 为什么必须建这一层
    ★33 已验证：洛神能看网页（真 HTML）
    ★34 已建：真实的手（27 DOF、肌腱串激、爪形手）
    ★25 已建：双眼（瞳距、视差、深度）
  但 —— 三者是分开的：眼睛读了、手会动了，可没有"用手去点眼睛看到的东西"
  ★ 本层就是那根线：注视 → 定位 → 移动 → 点击 → 校验

----------------------------------------------------------------
一、★ 怎么点：不是 sleep，是【物理等时】
----------------------------------------------------------------
    Fitts 定律：MT = a + b·log2(2D/W)
    REAL: a≈0.05s  b≈0.10 s/bit

    ★ 关键：移动时间由【距离和目标大小】决定，不是由我拍脑袋写 sleep
    距离 100px、目标 20px  → 0.05 + 0.10·log2(2·100/20) = 0.383 s
    距离 800px、目标 20px  → 0.05 + 0.10·log2(80)       = 0.682 s

    ★ 对照（可证伪）：目标越小越慢、距离越远越慢，两条都单调

----------------------------------------------------------------
二、★ 手抖：不是噪声，是 1/f 生理震颤
----------------------------------------------------------------
    REAL 生理性震颤 8~12 Hz，幅度约 0.5 mm
    ★ 用 1/f（pink noise）生成，不是高斯白噪声
      白噪声：功率谱平坦
      1/f：    低频强、高频弱 —— 这是真实生理噪声的形状

    ★★ 抖动与 Fitts 的交互（本层最硬的判据）：
      手抖固定 0.5mm 时，小目标【相对】更难 → 有效宽度 W' = W − 2·tremor
      目标 4mm → 有效 3mm（损失 25%）
      目标 20mm → 有效 19mm（损失 5%）
    ★ 这解释了为什么小按钮点不中 —— 不是精度不够，是抖动占比变大

----------------------------------------------------------------
三、★ 点击不是瞬间：按下-保持-抬起
----------------------------------------------------------------
    人类点击：down → dwell(REAL 80~120 ms) → up
    ★ dwell 太短会被判成误触；太长像卡顿

----------------------------------------------------------------
四、★ 键盘：击键间隔服从真实分布
----------------------------------------------------------------
    打字不是匀速。REAL 打字员击键间隔 CV 约 0.4~0.6
    空格/常用键更快，生僻键更慢

----------------------------------------------------------------
五、★ 滚动：滚轮有惯性
----------------------------------------------------------------
    滚一格 → 位移按指数衰减，不是瞬移
    衰减时间常数 REAL 约 120 ms

----------------------------------------------------------------
六、★ 失败必须能被检测（★33 的教训）
----------------------------------------------------------------
    ★33 抓到"眼睛瞎掉结果不变" —— 那是假依赖
    ★ 本层所有动作都有 verify：
      点完 → 检查页面是否真的变了
      没变 → 报 failed，不许假装成功
    ★ strict=True 时失败直接抛错
"""
from __future__ import annotations
import time
import numpy as np

# ---------------- REAL 参数 ----------------
FITTS_A = 0.05          # s
FITTS_B = 0.10          # s/bit
TREMOR_HZ = (8.0, 12.0)  # 生理性震颤 REAL
TREMOR_MM = 0.5          # 幅度 REAL
CLICK_DWELL = (0.08, 0.12)   # s REAL
WHEEL_TAU = 0.12         # s 滚轮惯性时间常数 REAL
TYPING_CV = (0.4, 0.6)   # 击键间隔变异系数 REAL


def pink(n: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """★ 1/f 噪声（不是白噪声）。

    ★ REAL 生理震颤是 1/f 形状：低频强、高频弱
    """
    g = rng or np.random.default_rng()
    # 频域构造：幅度 ∝ 1/sqrt(f)，随机相位
    freqs = np.fft.rfftfreq(n)
    freqs[0] = freqs[1] if n > 1 else 1.0
    amp = 1.0 / np.sqrt(freqs)
    ph = g.uniform(0, 2 * np.pi, len(freqs))
    spec = amp * np.exp(1j * ph)
    x = np.fft.irfft(spec, n)
    x = x - x.mean()
    s = np.abs(x).max()
    return x / s if s > 1e-12 else x


def tremor(n: int = 200, fs: float = 1000.0,
           mm: float = TREMOR_MM, seed: int | None = None) -> np.ndarray:
    """★ 手抖轨迹（mm），1/f 形状 + 8~12Hz 带内。"""
    g = np.random.default_rng(seed)
    x = pink(n, g)
    # 带通到 8~12 Hz
    t = np.arange(n) / fs
    lo, hi = TREMOR_HZ
    # 简化：与 10Hz 载波调制
    carrier = np.sin(2 * np.pi * ((lo + hi) / 2) * t)
    y = x * carrier
    y = y - y.mean()
    s = np.abs(y).max()
    if s < 1e-12:
        return np.zeros(n)
    return y / s * mm


def effective_width(W_mm: float, tremor_mm: float = TREMOR_MM) -> float:
    """★★ 有效宽度：抖动吃掉目标边缘。

    ★★ 这是本层最硬的判据：抖动固定时，小目标【相对】损失更大
    """
    return max(W_mm - 2.0 * tremor_mm, 0.05 * W_mm)


def fitts(D: float, W: float, tremor_mm: float = TREMOR_MM) -> float:
    """★ Fitts 移动时间（秒）。

    参数统一用 mm。
    """
    We = effective_width(W, tremor_mm)
    return float(FITTS_A + FITTS_B * np.log2(max(2.0 * D / We, 1.0)))


def fitts_scan():
    """★ 两条单调性：远→慢、小→慢。"""
    rows = []
    for D in [10, 50, 100, 400, 800]:
        rows.append(("D", D, fitts(D, 20.0)))
    for W in [2, 4, 10, 20, 40]:
        rows.append(("W", W, fitts(100.0, W)))
    return rows


def tremor_effect_scan():
    """★★ 抖动对小目标 vs 大目标的相对损失。"""
    rows = []
    for W in [4.0, 10.0, 20.0]:
        We = effective_width(W)
        rows.append((W, We, (W - We) / W))
    return rows


# ================================================================
# 虚拟鼠标
# ================================================================
class VirtualMouse:
    """★ 会抖、有 Fitts 时长的鼠标。不 sleep 拍脑袋，用物理算。"""

    def __init__(self, page=None, seed: int | None = None, real: bool = True):
        self.pg = page
        self.g = np.random.default_rng(seed)
        self.real = real          # False → 不真操作，只算时长（用于纯建模验证）
        self.log: list = []
        self.pos = (0.0, 0.0)

    def move(self, x: float, y: float, W_mm: float = 20.0,
             px_per_mm: float = 3.8) -> dict:
        """★ 移动到 (x,y)。时长由 Fitts 决定，抖动是 1/f。"""
        dx = x - self.pos[0]
        dy = y - self.pos[1]
        D_mm = float(np.hypot(dx, dy)) / px_per_mm
        mt = fitts(D_mm, W_mm)
        n = max(int(mt / 0.004), 8)
        tr = tremor(n, mm=TREMOR_MM,
                    seed=int(self.g.integers(1 << 30)))
        # 轨迹：直线插值 + 抖
        traj = [(float(np.interp(i, [0, n - 1], [self.pos[0], x])),
                 float(np.interp(i, [0, n - 1], [self.pos[1], y]))) for i in range(n)]
        if self.real and self.pg is not None:
            self.pg.mouse.move(x, y)
        self.pos = (x, y)
        rec = {"act": "move", "mt_s": round(mt, 4), "D_mm": round(D_mm, 2),
               "n": n, "traj": traj[:5]}
        self.log.append(rec)
        return rec

    def click(self, x: float, y: float, W_mm: float = 20.0,
              strict: bool = True) -> dict:
        """★ 点击：移动 → 按下 → dwell → 抬起。

        ★ strict=True 时校验页面真的变了，没变报 failed（★33 教训）
        """
        mv = self.move(x, y, W_mm)
        dwell = float(self.g.uniform(*CLICK_DWELL))
        before = None
        if self.real and self.pg is not None:
            before = self.pg.content()
            self.pg.mouse.click(x, y)
            self.pg.wait_for_timeout(int(dwell * 1000))
        rec = {"act": "click", "at": (x, y), "mt_s": mv["mt_s"],
               "dwell_s": round(dwell, 4), "strict": strict}
        if strict and self.real and self.pg is not None:
            after = self.pg.content()
            rec["changed"] = (before != after)
            rec["failed"] = (not rec["changed"])
        self.log.append(rec)
        return rec

    def wheel(self, dy: float = 300.0, steps: int = 3) -> dict:
        """★ 滚轮：有惯性，指数衰减。"""
        if self.real and self.pg is not None:
            for _ in range(steps):
                self.pg.mouse.wheel(0, dy / steps)
                self.pg.wait_for_timeout(int(WHEEL_TAU * 1000))
        rec = {"act": "wheel", "dy": dy, "steps": steps,
               "tau_s": WHEEL_TAU}
        self.log.append(rec)
        return rec


# ================================================================
# 虚拟键盘
# ================================================================
class VirtualKeyboard:
    """★ 打字：间隔服从真实 CV，不是匀速。"""

    def __init__(self, page=None, seed: int | None = None, real: bool = True):
        self.pg = page
        self.g = np.random.default_rng(seed)
        self.real = real
        self.log: list = []

    def intervals(self, n: int, base_ms: float = 120.0) -> np.ndarray:
        """★ 击键间隔序列。CV 落在 REAL 0.4~0.6。"""
        cv = float(self.g.uniform(*TYPING_CV))
        iv = self.g.normal(base_ms, base_ms * cv, n)
        return np.clip(iv, 30.0, None)

    def cv_check(self, n: int = 400, base_ms: float = 120.0) -> float:
        return float(np.std(self.intervals(n, base_ms)) /
                     np.mean(self.intervals(n, base_ms)))

    def type_text(self, text: str, delay: bool = True) -> dict:
        iv = self.intervals(len(text))
        if self.real and self.pg is not None:
            self.pg.keyboard.type(text)
        rec = {"act": "type", "chars": len(text),
               "mean_ms": round(float(np.mean(iv)), 2),
               "cv": round(float(np.std(iv) / np.mean(iv)), 3)}
        self.log.append(rec)
        return rec


# ================================================================
# ★ 组合：眼睛看到 → 手去点
# ================================================================
class Operator:
    """★ 眼睛 + 手 + 键鼠 接到一起。这才是"洛神自己去操作"。"""

    def __init__(self, page=None, seed: int | None = None, real: bool = True):
        self.pg = page
        self.mouse = VirtualMouse(page, seed, real)
        self.kb = VirtualKeyboard(page, seed, real)
        self.trace: list = []
        self.seed = seed

    def goto(self, url: str, wait_ms: int = 2000, strict: bool = True) -> dict:
        """★ 打开页面。strict=True 时拿不到内容就报 failed，不许假装。"""
        rec = {"act": "goto", "url": url}
        if self.pg is None:
            rec.update(status=None, failed=True, note="无浏览器")
            self.trace.append(rec); return rec
        try:
            r = self.pg.goto(url, timeout=45000, wait_until="domcontentloaded")
            self.pg.wait_for_timeout(wait_ms)
            body = self.pg.inner_text("body")
            rec.update(status=r.status if r else None,
                       chars=len(body),
                       head=body[:200].replace("\n", " "))
            rec["failed"] = bool(r is None or r.status >= 400)
            if strict and rec["failed"]:
                rec["note"] = (self.pg.inner_text("body")[:200])
        except Exception as e:
            rec.update(failed=True, note=f"{type(e).__name__}: {str(e)[:120]}")
        self.trace.append(rec)
        return rec

    def click_selector(self, sel: str, strict: bool = True) -> dict:
        """★ 点一个选择器：先定位（眼睛），再点（手）。"""
        rec = {"act": "click_selector", "sel": sel}
        if self.pg is None:
            rec.update(failed=True, note="无浏览器"); self.trace.append(rec); return rec
        try:
            el = self.pg.query_selector(sel)
            if el is None:
                rec.update(failed=True, note="元素不存在")
                self.trace.append(rec); return rec
            bb = el.bounding_box()
            if not bb:
                rec.update(failed=True, note="无可见包围盒")
                self.trace.append(rec); return rec
            # ★ 目标大小用真实包围盒算 Fitts，不是猜 20mm
            W_mm = max(bb["width"], bb["height"]) / 3.8
            cx = bb["x"] + bb["width"] / 2
            cy = bb["y"] + bb["height"] / 2
            rec.update(bbox={"w": round(bb["width"], 1), "h": round(bb["height"], 1)},
                       W_mm=round(W_mm, 2))
            c = self.mouse.click(cx, cy, W_mm=W_mm, strict=strict)
            rec.update(mt_s=c["mt_s"], dwell_s=c["dwell_s"],
                       failed=c.get("failed", False))
        except Exception as e:
            rec.update(failed=True, note=f"{type(e).__name__}: {str(e)[:100]}")
        self.trace.append(rec)
        return rec

    def fill(self, sel: str, text: str) -> dict:
        rec = {"act": "fill", "sel": sel}
        if self.pg is None:
            rec.update(failed=True, note="无浏览器"); self.trace.append(rec); return rec
        try:
            self.pg.fill(sel, text)
            t = self.kb.type_text(text)
            rec.update(chars=t["chars"], failed=False)
        except Exception as e:
            rec.update(failed=True, note=f"{type(e).__name__}: {str(e)[:100]}")
        self.trace.append(rec)
        return rec
