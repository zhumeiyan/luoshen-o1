"""视频生成层。

诚实定位
--------
这是**帧序列 + ffmpeg 编码**，不是文生视频模型。能稳定产出的是：
数据动图、帧动画、图片转场、带字幕的图集视频。做不到"生成一个场景的连续动作"。

而且有一条必须在代码里说清的：**ffmpeg 是外部依赖**。环境里没有 ffmpeg
时，这里不是静默返回失败，而是抛出 `MissingToolchain`——因为静默失败会
让调用方以为"视频生成了但内容空"，这正是我们要治的那类病。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from .artifact import Artifact, Kind

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


class MissingToolchain(RuntimeError):
    """外部工具缺失。显式抛出，不许静默降级。"""


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise MissingToolchain("环境里没有 ffmpeg，视频层不可用。这是工具链依赖，不是本包自带能力。")
    return exe


def from_frames(frames: list, out: str | None = None, fps: int = 24,
                out_dir: str = DEFAULT_OUT) -> Artifact:
    """把一串 PIL 图（或图片路径）编码成 mp4。

    `frames` 可以是 PIL.Image 对象，也可以是已存在的图片文件路径。
    """
    exe = _ffmpeg()
    os.makedirs(out_dir, exist_ok=True)
    path = out or os.path.join(out_dir, "video.mp4")

    tmpdir = tempfile.mkdtemp(prefix="capvid_")
    try:
        paths = []
        for i, fr in enumerate(frames):
            p = os.path.join(tmpdir, f"f{i:05d}.png")
            if isinstance(fr, str):
                shutil.copyfile(fr, p)
            else:                       # PIL.Image
                fr.save(p)
            paths.append(p)
        if not paths:
            raise ValueError("from_frames 收到 0 帧 —— 空视频不是视频。")

        # libx264 要求宽高都是偶数。880x495 这种奇数高会直接编码失败，
        # 所以统一向下取偶数 —— 差一像素不影响内容，编码失败才真的是交付失败。
        cmd = [exe, "-y", "-loglevel", "error",
               "-framerate", str(fps),
               "-i", os.path.join(tmpdir, "f%05d.png"),
               "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
               "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg 编码失败: {r.stderr.strip()[:400]}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return Artifact(kind=Kind.VIDEO, path=path,
                    meta={"fps": fps, "n_frames": len(frames)})


def animate(spec: dict, out_dir: str = DEFAULT_OUT) -> Artifact:
    """由 spec 直接生成一段数据动图。

    spec: {name, title, series(y随时间变化), fps, seconds}
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fps = int(spec.get("fps", 24))
    seconds = float(spec.get("seconds", 3))
    nframes = max(2, int(fps * seconds))
    series = spec.get("series") or []
    out = os.path.join(out_dir, f"{spec.get('name', 'anim')}.mp4")

    tmpdir = tempfile.mkdtemp(prefix="capanim_")
    try:
        paths = []
        for i in range(nframes):
            t = i / (nframes - 1)
            fig, ax = plt.subplots(figsize=(8, 4.5), dpi=110)
            for s in series:
                y = s["y"]
                cut = max(2, int(len(y) * (0.15 + 0.85 * t)))
                ax.plot(range(cut), y[:cut], lw=2.2,
                        label=s.get("label", ""), color=s.get("color"),
                        marker=s.get("marker"))
            ax.set_title(spec.get("title", ""), fontsize=14)
            ax.set_xlabel(spec.get("xlabel", ""))
            ax.set_ylabel(spec.get("ylabel", ""))
            if any(s.get("label") for s in series):
                ax.legend()
            ax.grid(alpha=0.3)
            ax.set_xlim(0, max(1, max(len(s["y"]) for s in series)))
            if spec.get("ymin") is not None:
                ax.set_ylim(spec.get("ymin"), spec.get("ymax"))
            fig.tight_layout()
            p = os.path.join(tmpdir, f"f{i:05d}.png")
            fig.savefig(p)
            plt.close(fig)
            paths.append(Image.open(p).convert("RGB"))
        return from_frames(paths, out=out, fps=fps, out_dir=out_dir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def slideshow(images: list, seconds_per: float = 2.0, out: str | None = None,
              fps: int = 24, out_dir: str = DEFAULT_OUT) -> Artifact:
    """图片轮播转视频。每张停留 seconds_per 秒。"""
    frames = []
    for p in images:
        frames += [p] * max(1, int(round(seconds_per * fps)))
    return from_frames(frames, out=out, fps=fps, out_dir=out_dir)


def probe(path: str) -> dict:
    """用 ffprobe（若存在）读真实编码信息。读不出来就返回空，不猜。"""
    exe = shutil.which("ffprobe")
    if not exe or not os.path.exists(path):
        return {}
    try:
        r = subprocess.run(
            [exe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,nb_frames,r_frame_rate,codec_name",
             "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True, text=True, timeout=20)
        d = __import__("json").loads(r.stdout or "{}")
        st = (d.get("streams") or [{}])[0]
        fm = d.get("format") or {}
        return {"width": st.get("width"), "height": st.get("height"),
                "codec": st.get("codec_name"), "fps": st.get("r_frame_rate"),
                "frames": st.get("nb_frames"), "duration": fm.get("duration")}
    except Exception:
        return {}
