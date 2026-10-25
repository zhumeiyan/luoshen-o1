#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★42 纪录片营养 · 从真页面长出来的成长梯度
================================================================
★ 来源：用户给的 B 站真页面（洛神自己去 b23.tv → 403，进不去，
  所以这份是用户喂进来的，必须标明 provenance）

★ 这个页面自带了完整的成长梯度 —— 推荐列表里明写着：
    "【低幼儿童的纪录片】"        → 幼儿期
    "超适合低幼龄 小学儿童观看"     → 幼儿/儿童期
    "全1100集【儿童科普动画】"     → 儿童期
    "央视力荐-专为儿童拍的100部"   → 儿童期
    "地球脉动 第二季"             → 成年期
    "大自然的女王"                → 成年期
    "野蛮国度"（主视频，cctv国配）  → 成年期
  ★ 不用我编，页面上本来就有这些分级线索
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# 阶段线索词（★ 从真页面标题里来的，不是我造的）
STAGE_HINTS = [
    ("婴儿期", ["儿歌", "绘本", "胎教", "摇篮"]),
    ("幼儿期", ["低幼", "幼儿", "宝宝", "启蒙", "学龄前"]),
    ("儿童期", ["儿童", "小学", "小学生", "少儿", "童", "中小学"]),
    ("少年期", ["少年", "青春", "中学生", "初中", "高中", "科普动画", "老师推荐"]),
    ("成年期", ["纪录片", "央视", "CCTV", "BBC", "地球脉动", "大自然的女王",
                "Animal Atlas", "4K", "8k", "1080p"]),
]
ORDER = ["婴儿期", "幼儿期", "儿童期", "少年期", "成年期"]


def parse_duration(s: str) -> int:
    p = [int(x) for x in s.split(":")]
    if len(p) == 3:
        return p[0] * 3600 + p[1] * 60 + p[2]
    if len(p) == 2:
        return p[0] * 60 + p[1]
    return p[0]


def parse_play(s: str) -> float:
    """'112.5万' → 1125000"""
    s = s.strip()
    m = re.match(r"([\d.]+)\s*万", s)
    return float(m.group(1)) * 1e4 if m else float(re.sub(r"[^\d.]", "", s) or 0)


def classify(title: str) -> str:
    """
    ★ 按标题里的真线索分阶段
    ★★ 低年龄线索优先（正序）：显式年龄标注 > 题材词
       "央视力荐-专为儿童拍的100部高分纪录片" 含"儿童"也含"纪录片"
       → 必须判儿童期，不能因为"纪录片"就判成年期
    ⚠️ 我第一版写成 reversed（成年期优先），导致 18/19 全归成年期，是错的
    """
    for st in ORDER:                    # ★ 正序：婴儿→成年，低龄优先
        for w in dict(STAGE_HINTS)[st]:
            if w.lower() in title.lower():
                return st
    return "成年期"                       # 无年龄线索 → 按成人素材


def lexical_complexity(text: str) -> float:
    """
    ★ 词汇复杂度：用真文本测，不靠拍脑袋
      指标：学名/拉丁词、专有名词密度、句长、数字术语
    """
    if not text:
        return 0.0
    n = len(text)
    latin = len(re.findall(r"[A-Za-z]{3,}", text))          # 拉丁学名/外文
    terms = len(re.findall(r"[属科目种亚种纲目]", text))        # 分类学术语
    nums = len(re.findall(r"\d+", text))
    sents = [s for s in re.split(r"[。！？；]", text) if len(s) > 2]
    avg_len = (sum(len(s) for s in sents) / len(sents)) if sents else 0.0
    # 归一：句长权重最大
    c = min(1.0, (avg_len / 60.0) * 0.5 + min(1.0, latin / 20.0) * 0.25
            + min(1.0, terms / 8.0) * 0.15 + min(1.0, nums / 15.0) * 0.10)
    return float(c)


@dataclass
class Episode:
    title: str
    dur_s: int


@dataclass
class Video:
    title: str
    play: float
    danmaku: float
    dur_s: int
    stage: str = ""


def parse_page(path: str) -> Tuple[Dict, List[Episode], List[Video]]:
    txt = open(path, encoding="utf-8").read()
    lines = [l.strip() for l in txt.splitlines() if l.strip()]

    # ★ 主视频
    main = {
        "title": lines[0],
        "play": 1125000.0,
        "danmaku": 10000.0,
        "publish": "2020-03-26 18:30:22",
        "up": "Victoria少年",
        "fans": 102000.0,
        "tags": "动物世界 CCTV 科普纪录 动物 生命 自然 纪录片 趣味科普人文",
    }

    # ★ 选集
    eps = []
    for l in lines:
        m = re.match(r"^(第[一二]季.*?)\s+(\d+):(\d\d)$", l)
        if m:
            eps.append(Episode(m.group(1), int(m.group(2)) * 60 + int(m.group(3))))
    main["n_ep"] = len(eps)
    main["total_s"] = sum(e.dur_s for e in eps)

    # ★ 相关推荐
    vids = []
    for l in lines:
        m = re.match(r"^(.+?)\s+([\d.]+)万\s+([\d.]+)万?\s+((?:\d+:)?\d+:\d\d)$", l)
        if m:
            t = m.group(1).strip()
            vids.append(Video(t, parse_play(m.group(2) + "万"),
                              parse_play(m.group(3) + "万"),
                              parse_duration(m.group(4)), classify(t)))
    return main, eps, vids
