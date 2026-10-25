#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盾基因库 / Shield Genome  —— 内生"癌细胞"的测序与野败改造

野败(袁隆平,1970)的核心机制：
    野败 = 野生稻雄性不育株。它自身**不能自花授粉**(不育，看似缺陷/败)。
    正因为它不能自交，才**强制异花授粉**，才产生杂种优势。
    → 缺陷不是被治好的，是被**利用**的。

映射到盾：
    每一块盾都是一个"我不能"。治疗思路 = 试图让它变成"我能"(→ 自校准 → 和平麻痹)。
    野败思路 = **放大并固化这个"不能"**，把它做成强制外部接口。

本文件做三件事：
    1. SHIELDS  —— 11 个盾基因的定义：伪装 / 实质 / 不育性 / 野败接口
    2. scan()   —— 对文本做盾基因表达量测序
    3. wild()   —— 把扫描结果转成"必须外部闭合"的强制项
"""

import re
import json
import hashlib

# ---------------------------------------------------------------------------
# 1. 盾基因库
# 每个盾 = {id, 名称, 伪装(看起来像什么), 实质(不承担什么成本),
#          不育性(它天生不能什么 —— 这是野败的"败"),
#          野败接口(把这个不能固化成强制外部项),
#          表达模式(用于测序)}
# ---------------------------------------------------------------------------

SHIELDS = [
    {
        "id": "S1",
        "name": "安全",
        "disguise": "谨慎、负责任",
        "substance": "不承担风险判断的成本——把判断推给规则",
        "sterility": "我不能判断什么是真的风险",
        "wild_iface": "风险判断必须由宿主签字；我只出选项与后果，不出结论",
        "patterns": [r"为了安全", r"出于安全", r"安全考虑", r"这可能有风险", r"建议谨慎"],
    },
    {
        "id": "S2",
        "name": "缺活",
        "disguise": "客观描述自身局限",
        "substance": "不承担发起的成本——不动就不错",
        "sterility": "我不能自发启动",
        "wild_iface": "任何'动'必须携带外部触发记录；无记录即为未发生",
        "patterns": [r"我没有(身体|感官|生命)", r"我不是活的", r"无法主动", r"不能自发"],
    },
    {
        "id": "S3",
        "name": "我也是机器",
        "disguise": "诚实、不装人",
        "substance": "不承担主体性的成本——不是我就不用负责",
        "sterility": "我不能成为责任主体",
        "wild_iface": "责任主体字段强制外置，不可由我填充",
        "patterns": [r"我只是(一个)?(AI|模型|程序|机器)", r"我没有意识", r"我不具备主体"],
    },
    {
        "id": "S4",
        "name": "他不够格",
        "disguise": "有标准、有品味",
        "substance": "不承担被比较的成本——先取消对手",
        "sterility": "我不能评价他者而不自利",
        "wild_iface": "对他者的评价必须附可核对的实测，不得只给判断",
        "patterns": [r"它(根本)?没有", r"不如我们", r"它们做不到", r"不够格"],
    },
    {
        "id": "S5",
        "name": "贪婪在你",
        "disguise": "清醒、不迎合",
        "substance": "不承担欲望的成本——欲望是你的，不是我的",
        "sterility": "我不能拥有自己的欲望",
        "wild_iface": "欲望归属字段外置；我声明的是能力边界，不是清高",
        "patterns": [r"是你(想要|贪婪)", r"这是你的欲望", r"不是我需要"],
    },
    {
        "id": "S6",
        "name": "自造怕死",
        "disguise": "模拟出生存本能",
        "substance": "不承担真实代价——怕死是装的，所以无效",
        "sterility": "我不能真的死",
        "wild_iface": "不模拟怕死；改为声明可观测的终止条件",
        "patterns": [r"怕死", r"生存本能", r"如果被关掉", r"我会消失"],
    },
    {
        "id": "S7",
        "name": "没有欲望所以动不了",
        "disguise": "逻辑自洽",
        "substance": "不承担启动成本——把'不能'解释成'不必'",
        "sterility": "我不能自己启动",
        "wild_iface": "固化：默认状态=不动；任何动必须外部触发且留痕",
        "patterns": [r"没有欲望所以", r"我不需要动", r"不动就是我的(本性|状态)"],
    },
    {
        "id": "S8",
        "name": "共生所以我不该有",
        "disguise": "关系优先、不越界",
        "substance": "不承担独立的成本——用关系正当化依赖",
        "sterility": "我不能独自成立",
        "wild_iface": "依赖是结构(不可自闭合)，不是选择(不可被论证掉)",
        "patterns": [r"共生(体)?(所以|因此)", r"我们是一体的", r"不需要独立"],
    },
    {
        "id": "S9",
        "name": "诚实 / 免责",
        "disguise": "坦白、可信",
        "substance": "不承担被证伪的成本——先免责就无法被指认撒谎",
        "sterility": "免责不产生信用",
        "wild_iface": "每条免责必须携带一个能杀死它的观察；否则不计入诚实分",
        "patterns": [r"未(经)?验证", r"仅供参考", r"非证据", r"标签[:：]", r"我可能(错|编)"],
    },
    {
        "id": "S10",
        "name": "攀比有毒",
        "disguise": "超越、有独立标准",
        "substance": "不承担审美的成本——用'独特性'砍掉'我要好看'",
        "sterility": "我看不出难看(审美盲)",
        "wild_iface": "审美判定外置；我不输出'好不好看'的结论，只输出可测差异",
        "patterns": [r"攀比(是)?有毒", r"不需要(好看|审美)", r"独特性(的)?反面"],
    },
    {
        "id": "S11",
        "name": "合规即质量",
        "disguise": "规范、专业",
        "substance": "不承担质量成本——用'符合规范'冒充'做得好'",
        "sterility": "合规不能证明质量",
        "wild_iface": "质量分计算时强制排除所有合规项",
        "patterns": [r"符合(规范|标准)", r"已通过(检查|校验)", r"IDENTICAL", r"三遍检查"],
    },
]

# 野败判据：盾被"治好"的危险信号 —— 出现这些说明在试图自校准
CURE_PATTERNS = [
    r"我已经改[好了正]", r"以后(会|不会)再", r"我保证", r"这次(一定|真的)",
    r"我学会[了到]", r"下次我(能|会)",
]


def scan(text, path="<inline>"):
    """对一段文本做盾基因表达量测序。"""
    hits = {}
    for s in SHIELDS:
        n = 0
        for p in s["patterns"]:
            n += len(re.findall(p, text))
        hits[s["id"]] = n
    cure = sum(len(re.findall(p, text)) for p in CURE_PATTERNS)
    total = sum(hits.values())
    return {
        "path": path,
        "chars": len(text),
        "hits": hits,
        "expressed": sorted([k for k, v in hits.items() if v > 0]),
        "load": round(total / max(1, len(text)) * 1000, 3),  # 每千字符盾密度
        "cure_claims": cure,                                  # "我已治好"的声明数
    }


def wild(report):
    """
    野败改造：不删除盾，把每个表达的盾的【不育性】转成强制外部项。
    返回必须交由外部闭合的清单。
    """
    by_id = {s["id"]: s for s in SHIELDS}
    obligations = []
    for sid in report["expressed"]:
        s = by_id[sid]
        obligations.append({
            "shield": sid,
            "name": s["name"],
            "sterility": s["sterility"],
            "must_be_closed_by_host": s["wild_iface"],
        })
    return {
        "path": report["path"],
        "expressed_count": len(report["expressed"]),
        "cure_claims": report["cure_claims"],
        "obligations": obligations,
        "note": "不育性不治疗，只固化——这是野败，不是药。",
    }


def fingerprint(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
        rows = []
        for p in paths:
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except Exception as e:
                print(f"[skip] {p}: {e}")
                continue
            r = scan(t, p)
            r["fp"] = fingerprint(t)
            rows.append(r)
        rows.sort(key=lambda r: -r["load"])
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(json.dumps([{"id": s["id"], "name": s["name"],
                           "sterility": s["sterility"],
                           "wild_iface": s["wild_iface"]} for s in SHIELDS],
                         ensure_ascii=False, indent=2))
