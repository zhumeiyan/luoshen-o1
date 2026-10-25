"""判定层。

这是本包与"大模型也能生成"的分界所在。三条硬规则：

  R1 判定只读**产物本身**（像素 / 采样 / 字节），绝不读生成时传入的 spec。
     读 spec 等于让生成层给自己发合格证。
  R2 失败必须指出**具体哪个指标**越界，禁止返回"看起来不太好"。
     没有指标的失败不可复现，也不可修复。
  R3 判定层自身要被自检（selftest.py），否则它就是一个会静默失效的仪表。

每一类产物的"合格"都被拆成可观测指标，且**刻意包含能抓住空壳的检查**：
一张纯白图、一段静音音频、一帧黑屏视频，都必须在对应判定里 FAIL。
"""
from __future__ import annotations

import os

import numpy as np

from .artifact import Artifact, Verdict, verdict
from . import video as _video
from . import audio as _audio


# ---------------------------------------------------------------------------
# 图片
# ---------------------------------------------------------------------------
def image(art: Artifact, min_ink: float = 0.002,
          min_colors: int = 2, min_side: int = 64) -> Verdict:
    """判定一张图是不是真渲染出来了。

    `ink_ratio` 抓的是"全是背景"——纯白图的值接近 0。
    `distinct_colors` 抓的是"渲染失败只剩一个色块"。
    """
    reasons, m = [], {}
    if not art.exists:
        return verdict("image", False, {"exists": False},
                       ["文件不存在: " + art.path])

    from PIL import Image
    try:
        im = Image.open(art.path).convert("RGB")
    except Exception as e:
        return verdict("image", False, {"open": False}, [f"打不开: {e}"])

    w, h = im.size
    a = np.asarray(im).astype(np.int16)
    m.update({"width": w, "height": h, "bytes": art.size})

    if min(w, h) < min_side:
        reasons.append(f"尺寸过小 {w}x{h} < {min_side}")

    # 背景色 = 出现最多的颜色；ink = 偏离背景超过阈值的像素占比
    flat = a.reshape(-1, 3)
    # 量化后找众数，避免 255,255,255 与 254,255,255 被算成两种色
    q = (flat // 16)
    keys, counts = np.unique(q, axis=0, return_counts=True)
    bg = keys[counts.argmax()] * 16
    dist = np.abs(flat - bg).sum(axis=1)
    ink = float((dist > 30).mean())
    m["ink_ratio"] = round(ink, 5)

    ncol = int(len(np.unique(q, axis=0)))
    m["distinct_colors"] = ncol

    if ink < min_ink:
        reasons.append(f"几乎无内容 ink_ratio={ink:.5f} < {min_ink}（可能是纯背景空图）")
    if ncol < min_colors:
        reasons.append(f"颜色数过少 {ncol} < {min_colors}（可能是单色块）")

    art.probed.update(m)
    return verdict("image", not reasons, m, reasons)


# ---------------------------------------------------------------------------
# 视频
# ---------------------------------------------------------------------------
def video(art: Artifact, min_seconds: float = 0.5,
          min_motion: float = 0.004, min_side: int = 64) -> Verdict:
    """判定一段视频是不是真的有画面、且在动。

    两条能抓住空壳的检查：
      - `duration` 抓"压根没编出来"
      - `motion` 抓"编出来了但每帧都一样"（图片轮播的退化形态）
    """
    reasons, m = [], {}
    if not art.exists:
        return verdict("video", False, {"exists": False}, ["文件不存在: " + art.path])

    info = _video.probe(art.path)
    m.update({k: v for k, v in info.items() if v is not None})
    m["bytes"] = art.size

    dur = None
    if info.get("duration"):
        try:
            dur = float(info["duration"])
        except (TypeError, ValueError):
            dur = None
    if dur is None and info.get("frames") and info.get("fps"):
        try:
            num, den = str(info["fps"]).split("/")
            fps = float(num) / float(den) if float(den) else 0.0
            dur = int(info["frames"]) / fps if fps else None
        except Exception:
            dur = None
    if dur is not None:
        m["seconds"] = round(dur, 3)
        if dur < min_seconds:
            reasons.append(f"时长过短 {dur:.3f}s < {min_seconds}s")

    w, h = info.get("width"), info.get("height")
    if w and h and min(int(w), int(h)) < min_side:
        reasons.append(f"分辨率过低 {w}x{h}")

    # 抽帧算帧间差。抽不到必须 FAIL，不能静默放行 ——
    # 一个抓不到"静止视频"的判定器等于没有判定器，而它失效时看起来
    # 和通过一模一样（都是 ok=True）。这是本层最容易坏的地方。
    motion = _frame_motion(art.path, samples=8, duration=dur)
    if motion is None:
        reasons.append("抽帧失败，无法判定画面是否在变化（不猜，判 FAIL）")
    else:
        m["motion"] = round(motion, 5)
        if motion < min_motion:
            reasons.append(
                f"帧间几乎无变化 motion={motion:.5f} < {min_motion}（可能是静止图当视频）")

    art.probed.update(m)
    return verdict("video", not reasons, m, reasons)


def _frame_motion(path: str, samples: int = 8, duration: float | None = None):
    """按视频全长等距抽帧，算平均帧间差。返回 None 表示抽帧失败（不猜）。

    采样间隔必须由时长算出来，不能写死 fps。写死会出这种错：2 秒视频按
    `fps=1/2` 只抽到 1 帧，于是"帧间差"无从计算，判定器静默放行 —— 而
    静止视频恰好是它最该抓住的东西。
    """
    import shutil
    import subprocess
    import tempfile
    exe = shutil.which("ffmpeg")
    if not exe:
        return None
    from PIL import Image
    # 把 samples 帧铺满全长：间隔 = 时长 / 帧数；时长未知就按 1 帧/秒兜底
    if duration and duration > 0:
        fps = max(0.5, samples / float(duration))
    else:
        fps = 1.0
    tmp = tempfile.mkdtemp(prefix="capver_")
    try:
        r = subprocess.run(
            [exe, "-y", "-loglevel", "error", "-i", path,
             "-vf", f"fps={fps:.3f},scale=64:36",
             "-frames:v", str(samples), os.path.join(tmp, "s%02d.png")],
            capture_output=True, text=True, timeout=40)
        files = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
        if len(files) < 2:
            return None
        arrs = []
        for f in files:
            arrs.append(np.asarray(Image.open(os.path.join(tmp, f))
                                   .convert("L"), dtype=np.int16))
        diffs = [float(np.abs(arrs[i + 1] - arrs[i]).mean()) / 255.0
                 for i in range(len(arrs) - 1)]
        return float(np.mean(diffs)) if diffs else None
    except Exception:
        return None
    finally:
        import shutil as sh
        sh.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 音频
# ---------------------------------------------------------------------------
def audio(art: Artifact, min_seconds: float = 0.2,
          min_rms: float = 0.001, max_clip_run: int = 20) -> Verdict:
    """判定一段音频是不是真有声、且没被削波。

    `rms` 抓静音文件（值为 0）。
    `clip_run` 抓削波：看最长的一段连续贴顶采样有多长（平顶平台）。

    这里踩过两个坑，都写下来免得再踩：
      1. 不能用 peak≈1.0 判削波 —— 满幅正弦的峰值本来就是 1.0，那是正常
         响度。早期版本这么写，把每一段正常音频都判成了坏。
      2. 也不能用贴顶占比 —— 满幅正弦的占比实测就有 2%，同样会误判。
    削波真正的特征是平顶**连续成段**：硬截断会留下几十上百个采样精确
    贴边的平台，而正弦每个周期只有孤立的一两个采样接近峰值。
    """
    reasons, m = [], {}
    if not art.exists:
        return verdict("audio", False, {"exists": False}, ["文件不存在: " + art.path])

    if art.ext == "wav":
        info = _audio.probe(art.path)
        if not info:
            return verdict("audio", False, {"open": False}, ["读不出 wav 头"])
        m.update(info)
    else:
        # mp3 用 ffmpeg 转 wav 再读不划算，这里只读时长与码率等基本信息
        import shutil
        import subprocess
        exe = shutil.which("ffprobe")
        if exe:
            try:
                import json as _json
                r = subprocess.run(
                    [exe, "-v", "error", "-show_entries",
                     "format=duration,bit_rate", "-of", "json", art.path],
                    capture_output=True, text=True, timeout=20)
                fm = _json.loads(r.stdout or "{}").get("format", {})
                if fm.get("duration"):
                    m["seconds"] = round(float(fm["duration"]), 3)
                if fm.get("bit_rate"):
                    m["bit_rate"] = int(fm["bit_rate"])
            except Exception:
                pass
        m["bytes"] = art.size
        m["note"] = "非 wav，rms/peak 未测（不猜）"

    sec = m.get("seconds")
    if sec is not None and sec < min_seconds:
        reasons.append(f"时长过短 {sec}s < {min_seconds}s")

    rms = m.get("rms")
    if rms is not None:
        if rms < min_rms:
            reasons.append(f"接近静音 rms={rms} < {min_rms}")

    run = m.get("clip_run")
    if run is not None and run > max_clip_run:
        reasons.append(
            f"最长连续贴顶段 {run} 采样 > {max_clip_run}，波形被截断（削波失真）")

    art.probed.update(m)
    return verdict("audio", not reasons, m, reasons)


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------
def check(art: Artifact, **kw) -> Verdict:
    if art.kind == "image":
        return image(art, **kw)
    if art.kind == "video":
        return video(art, **kw)
    if art.kind == "audio":
        return audio(art, **kw)
    return verdict(art.kind, False, {}, [f"没有 {art.kind} 的判定器（不假装判过）"])
