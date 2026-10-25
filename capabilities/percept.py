"""显形层：把「一个结论」换成「两个数」。

判定层（verify.py）回答的是 PASS / FAIL —— 那是**我替你下了结论**。
本模块回答的是另一件事，也是本包真正要交付的东西：

    实际误差是多少      ← 我测出来的
    你能看见多少        ← 由五官常量算出，不归我定
    藏了多少倍          ← 两者的比

为什么这两个数比一个布尔值重要
------------------------------
第九节（错误美）已经实测过：抖动的实际误差 50.3%，你只感知到 2.4%，
藏了 21 倍。一个 PASS/FAIL 会把这 21 倍完全抹掉 —— 它过了，于是
那 21 倍的误差从来没有被谁看见过。

所以本模块不做判定，只做换算。判定权交回眼睛。

换算用的全部是五官常量（第一节），它们不归我们定、不归大模型定：
    中央凹 1.25° · 视锥密度曲线 · 韦伯比（亮度 7.9% / 长度 2.9% / 时间 8% / 声强 10%）
    瞬时动态范围 3.4 log · 分辨极限 0.5 角分

硬约束（第二十一节）：
    零 LLM · 依赖只有 numpy(+PIL) · 算不了必须出声，不许静默降级
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# 五官常量（第一节，不可改）
# ---------------------------------------------------------------------------
FOVEA_DEG = 1.25          # Curcio 1990, rod-free zone 0.350mm
PEAK_CONE_PER_DEG = 111.0
WEBER = {                  # ΔI/I
    "luminance": 0.079,
    "length": 0.029,
    "time": 0.08,
    "intensity": 0.10,     # 声强
    "chroma": 0.02,        # 色度辨别（近似，Legge 幂律的低端）
}
INSTANT_LOG_RANGE = 3.4    # Ferwerda：同时真能分辨的动态范围
MAX_PPD = 120.0            # 0.5 角分 Nyquist

# 视锥密度相对衰减：文献趋势拟合（非 Curcio 原始数据表）——已如实标注
# 离心角(度): 相对密度
_DENSITY = [
    (0.0, 1.000), (0.5, 0.980), (1.0, 0.900), (2.0, 0.680),
    (4.0, 0.420), (6.0, 0.300), (10.0, 0.180), (15.0, 0.110),
    (20.0, 0.075), (30.0, 0.042), (40.0, 0.028), (60.0, 0.015),
    (90.0, 0.008),
]


def density_rel(theta_deg: np.ndarray) -> np.ndarray:
    """离心角 → 相对视锥密度（0~1）。用于给「哪里看得见」加权。"""
    t = np.abs(np.asarray(theta_deg, dtype=float))
    xs = [p[0] for p in _DENSITY]
    ys = [p[1] for p in _DENSITY]
    return np.interp(t, xs, ys)


def weber_deadzone(x: np.ndarray, k: float) -> np.ndarray:
    """韦伯死区：|ΔI|/I 小于 k 的部分你看不见，剩下的才进入感知。

    这不是四舍五入，是**生理死区**——低于阈的部分不是"小"，是"不存在"。
    """
    x = np.abs(np.asarray(x, dtype=float))
    return np.maximum(0.0, x - k)


# ---------------------------------------------------------------------------
# 图片
# ---------------------------------------------------------------------------
def perceive_image(path: str, view_deg: float = 30.0,
                   dist_mm: float = 300.0) -> dict:
    """一张图：实际偏差 vs 你能看见的偏差。

    `view_deg` 是这块画面在视网膜上张开的视角。手机 30cm 看 6.1 英寸屏
    约 30°（已由设备谱系实测过 P50 Pro: 95 px/度）。

    返回两个数 + 一个比值。不返回 PASS/FAIL。
    """
    from PIL import Image

    out: dict[str, Any] = {"kind": "image", "limits": []}
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]

    # --- 离心角图（度）。画面中心 = 中央凹中心 ---
    # 视角展开：半宽 = view_deg/2（近似，忽略正切畸变，已标注）
    half = view_deg / 2.0
    xs = (np.arange(w) - w / 2.0) / (w / 2.0) * half
    ys = (np.arange(h) - h / 2.0) / (h / 2.0) * half
    TH = np.sqrt(xs[None, :] ** 2 + ys[:, None] ** 2)
    W = density_rel(TH)                       # 哪里看得见

    # --- 实际偏差：相对局部背景的偏离 ---
    # 背景 = 量化后的众数色（与 verify.image 同一算法，保证两处一致）
    flat = a.reshape(-1, 3)
    q = (flat // 16).astype(np.int32)
    keys, counts = np.unique(q, axis=0, return_counts=True)
    bg = keys[counts.argmax()] * 16.0
    lum = a.mean(axis=2)
    bg_lum = float(np.mean(bg))

    # 相对偏差 ΔI/I（亮度域）
    dev = np.abs(lum - bg_lum) / max(bg_lum, 1.0)
    # 归一化到 0..1（按 3.4 log 瞬时范围的低端做参考，饱和即 1）
    dev_n = np.clip(dev / 1.0, 0.0, 1.0)

    actual = float((dev_n * W).sum() / max(W.sum(), 1e-9))

    # --- 你能看见的：过韦伯死区（亮度 7.9%）后再按密度加权 ---
    seen = weber_deadzone(dev_n, WEBER["luminance"])
    perceived = float((seen * W).sum() / max(W.sum(), 1e-9))

    out["actual_error"] = round(actual, 5)
    out["perceived_error"] = round(perceived, 5)
    out["hidden_x"] = round(actual / perceived, 2) if perceived > 1e-9 else None
    out["weber_used"] = WEBER["luminance"]
    out["method"] = "离心角密度加权(Curcio趋势拟合) + 亮度韦伯死区 7.9%"

    # --- 分辨极限：这一屏上，你最多能分多少级 ---
    ppd = w / view_deg
    out["px_per_deg"] = round(ppd, 1)
    out["eye_limit_ppd"] = MAX_PPD
    out["resolution_headroom_x"] = round(ppd / MAX_PPD, 2)
    out["limits"].append(
        "密度曲线是文献趋势拟合，不是 Curcio 原始数据表")
    out["limits"].append(
        "视角按线性展开，未用正切校正；边缘会有几个百分点的偏差")
    return out


# ---------------------------------------------------------------------------
# 音频
# ---------------------------------------------------------------------------
def perceive_audio(path: str) -> dict:
    """一段音频：实际失真 vs 你能听见的失真。

    感知侧用两道过滤：
      1. 听阈（近似等响，按频率加权）—— 听不见的频段不算
      2. 声强韦伯死区 10% —— 低于阈的强度差不存在

    只处理 wav。其他格式如实说"测不了"。
    """
    out: dict[str, Any] = {"kind": "audio", "limits": []}
    try:
        import wave
    except Exception:
        out["limits"].append("wave 模块不可用")
        return out

    import wave as _wave
    try:
        wf = _wave.open(path, "rb")
    except Exception as e:
        out["limits"].append(f"读不出 wav: {e}")
        return out
    with wf:
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        nf = wf.getnframes()
        raw = wf.readframes(nf)
    if sw != 2:
        out["limits"].append(f"仅支持 16bit，当前 {sw*8}bit，未测（不猜）")
        return out

    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)

    out["sample_rate"] = sr
    out["seconds"] = round(len(x) / sr, 3) if sr else None

    # --- 实际侧：削波 + 总谐波失真的粗测 ---
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    clip_ratio = float((np.abs(x) >= 0.999).mean()) if len(x) else 0.0
    # 连续贴顶段（verify.audio 同口径）
    top = (np.abs(x) >= 0.999).astype(np.int8)
    run = 0
    if len(top):
        cur = 0
        for v in top:
            cur = cur + 1 if v else 0
            run = max(run, cur)
    out["actual_clip_ratio"] = round(clip_ratio, 6)
    out["actual_clip_run"] = int(run)
    out["actual_peak"] = round(peak, 4)

    # --- 感知侧：过听阈 + 韦伯死区 ---
    if len(x) < 64:
        out["limits"].append("样本过短，未做频谱分析")
        return out
    n = 1 << int(math.floor(math.log2(min(len(x), 1 << 15))))
    seg = x[:n] * np.hanning(n)
    sp = np.abs(np.fft.rfft(seg)) / (n / 2)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)

    # 听阈近似：低频与极高频都需要更大声才听得见（等响曲线的粗轮廓）
    f = np.maximum(freqs, 20.0)
    thr = (0.0005
           + 0.0008 * (1000.0 / f) ** 1.2
           + 0.0006 * (f / 8000.0) ** 2.0)
    audible = sp > thr
    out["audible_bins"] = int(audible.sum())
    out["total_bins"] = int(len(sp))
    out["audible_fraction"] = round(float(audible.mean()), 4)

    # 强度韦伯死区：能察觉的强度差
    rel = sp / max(sp.max(), 1e-12)
    seen = weber_deadzone(rel, WEBER["intensity"])
    out["actual_dynamic"] = round(float(rel[audible].std() if audible.any() else 0.0), 5)
    out["perceived_dynamic"] = round(float(seen[audible].mean() if audible.any() else 0.0), 5)

    # 削波的感知：连续贴顶段在多长以上才听得出来
    # 粗略：>20 采样（verify 口径）视为可闻失真起点
    out["perceived_clip_run_threshold"] = 20
    out["clip_audible"] = bool(run > 20)
    out["method"] = "听阈近似(等响曲线粗轮廓) + 声强韦伯死区 10%"
    out["limits"].append("听阈用解析近似，非 ISO 226 等响曲线原始表")
    out["limits"].append("THD 未测（需要纯净参照信号，本层只有产物本身）")
    return out


# ---------------------------------------------------------------------------
# 视频
# ---------------------------------------------------------------------------
def perceive_video(path: str, samples: int = 8,
                   view_deg: float = 30.0) -> dict:
    """一段视频：帧间实际变化 vs 你能察觉的变化。

    两道过滤，缺一不可：
      1. 时间韦伯死区 8% —— 变化太小你根本看不见"它在动"
      2. 离心角密度加权 —— 画面边缘的变化权重低
    """
    out: dict[str, Any] = {"kind": "video", "limits": []}
    frames, dur = _sample_frames(path, samples)
    if frames is None or len(frames) < 2:
        out["limits"].append("抽帧失败或不足 2 帧，未测（不猜）")
        return out

    h, w = frames[0].shape
    half = view_deg / 2.0
    xs = (np.arange(w) - w / 2.0) / (w / 2.0) * half
    ys = (np.arange(h) - h / 2.0) / (h / 2.0) * half
    TH = np.sqrt(xs[None, :] ** 2 + ys[:, None] ** 2)
    W = density_rel(TH)

    diffs = [np.abs(frames[i + 1] - frames[i]) for i in range(len(frames) - 1)]
    # 归一化到 0..1
    diffs = [d / 255.0 for d in diffs]

    # 实际：直接加权平均
    actual = float(np.mean([(d * W).sum() / max(W.sum(), 1e-9) for d in diffs]))
    # 感知：过时间韦伯死区
    seen = [weber_deadzone(d, WEBER["time"]) for d in diffs]
    perceived = float(np.mean([(s * W).sum() / max(W.sum(), 1e-9) for s in seen]))

    out["frames_sampled"] = len(frames)
    out["seconds"] = round(dur, 3) if dur else None
    out["actual_motion"] = round(actual, 6)
    out["perceived_motion"] = round(perceived, 6)
    out["hidden_x"] = round(actual / perceived, 2) if perceived > 1e-9 else None
    out["weber_used"] = WEBER["time"]

    # 时间量子：相邻采样间隔 vs 你的 30ms
    if dur and len(frames) > 1:
        gap = dur / max(len(frames) - 1, 1)
        out["sample_gap_ms"] = round(gap * 1000, 1)
        out["quantum_ms"] = 30.0
        out["gap_in_quantums"] = round(gap * 1000 / 30.0, 2)
        if gap * 1000 < 30.0:
            out["limits"].append(
                f"采样间隔 {gap*1000:.1f}ms < 你的顺序阈 30ms —— "
                "这两个采样在你眼里可能是同一件事，motion 会被高估")
    out["method"] = "离心角密度加权 + 时间韦伯死区 8%"
    return out


def _sample_frames(path: str, samples: int = 8):
    """等距抽帧，返回 (灰度数组列表, 时长)。失败返回 (None, None)。不猜。"""
    import os
    import shutil
    import subprocess
    import tempfile
    from PIL import Image

    exe = shutil.which("ffmpeg")
    if not exe:
        return None, None

    dur = None
    fp = shutil.which("ffprobe")
    if fp:
        try:
            import json as _json
            r = subprocess.run(
                [fp, "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", path], capture_output=True, text=True, timeout=20)
            dur = float(_json.loads(r.stdout or "{}").get("format", {}).get("duration", 0)) or None
        except Exception:
            dur = None

    fps = max(0.5, samples / dur) if dur and dur > 0 else 1.0
    tmp = tempfile.mkdtemp(prefix="capper_")
    try:
        subprocess.run(
            [exe, "-y", "-loglevel", "error", "-i", path,
             "-vf", f"fps={fps:.3f},scale=64:36",
             "-frames:v", str(samples), os.path.join(tmp, "s%02d.png")],
            capture_output=True, text=True, timeout=40)
        files = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
        if len(files) < 2:
            return None, dur
        arrs = [np.asarray(Image.open(os.path.join(tmp, f)).convert("L"),
                           dtype=np.float32) for f in files]
        return arrs, dur
    except Exception:
        return None, dur
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------
def perceive(kind: str, path: str, **kw) -> dict:
    """按模态返回「两个数」。不做 PASS/FAIL。

    返回至少含：actual_* / perceived_* / method / limits。
    `limits` 永远给出：哪部分我没算、为什么不算。不许静默。
    """
    if kind == "image":
        return perceive_image(path, **kw)
    if kind == "audio":
        return perceive_audio(path)
    if kind == "video":
        return perceive_video(path, **kw)
    return {"kind": kind, "limits": [f"没有 {kind} 的显形器（不假装算过）"]}


def format_pair(d: dict) -> str:
    """把「两个数」排成人一眼能比的样子。不替你下结论。"""
    if not d:
        return "  （无数据）"
    lines = []
    keys = [k for k in d if k.startswith("actual_")]
    for k in keys:
        a = d[k]
        p = d.get(k.replace("actual_", "perceived_"))
        if p is None:
            continue
        try:
            ratio = f"{float(a)/float(p):.1f}×" if float(p) > 1e-9 else "∞"
        except (TypeError, ValueError):
            ratio = "—"
        name = k[len("actual_"):]
        lines.append(f"  {name:<14} 实际 {fmt(a):>10}   你看见 {fmt(p):>10}   藏 {ratio:>7}")
    for k in ("hidden_x",):
        if k in d and d[k]:
            lines.append(f"  {'—'*40}")
    for k, v in d.items():
        if k.startswith(("actual_", "perceived_")):
            continue
        if k in ("kind", "method", "limits"):
            continue
        lines.append(f"  {k:<28} {fmt(v)}")
    if d.get("method"):
        lines.append(f"  算法: {d['method']}")
    for lim in d.get("limits", []):
        lines.append(f"  ⚠ {lim}")
    return "\n".join(lines)


def fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.5g}"
    if isinstance(v, bool):
        return "是" if v else "否"
    return str(v)
