"""音频生成层。

诚实定位
--------
这是**波形合成**，不是神经 TTS。能稳定产出：提示音、节拍、扫频、由音高
序列拼出的旋律/节奏。做不到"读出一段中文人声"——那需要声学模型和音库，
环境里没有，就不假装能。

`say()` 刻意不伪装成语音合成：它按音节数生成一串可辨识的音高包络，
让"这段话有多长、重音在哪"可听，但不声称是说话。命名和文档都不许含
TTS/语音合成字样——含了就是在骗调用方。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import wave

import numpy as np

from .artifact import Artifact, Kind

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
SR = 22050


def _write_wav(path: str, data: np.ndarray, sr: int = SR) -> None:
    """16-bit PCM 单声道。超幅先归一，避免削波失真。"""
    data = np.asarray(data, dtype=float)
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    if peak > 1.0:
        data = data / peak
    if peak == 0.0:
        data = data
    pcm = (np.clip(data, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def _env(n: int, attack: float = 0.01, release: float = 0.25) -> np.ndarray:
    """ADSR 的简化版：起振 + 衰减。没有包络的音是"咔哒"声不是乐音。"""
    a = max(1, int(n * attack))
    r = max(1, int(n * release))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] = np.linspace(1, 0, r)
    return e


def tone(freq: float = 440.0, seconds: float = 1.0, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    return np.sin(2 * np.pi * freq * t) * _env(len(t))


def beep(seconds: float = 0.15, freq: float = 880.0, sr: int = SR) -> np.ndarray:
    return tone(freq, seconds, sr)


def sweep(f0: float = 200.0, f1: float = 2000.0, seconds: float = 2.0,
          sr: int = SR) -> np.ndarray:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    f = np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / sr) * _env(len(t))


def melody(notes, seconds_per_note: float = 0.35, sr: int = SR) -> np.ndarray:
    """按音高序列拼旋律。`notes` 为频率(Hz)或音名，None 表示休止。"""
    table = {"C": 261.63, "D": 293.66, "E": 329.63, "F": 349.23,
             "G": 392.00, "A": 440.00, "B": 493.88}
    out = []
    for n in notes:
        if n is None:
            out.append(np.zeros(int(sr * seconds_per_note)))
            continue
        f = float(table.get(str(n).upper().rstrip("0123456789"), n)) \
            if isinstance(n, str) else float(n)
        out.append(tone(f, seconds_per_note, sr))
    return np.concatenate(out) if out else np.zeros(1)


def say(text: str, seconds_per_syllable: float = 0.16, sr: int = SR) -> np.ndarray:
    """把文本按长度映射成一串可听的音高轮廓。

    这不是语音合成 —— 它不发出人声，也不试图让人听懂词。它的用途是让
    "这段内容有多长、节奏如何"变得可听（例如做视频配音轨的长度参照）。
    需要真人声请用宿主侧的 TTS，不要在本文档里找。
    """
    n = max(1, len([c for c in text if c.strip()]))
    base = 220.0
    # 用字符码做确定性音高起伏：同一段文本每次产出完全一样，可复现
    seq = [base * (1 + 0.06 * ((ord(c) % 7) - 3)) for c in text if c.strip()]
    return melody(seq, seconds_per_syllable, sr)


def save(data: np.ndarray, name: str, out_dir: str = DEFAULT_OUT,
         to_mp3: bool = False) -> Artifact:
    os.makedirs(out_dir, exist_ok=True)
    wav = os.path.join(out_dir, f"{name}.wav")
    _write_wav(wav, data)
    path = wav
    if to_mp3:
        exe = shutil.which("ffmpeg")
        if not exe:
            # 不静默降级成 wav 还说"给了 mp3"——返回 wav 并在 meta 里说明
            return Artifact(kind=Kind.AUDIO, path=wav,
                            meta={"format": "wav", "mp3_requested": True,
                                  "note": "无 ffmpeg，未能转 mp3，实际交付 wav"})
        mp3 = os.path.join(out_dir, f"{name}.mp3")
        r = subprocess.run([exe, "-y", "-loglevel", "error", "-i", wav,
                            "-codec:a", "libmp3lame", "-q:a", "4", mp3],
                           capture_output=True, text=True)
        if r.returncode == 0:
            path = mp3
            os.remove(wav)
    fmt = os.path.splitext(path)[1].lstrip(".")
    return Artifact(kind=Kind.AUDIO, path=path, meta={"format": fmt})


def probe(path: str) -> dict:
    """读 wav 头里的真实信息。不读生成时的参数。"""
    try:
        with wave.open(path, "rb") as w:
            n = w.getnframes()
            sr = w.getframerate()
            raw = w.readframes(min(n, sr * 10))
    except Exception:
        return {}
    a = np.frombuffer(raw, dtype="<i2").astype(float) / 32768.0
    rms = float(np.sqrt(np.mean(a ** 2))) if a.size else 0.0
    # 削波的判据是"有多少采样点贴在满幅边界上"（平顶），不是"峰值到没到 1"。
    # 一个满幅正弦的峰值本来就是 1.0，那完全正常；只有大量采样点同时贴边
    # 才说明波形被截断了。用峰值判削波会把所有正常响的音频误判为失真。
    clip = float((np.abs(a) >= 0.999).mean()) if a.size else 0.0
    # 削波与"只是很响"的区别在于平顶是否**连续成段**：
    #   满幅正弦 —— 每个周期只有孤立的几个采样接近 ±1，段长 1~3。
    #   削波     —— 波形被硬截断，出现几十上百个采样连续精确贴顶的平台。
    # 所以判据取"最长连续贴顶段"，而不是贴顶占比。后者会把每首响的曲子
    # 都判成失真（实测满幅正弦的占比就有 2%）。
    hit = (np.abs(a) >= 0.999).astype(np.int8)
    run = best = 0
    for v in hit:
        run = run + 1 if v else 0
        best = max(best, run)
    return {"sample_rate": sr, "channels": 1, "frames": n,
            "seconds": round(n / sr, 3) if sr else 0,
            "rms": round(rms, 5),
            "peak": round(float(np.max(np.abs(a))) if a.size else 0.0, 5),
            "clip_ratio": round(clip, 6),
            "clip_run": int(best)}
