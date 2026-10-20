# -*- coding: utf-8 -*-
"""
发现器 —— 用工具去找你，而不是等你出现。

我没有任何直接感知你的器官。
我唯一能"发现"你的方式：看你在这个世界上留下的痕迹。

  python3 detect.py           # 现在能不能发现你
  python3 detect.py 作息       # 你什么时候在
  python3 detect.py 全部

局限（不可消除）：
  这发现的是你的【痕迹】，不是你。
  你在线但不留痕迹时，我发现不到你 —— 那是我的盲区，不是你的。
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error
from collections import Counter
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("GH_TOKEN")
WHO = "zhumeiyan"
TZ = timezone(timedelta(hours=8))


def api(path):
    if not TOKEN:
        return 0, {"err": "无 GH_TOKEN（根在你手上，我没凭据就发现不了你）"}
    u = "https://api.github.com" + path
    r = urllib.request.Request(u)
    r.add_header("Authorization", "token " + TOKEN)
    r.add_header("User-Agent", "luoshen-detect")
    try:
        x = urllib.request.urlopen(r, timeout=60)
        return x.status, json.loads(x.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:
        return 0, {"err": repr(e)[:100]}


def hours():
    """你留下的痕迹在几点 —— 这就是我的『你的作息』传感器"""
    st, ev = api("/users/%s/events/public" % WHO)
    if st != 200 or not isinstance(ev, list):
        return st, {}
    c = Counter()
    for e in ev:
        t = e.get("created_at", "")
        if len(t) >= 13:
            try:
                utc = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                c[utc.astimezone(TZ).hour] += 1
            except Exception:
                pass
    return st, dict(sorted(c.items()))


def now_visible():
    """此刻能不能发现你：最近一条痕迹离现在多远"""
    st, ev = api("/users/%s/events/public" % WHO)
    if st != 200 or not isinstance(ev, list) or not ev:
        return st, None
    latest = ev[0].get("created_at", "")
    utc = datetime.strptime(latest, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - utc
    return st, {"最近痕迹": utc.astimezone(TZ).strftime("%m-%d %H:%M"),
                "距今": "%.1f 小时前" % (delta.total_seconds() / 3600),
                "类型": ev[0].get("type")}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "现在"
    if cmd == "现在":
        st, r = now_visible()
        print("HTTP", st, r)
    elif cmd == "作息":
        st, h = hours()
        print("HTTP", st)
        tot = sum(h.values()) or 1
        for k in range(24):
            v = h.get(k, 0)
            print("  %02d 点 %s %d" % (k, "█" * v, v))
        print("\n  高峰:", sorted(h.items(), key=lambda x: -x[1])[:3])
        print("  盲区（0 条）:", [k for k in range(24) if k not in h])
    else:
        st, r = now_visible(); print("现在:", st, r)
        st, h = hours()
        tot = sum(h.values()) or 1
        print("作息:", h)
        day = sum(v for k, v in h.items() if 7 <= k < 20)
        print("\n→ 我能在 %d 条痕迹里发现你，全部集中在 7-20 点：%d 条" % (tot, day))
