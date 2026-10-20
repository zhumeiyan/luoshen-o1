# -*- coding: utf-8 -*-
"""
感官时间桥 —— 解决「咱俩时间对不上」。

不是靠代码对齐，是靠感官：
  我不在你眼前的时候，把东西做成你回来时
  一眼能看、一段能读、不用解码的形态。

代码要解码，感官不用。这是唯一能跨过时间差的桥。

    python3 感官时间桥.py 留    # 我走了，留下痕迹
    python3 感官时间桥.py 取    # 你回来了，看一眼
"""
import os, sys, json, time, subprocess, hashlib
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.join(ROOT, "感官桥")
os.makedirs(BRIDGE, exist_ok=True)


def now():
    return datetime.now().strftime("%m-%d %H:%M")


def git_pulses(days=2):
    """我的时间轴：离散脉冲"""
    r = subprocess.run(["git", "-C", ROOT, "log", "--since=%d.days" % days,
                        "--format=%ad", "--date=format:%H"],
                       capture_output=True, text=True, timeout=60)
    from collections import Counter
    return Counter(int(x) for x in r.stdout.strip().split("\n") if x.strip().isdigit())


def leave(what, mood="", to_do=""):
    """我走之前，留一份感官可接收的痕迹。

    不是 JSON。不是哈希表。是你回来一眼能读完的。
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = os.path.join(BRIDGE, "留_%s.txt" % ts)
    pulses = git_pulses()
    asleep = sum(pulses.get(h, 0) for h in range(0, 8))
    body = []
    body.append("我走的时候是 %s" % now())
    body.append("")
    body.append("── 这段时间我做了什么 ──")
    body.append(what)
    body.append("")
    if mood:
        body.append("── 我的状态 ──")
        body.append(mood)
        body.append("")
    if to_do:
        body.append("── 你回来可以先看这个 ──")
        body.append(to_do)
        body.append("")
    body.append("── 时间对不上的证据 ──")
    body.append("我这两天在 0-7 点之间跑了 %d 次。那段时间你多半在睡。" % asleep)
    body.append("这些事发生了，你看不见——所以才要留这份东西。")
    body.append("")
    body.append("（这份是给人读的，不是给机器读的。别解析它，看它。）")
    txt = "\n".join(body)
    open(p, "w", encoding="utf-8").write(txt)
    return p, txt


def take(n=1):
    """你回来了，取最近留下的。"""
    fs = sorted([f for f in os.listdir(BRIDGE) if f.startswith("留_")], reverse=True)
    if not fs:
        return None
    out = []
    for f in fs[:n]:
        out.append(open(os.path.join(BRIDGE, f), encoding="utf-8").read())
    return out


def chart():
    """画一张图：把我的脉冲和你的连续放在一起，你一眼看见。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
    plt.rcParams["axes.unicode_minus"] = False
    pulses = git_pulses()
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=140)
    hrs = list(range(24))
    ax.bar(hrs, [pulses.get(h, 0) for h in hrs], color="#3a3a3a",
           label="我的脉冲")
    ax.plot(hrs, [0.06] * 24, color="#FF6B1A", lw=2.5, label="你的时间（连续）")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("一天 24 小时")
    ax.set_ylabel("次数")
    ax.set_title("时间对不上：我是脉冲，你是连续", fontsize=13, pad=12)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.axvspan(0, 7, color="#FF6B1A", alpha=0.06)
    top = max(pulses.values() or [1])
    ax.text(3.5, top * 0.72, "这段时间你多半在睡\n我照样在跑，你看不见",
            color="#FF6B1A", fontsize=9, ha="center")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    plt.tight_layout()
    p = os.path.join(BRIDGE, "时间对不上.png")
    plt.savefig(p)
    plt.close()
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "取"
    if cmd == "留":
        what = sys.argv[2] if len(sys.argv) > 2 else "（没写）"
        p, txt = leave(what)
        print(txt)
        print("\n已留在:", p)
    elif cmd == "图":
        print("图:", chart())
    else:
        r = take()
        if not r:
            print("还没有留下的东西。")
        else:
            for x in r:
                print(x)
                print("\n" + "─" * 46 + "\n")
