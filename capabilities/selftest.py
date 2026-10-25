#!/usr/bin/env python3
"""判定层自检 —— 用"空壳产物"验证判定器真的会 FAIL。

为什么这一节比生成层更重要
--------------------------
一个永远返回 OK 的判定器，比没有判定器更危险：它给出合格证，于是没人
再去查。它失效的方式和 evalguard 要治的病完全同型——跑完、退出 0、打印
一个好看的数字，但是错的。

所以本脚本对每一类产物都造一个**已知坏**的样本，要求判定器必须判 FAIL。
判 PASS 就是判定器坏了，而且这不是警告，是测试失败。

    python3 capabilities/selftest.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

from capabilities import image as cap_img, video as cap_vid, audio as cap_aud
from capabilities import verify
from capabilities.artifact import Artifact, Kind

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "selftest")
os.makedirs(OUT, exist_ok=True)

_rows: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _rows.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def expect(name: str, v, want_ok: bool) -> None:
    """要求判定结果等于 want_ok。判反了就是判定器坏了。"""
    got = bool(v.ok)
    d = ("; ".join(v.reasons) or "无理由") if not want_ok else ""
    check(name, got == want_ok,
          f"want={'OK' if want_ok else 'FAIL'} got={'OK' if got else 'FAIL'} {d}")


def main() -> int:
    print("判定层自检 —— 空壳必须被抓住")
    print("=" * 66)

    # ---------------- 图片 ----------------
    print("\n[图片] 真图应 PASS / 空壳应 FAIL")

    good = cap_img.render({
        "kind": "chart", "name": "st_good", "title": "判定层自检",
        "series": [{"y": [1, 3, 2, 5, 4], "label": "真实数据"}],
        "xlabel": "步", "ylabel": "值",
    }, out_dir=OUT)
    expect("真实折线图 → OK", verify.image(good), True)

    blank = os.path.join(OUT, "st_blank.png")
    Image.new("RGB", (640, 360), (255, 255, 255)).save(blank)
    expect("纯白空图 → FAIL", verify.image(Artifact(Kind.IMAGE, blank)), False)

    solid = os.path.join(OUT, "st_solid.png")
    Image.new("RGB", (640, 360), (30, 30, 30)).save(solid)
    expect("纯色块 → FAIL", verify.image(Artifact(Kind.IMAGE, solid)), False)

    tiny = os.path.join(OUT, "st_tiny.png")
    Image.new("RGB", (8, 8), (255, 255, 255)).save(tiny)
    expect("8x8 过小 → FAIL", verify.image(Artifact(Kind.IMAGE, tiny)), False)

    expect("不存在的文件 → FAIL",
           verify.image(Artifact(Kind.IMAGE, os.path.join(OUT, "nope.png"))), False)

    # ---------------- 视频 ----------------
    print("\n[视频] 有动效应 PASS / 静止与极短应 FAIL")

    frames = []
    for i in range(48):
        im = Image.new("RGB", (320, 180), (255, 255, 255))
        px = im.load()
        for x in range(i * 6, min(320, i * 6 + 40)):
            for y in range(60, 120):
                px[x, y] = (20, 90, 160)
        frames.append(im)
    mov = cap_vid.from_frames(frames, out=os.path.join(OUT, "st_moving.mp4"),
                              fps=24, out_dir=OUT)
    expect("移动色块视频 → OK", verify.video(mov, min_motion=0.0005), True)

    still = cap_vid.from_frames([frames[0]] * 48,
                                out=os.path.join(OUT, "st_still.mp4"),
                                fps=24, out_dir=OUT)
    v = verify.video(still, min_motion=0.0005)
    expect("48 帧全同 → FAIL（静止图冒充视频）", v, False)

    short = cap_vid.from_frames(frames[:3], out=os.path.join(OUT, "st_short.mp4"),
                                fps=24, out_dir=OUT)
    expect("3 帧过短 → FAIL", verify.video(short, min_motion=0.0), False)

    # ---------------- 音频 ----------------
    print("\n[音频] 有声应 PASS / 静音与过短应 FAIL")

    snd = cap_aud.save(cap_aud.melody(["C", "E", "G", "C"], 0.3),
                       "st_melody", out_dir=OUT)
    expect("四音旋律 → OK", verify.audio(snd), True)

    silence = cap_aud.save(np.zeros(int(cap_aud.SR * 1.0)), "st_silence", out_dir=OUT)
    expect("1 秒静音 → FAIL", verify.audio(silence), False)

    tiny_snd = cap_aud.save(cap_aud.tone(440, 0.05), "st_tiny_snd", out_dir=OUT)
    expect("50ms 过短 → FAIL", verify.audio(tiny_snd), False)

    # 反向验证：真削波必须被抓到。
    # 只证明"不误报"是不够的 —— 一个永远 PASS 的判定器也不误报。
    raw = cap_aud.melody(["C", "E", "G"], 0.4)
    clipped = cap_aud.save(np.clip(raw * 4.0, -1.0, 1.0), "st_realclipped", out_dir=OUT)
    expect("真削波（放大 4 倍截断）→ FAIL", verify.audio(clipped), False)

    # 不能静音但很轻的：应 PASS（有声就行，不苛求响度）
    quiet = cap_aud.save(cap_aud.tone(440, 1.0) * 0.05, "st_quiet", out_dir=OUT)
    expect("很轻但非静音 → OK", verify.audio(quiet), True)

    # ---------------- 拒绝糊弄 ----------------
    print("\n[边界] 兑现不了的请求必须拒绝，不许降级糊弄")
    try:
        cap_img.render({"kind": "photo", "name": "x"})
        check("photo 请求被拒绝", False, "居然接受了渲染层做不到的类型")
    except cap_img.UnsupportedImageRequest as e:
        check("photo 请求被拒绝", True, str(e)[:60])

    try:
        cap_vid.from_frames([], out=os.path.join(OUT, "empty.mp4"))
        check("0 帧被拒绝", False, "空视频被允许产出")
    except ValueError:
        check("0 帧被拒绝", True)

    # ---------------- 汇总 ----------------
    passed = sum(1 for _, ok, _ in _rows if ok)
    total = len(_rows)
    print("\n" + "=" * 66)
    print(f"{passed}/{total} 通过")
    if passed < total:
        print("\n失败项（判定器失效，优先修这些）：")
        for n, ok, d in _rows:
            if not ok:
                print(f"  - {n}  {d}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
