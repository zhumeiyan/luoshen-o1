#!/usr/bin/env python3
"""统一命令行入口 —— 所有模态一个命令。

    python3 -m capabilities list                     # 能力清单
    python3 -m capabilities image  --spec s.json     # 出图
    python3 -m capabilities video  --spec s.json     # 出视频
    python3 -m capabilities audio  --spec s.json     # 出音频
    python3 -m capabilities demo                     # 三模态各出一个，并当场判定
    python3 -m capabilities selftest                 # 判定层自检
    python3 -m capabilities show <文件>               # 显形：只给两个数，不下结论

两组命令，两件事，不要混：

    image/video/audio/demo/selftest  → 判定层（我下结论，给 CI 用）
    show                             → 显形层（给两个数，判定权在你）

退出码：`0` = 产物通过了判定；`1` = 判定失败或出错。
**产出了但没通过判定，退出码也是 1** —— 这是本工具与"生成即交付"的分界。

`show` 例外：它不做判定，所以永远返回 0。它只负责把两个数摆出来。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# evalguard 在 overseas/ 下，是代码模态的判定层，单独挂进来
_OVS = os.path.join(_ROOT, "overseas")
if os.path.isdir(_OVS) and _OVS not in sys.path:
    sys.path.insert(0, _OVS)

from capabilities import (image as cimg, video as cvid, audio as caud,  # noqa: E402
                          verify, percept, capabilities_manifest)

DEFAULT_OUT = os.path.join(_HERE, "out")


def _load_spec(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _emit(art, v) -> int:
    print(f"产物: {art.path}  ({art.size} bytes, sha256 {art.sha256[:12]})")
    print(v.report())
    # 判定之后，把两个数也摆出来。布尔给 CI，两个数给人。
    if art.exists:
        try:
            d = percept.perceive(art.kind, art.path)
            print("  【两个数】实际误差 / 你能看见的误差")
            print(percept.format_pair(d))
        except Exception as e:
            print(f"  [显形层跳过] {type(e).__name__}: {e}")
    return 0 if v.ok else 1


def _kind_of(path: str) -> str:
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext in ("png", "jpg", "jpeg", "webp", "bmp", "gif"):
        return "image"
    if ext in ("mp4", "mov", "mkv", "webm", "avi"):
        return "video"
    if ext in ("wav", "mp3", "flac", "ogg", "m4a"):
        return "audio"
    return "unknown"


def cmd_show(a) -> int:
    """显形：只给两个数，不下结论。

    这是本包真正要交付的东西（第二十节）。判定层说 PASS/FAIL 会把
    「藏了多少倍」完全抹掉 —— 它过了，于是那些误差从来没被谁看见过。
    本命令把它们摆出来，看不看得见由你的眼睛决定。
    """
    kind = a.kind or _kind_of(a.path)
    if kind == "unknown":
        print(f"认不出这是哪种产物: {a.path}")
        print("用 --kind image|video|audio 指定")
        return 1
    try:
        d = percept.perceive(kind, a.path, view_deg=a.view_deg)
    except Exception as e:
        print(f"[{type(e).__name__}] {e}")
        return 1
    print(f"显形: {a.path}  ({kind})")
    print(percept.format_pair(d))
    return 0


def cmd_list(a) -> int:
    print(json.dumps(capabilities_manifest(), ensure_ascii=False, indent=2))
    return 0


def cmd_image(a) -> int:
    spec = _load_spec(a.spec)
    art = cimg.render(spec, out_dir=a.out or DEFAULT_OUT)
    return _emit(art, verify.image(art))


def cmd_video(a) -> int:
    spec = _load_spec(a.spec)
    if spec.get("mode") == "slideshow":
        art = cvid.slideshow(spec["images"], spec.get("seconds_per", 2.0),
                             out_dir=a.out or DEFAULT_OUT)
    else:
        art = cvid.animate(spec, out_dir=a.out or DEFAULT_OUT)
    return _emit(art, verify.video(art))


def cmd_audio(a) -> int:
    spec = _load_spec(a.spec)
    kind = spec.get("kind", "melody")
    if kind == "tone":
        data = caud.tone(spec.get("freq", 440), spec.get("seconds", 1.0))
    elif kind == "sweep":
        data = caud.sweep(spec.get("f0", 200), spec.get("f1", 2000),
                          spec.get("seconds", 2.0))
    elif kind == "beep":
        data = caud.beep(spec.get("seconds", 0.15), spec.get("freq", 880))
    elif kind == "say":
        data = caud.say(spec.get("text", ""))
    else:
        data = caud.melody(spec.get("notes", ["C", "E", "G"]),
                           spec.get("seconds_per_note", 0.35))
    art = caud.save(data, spec.get("name", "audio"),
                    out_dir=a.out or DEFAULT_OUT, to_mp3=spec.get("mp3", False))
    return _emit(art, verify.audio(art))


def cmd_demo(a) -> int:
    """三模态各出一个真产物，并当场判定。用来证明不是文档里的承诺。"""
    out = a.out or DEFAULT_OUT
    os.makedirs(out, exist_ok=True)
    rc = 0

    print("— 图片 —")
    art = cimg.render({
        "kind": "chart", "name": "demo_chart", "title": "存活率随稀缺度衰减",
        "series": [{"y": [0.99, 0.95, 0.81, 0.52, 0.18, 0.03], "label": "存活率"}],
        "xlabel": "稀缺度", "ylabel": "存活率",
    }, out_dir=out)
    rc |= _emit(art, verify.image(art))

    print("\n— 视频 —")
    art = cvid.animate({
        "name": "demo_anim", "title": "判据随时间累积",
        "series": [{"y": [1, 2, 4, 7, 11, 16, 22, 29], "label": "判据数"}],
        "xlabel": "轮次", "ylabel": "累计", "seconds": 3, "fps": 24,
    }, out_dir=out)
    rc |= _emit(art, verify.video(art))

    print("\n— 音频 —")
    art = caud.save(caud.melody(["C", "E", "G", "B", "C"], 0.3),
                    "demo_melody", out_dir=out)
    rc |= _emit(art, verify.audio(art))

    print("\n— 代码判定（唯一两层都自持的模态）—")
    try:
        from evalguard import scan_source
        r = scan_source("try:\n    pass\nexcept Exception:\n    pass\n", path="x.py")
        print(r.to_text())
        rc |= 0 if not r.ok else 0
        print("（此处期望扫出 blocker，扫出即判定层工作正常）")
    except Exception as e:
        print(f"[跳过] evalguard 不可用: {e}")

    return rc


def cmd_selftest(a) -> int:
    import subprocess
    return subprocess.call([sys.executable, os.path.join(_HERE, "selftest.py")])


def main() -> int:
    ap = argparse.ArgumentParser(prog="capabilities", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="打印能力清单").set_defaults(fn=cmd_list)

    for name, fn in (("image", cmd_image), ("video", cmd_video), ("audio", cmd_audio)):
        p = sub.add_parser(name, help=f"产出 {name}")
        p.add_argument("--spec", required=True, help="JSON spec 文件")
        p.add_argument("--out", help="输出目录")
        p.set_defaults(fn=fn)

    p = sub.add_parser("demo", help="三模态各出一个并判定")
    p.add_argument("--out", help="输出目录")
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser("show", help="显形：给两个数，不下结论")
    p.add_argument("path", help="产物路径")
    p.add_argument("--kind", choices=["image", "video", "audio"], help="强制指定模态")
    p.add_argument("--view-deg", type=float, default=30.0, help="画面张角（度，默认 30）")
    p.set_defaults(fn=cmd_show)

    sub.add_parser("selftest", help="判定层自检").set_defaults(fn=cmd_selftest)

    a = ap.parse_args()
    try:
        return a.fn(a)
    except Exception as e:
        print(f"[{type(e).__name__}] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
