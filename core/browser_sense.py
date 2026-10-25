#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
常驻浏览器感官 —— 让洛神真的去看网页，而不是拿现成答案
================================================================
★ 针对上一轮发现的问题：
    眼睛坏了 → 结果完全不变
    说明"看"这一步没参与输出，是挂件

★ 本模块的目标：把"看"变成【硬依赖】
    看失败 → 必须答不出来（raise），不许悄悄回退到先验

----------------------------------------------------------------
设计原则（与 ★26/★31 一致：不假装）
----------------------------------------------------------------
    1. 不许 try/except 兜底后返回默认值
    2. 看不到的字段一律 None，并标注 provenance
    3. 每次看都要留：URL、抓取时刻、HTTP 状态、内容哈希
    4. 与 ★24 双耳/★25 双眼同构：
       眼睛有 Nyquist（每度 10 像素）
       浏览器有【抓取能力边界】—— 403 就是 403，不伪装成空内容
"""
from __future__ import annotations
import os, json, time, hashlib, datetime, subprocess
from typing import Any

# 抓取留痕目录（★ 每次看都要留证据）
SHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), ".sense", "shots")


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()[:16]


class SeenWeb:
    """一次真实的"看"。看不到就是看不到，不编。"""

    def __init__(self, url: str, ok: bool, status: Any,
                 text: str | None, err: str | None,
                 ts: str, elapsed: float):
        self.url = url
        self.ok = ok
        self.status = status
        self.text = text
        self.err = err
        self.ts = ts
        self.elapsed = elapsed

    @property
    def sha(self) -> str | None:
        return _sha(self.text) if self.text else None

    @property
    def nchars(self) -> int:
        return len(self.text) if self.text else 0

    def to_dict(self) -> dict:
        return {"url": self.url, "ok": self.ok, "status": self.status,
                "nchars": self.nchars, "sha": self.sha, "err": self.err,
                "ts": self.ts, "elapsed_s": round(self.elapsed, 2)}


class BrowserSense:
    """★ 硬依赖的浏览器感官。

    与上一轮的区别：
      - 上一轮 看失败 → 照常用先验答（假依赖）
      - 本模块 看失败 → 【raise】，不许回退
    """

    def __init__(self, strict: bool = True):
        self.strict = strict
        self.history: list[SeenWeb] = []
        os.makedirs(SHOT_DIR, exist_ok=True)

    # ---------- 用系统 fetch 工具去看 ----------
    def look(self, url: str, timeout: int = 25) -> SeenWeb:
        t0 = time.time()
        ts = _now()
        try:
            r = subprocess.run(
                ["python3", "-c", _FETCH_SNIPPET, url, str(timeout)],
                capture_output=True, text=True, timeout=timeout + 10)
            out = r.stdout.strip()
            if r.returncode != 0 and not out:
                s = SeenWeb(url, False, None, None,
                            (r.stderr or "no output").strip()[:300],
                            ts, time.time() - t0)
            else:
                # 第一行是状态，后面是正文
                lines = out.split("\n", 1)
                head = lines[0]
                body = lines[1] if len(lines) > 1 else ""
                if head.startswith("OK"):
                    status = head.split(" ", 1)[1] if " " in head else "?"
                    s = SeenWeb(url, True, status, body, None,
                                ts, time.time() - t0)
                else:
                    s = SeenWeb(url, False, head[:80], None,
                                head[:300], ts, time.time() - t0)
        except subprocess.TimeoutExpired:
            s = SeenWeb(url, False, "TIMEOUT", None, "timeout",
                        ts, time.time() - t0)
        except Exception as e:
            s = SeenWeb(url, False, "EXC", None, str(e)[:300],
                        ts, time.time() - t0)

        self.history.append(s)
        self._archive(s)
        return s

    # ---------- ★ 硬依赖：看不到就炸 ----------
    def must_look(self, url: str, timeout: int = 25) -> SeenWeb:
        s = self.look(url, timeout=timeout)
        if not s.ok and self.strict:
            raise RuntimeError(
                f"★ 看不到 {url}（{s.status}/{s.err}）—— "
                f"按硬依赖原则，不许回退到先验")
        return s

    def _archive(self, s: SeenWeb) -> None:
        """★ 每次看都留证据（URL/时刻/状态/哈希）"""
        p = os.path.join(SHOT_DIR, f"{int(time.time())}_{_sha(s.url)}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(s.to_dict(), f, ensure_ascii=False, indent=1)

    # ---------- 从看到的内容里【读】 ----------
    def read_field(self, s: SeenWeb, key: str) -> str | None:
        """★ 从真实抓到的文本里读字段。读不到返回 None，不猜。"""
        if not s.text:
            return None
        for line in s.text.split("\n"):
            if key.lower() in line.lower():
                return line.strip()[:200]
        return None


_FETCH_SNIPPET = r'''
import sys, urllib.request, urllib.error
url = sys.argv[1]
to = int(sys.argv[2])
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/153 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
})
try:
    with urllib.request.urlopen(req, timeout=to) as r:
        raw = r.read(400000)
        txt = raw.decode("utf-8", "ignore")
        print("OK", r.status)
        print(txt)
except urllib.error.HTTPError as e:
    print("HTTPERROR", e.code)
except Exception as e:
    print("ERROR", type(e).__name__, str(e)[:200])
'''


# ================================================================
# ★ 让洛神"看完之后说出来" —— 不许用先验
# ================================================================
def describe(s: SeenWeb) -> str:
    """★ 它只能说【它看到的东西】。看不到就说看不到。"""
    if not s.ok:
        return f"我打不开 {s.url}（{s.status}）。我没有看到它的内容，所以不能说它是什么。"
    return (f"我看的是 {s.url}\n"
            f"  HTTP {s.status}，抓到 {s.nchars} 个字符\n"
            f"  内容哈希 {s.sha}\n"
            f"  抓取时刻 {s.ts}，耗时 {s.elapsed:.2f}s")
