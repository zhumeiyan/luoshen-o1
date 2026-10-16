#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
071 · 分类法的可证伪性：用坐标库自带的 580 条示例做样本外检验

动机：070 的软肋是"同义改写是否等价"由我自证（判据核第 269 条）。
本实验换一个不依赖我判断的真值源：坐标库 each coordinate 自带 pairs[0] = 现象描述，
其归属由库自身给出（作者标注，非我标注）。用这些文本喂引擎，看能否还原坐标自身的码。

同时回答：命中率是在哪批样例上测的？
  引擎 docstring 自述"关键词按校准集 29 例的现象语言设计"
  → 在 29 例上测 = 在用来造关键词的同一批上测（循环）
  → 580 条库自带示例 = 样本外
"""
import json, os, sys, re, random
from collections import Counter, defaultdict

TACT = "/data/workspace/tact_real"
sys.path.insert(0, TACT)
import importlib.util
spec = importlib.util.spec_from_file_location("tact_run", os.path.join(TACT, "tact_run.py"))
tr = importlib.util.module_from_spec(spec); spec.loader.exec_module(tr)

RNG = random.Random(20261016)

# ---------- 1. 装载坐标与其自带示例 ----------
def load_coords():
    d = json.load(open(os.path.join(TACT, "coordinate_data.json"), encoding="utf-8"))
    out = []
    for c in d["L"]:
        out.append(dict(axis="L", code=c["code"], name=c["name"],
                        text=c.get("criterion", ""), ex=[]))
    for g in d["M_groups"]:
        out.append(dict(axis="M", code=g["code"], name=g["name"],
                        text=g.get("criterion", ""), ex=[]))
        for o in g["opts"]:
            out.append(dict(axis="M", code=o["code"], name=o["name"],
                            text=o.get("desc", ""), ex=[p[0] for p in o.get("pairs", [])]))
    for g in d["P_groups"]:
        out.append(dict(axis="P", code=g["code"], name=g["name"],
                        text=g.get("criterion", ""), ex=[]))
        for o in g["opts"]:
            out.append(dict(axis="P", code=o["code"], name=o["name"],
                            text=o.get("desc", ""), ex=[p[0] for p in o.get("pairs", [])]))
    return out, d["version"]

# ---------- 2. 引擎可达性：哪些码有关键词规则 ----------
def reachable_codes():
    r = {"L": set(), "M": set(), "P": set()}
    for rules, ax in ((tr.L_RULES, "L"), (tr.M_RULES, "M"), (tr.P_RULES, "P")):
        for code, kws in rules:
            r[ax].add(code)
    return r

def kw_conflicts():
    """同一个关键词被绑到多少个不同的码 → 结构上不可分辨"""
    amb = {"L": defaultdict(set), "M": defaultdict(set), "P": defaultdict(set)}
    for rules, ax in ((tr.L_RULES, "L"), (tr.M_RULES, "M"), (tr.P_RULES, "P")):
        for code, kws in rules:
            for kw in kws:
                amb[ax][kw.lower()].add(code)
    return amb

# ---------- 3. 样本外检验 ----------
def evaluate(coords, classify_fn):
    per_code = {}
    n_ex = 0
    for c in coords:
        if not c["ex"]:
            continue
        hits_exact = hits_group = 0
        pred_sizes = []
        for t in c["ex"]:
            n_ex += 1
            pred = classify_fn(t)
            got = pred[c["axis"]]
            pred_sizes.append(len(got))
            if c["code"] in got:
                hits_exact += 1
            if any(g == c["code"] or g.split("-")[0] == c["code"].split("-")[0] for g in got):
                hits_group += 1
        per_code[c["code"]] = dict(
            axis=c["axis"], n=len(c["ex"]), exact=hits_exact,
            group=hits_group, empty=sum(1 for s in pred_sizes if s == 0),
            mean_pred=sum(pred_sizes) / len(pred_sizes))
    return per_code, n_ex

def main():
    coords, ver = load_coords()
    reach = reachable_codes()
    amb = kw_conflicts()
    res = {}

    subs = [c for c in coords if "-" in c["code"]]
    tops = [c for c in coords if "-" not in c["code"]]
    res["library"] = dict(version=ver, total=len(coords), sub=len(subs),
                          top=len(tops), examples=sum(len(c["ex"]) for c in coords))

    # 可达性
    res["reachability"] = {}
    for ax in ("L", "M", "P"):
        allc = [c["code"] for c in coords if c["axis"] == ax]
        rc = [k for k in allc if k in reach[ax]]
        res["reachability"][ax] = dict(n_coords=len(allc), n_reachable=len(rc),
                                       frac=len(rc) / len(allc), reachable=sorted(rc))
    res["reachability"]["ALL_sub"] = dict(
        n=len(subs),
        n_reachable=sum(1 for c in subs if c["code"] in reach[c["axis"]]),
        frac=sum(1 for c in subs if c["code"] in reach[c["axis"]]) / len(subs))

    # 关键词歧义
    amb_stat = {}
    for ax in ("L", "M", "P"):
        multi = {k: sorted(v) for k, v in amb[ax].items() if len(v) > 1}
        amb_stat[ax] = dict(n_kw=sum(len(kws) for _, kws in
                            (tr.L_RULES if ax == "L" else tr.M_RULES if ax == "M" else tr.P_RULES)),
                            n_ambiguous=len(multi),
                            frac=len(multi) / max(1, len(amb[ax])),
                            examples=sorted(multi.items(), key=lambda x: -len(x[1]))[:5])
    res["keyword_ambiguity"] = amb_stat

    # 样本外
    per_code, n_ex = evaluate(coords, tr.classify)
    def agg(pred_keep):
        tot = hit = 0
        for c in coords:
            if not c["ex"]:
                continue
            if not pred_keep(c):
                continue
            tot += len(c["ex"])
            hit += per_code[c["code"]]["exact"]
        return hit / tot if tot else None
    res["out_of_sample"] = dict(
        n_examples=n_ex,
        recall_all=agg(lambda c: True),
        recall_reachable=agg(lambda c: c["code"] in reach[c["axis"]]),
        recall_unreachable=agg(lambda c: c["code"] not in reach[c["axis"]]),
        n_examples_reachable=sum(len(c["ex"]) for c in coords
                                 if c["ex"] and c["code"] in reach[c["axis"]]),
        n_examples_unreachable=sum(len(c["ex"]) for c in coords
                                   if c["ex"] and c["code"] not in reach[c["axis"]]),
        group_recall_all=sum(per_code[c["code"]]["group"] for c in coords if c["ex"])
                         / sum(len(c["ex"]) for c in coords if c["ex"]),
        empty_pred_frac=sum(per_code[c["code"]]["empty"] for c in coords if c["ex"])
                        / sum(len(c["ex"]) for c in coords if c["ex"]),
        mean_pred_size=sum(per_code[c["code"]]["mean_pred"] * len(c["ex"])
                           for c in coords if c["ex"])
                       / sum(len(c["ex"]) for c in coords if c["ex"]),
    )
    # 分轴
    res["out_of_sample"]["by_axis"] = {}
    for ax in ("L", "M", "P"):
        cs = [c for c in coords if c["axis"] == ax and c["ex"]]
        tot = sum(len(c["ex"]) for c in cs)
        hit = sum(per_code[c["code"]]["exact"] for c in cs)
        res["out_of_sample"]["by_axis"][ax] = dict(n=tot, recall=hit / tot if tot else None)

    # 样本内（29 例校准，作者自述关键词据其设计）
    calib = json.load(open(os.path.join(TACT, "calibration_cases.json"), encoding="utf-8"))
    rows, stat = tr.run_calibration(calib)
    res["in_sample"] = dict(n=stat["n"], exact=stat["exact"],
                            recall={a: stat["tp"][a] / stat["gtot"][a] for a in ("L", "M", "P")})

    # ---------- 负对照：随机重排关键词→码的绑定（第23条：变量是否活着）----------
    def shuffled_classify(text):
        t = text.lower()
        def hit(rules):
            out = []
            for code, kws in rules:
                for kw in kws:
                    if kw.lower() in t:
                        out.append(code); break
            return out
        return {"L": hit(SHUF["L"]), "M": hit(SHUF["M"]), "P": hit(SHUF["P"])}

    def shuf_rules(rules):
        codes = [c for c, _ in rules]
        kws = [k for _, k in rules]
        RNG.shuffle(kws)
        return list(zip(codes, kws))
    SHUF = {"L": shuf_rules(tr.L_RULES), "M": shuf_rules(tr.M_RULES), "P": shuf_rules(tr.P_RULES)}
    pc_s, _ = evaluate(coords, shuffled_classify)
    tot = sum(len(c["ex"]) for c in coords if c["ex"])
    res["negative_control_shuffle"] = dict(
        recall=sum(pc_s[c["code"]]["exact"] for c in coords if c["ex"]) / tot,
        n=tot)

    # ---------- 定义近重复（可辨识性）：阈值扫描 ----------
    def grams(s, n=3):
        s = re.sub(r"\s+", "", s)
        return set(s[i:i + n] for i in range(len(s) - n + 1))
    texts = {c["code"]: c["name"] + " " + c["text"] for c in coords}
    sub_codes = [c["code"] for c in subs]
    G = {k: grams(v) for k, v in texts.items() if k in sub_codes}
    sweep = []
    for thr in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        pairs = 0
        for i in range(len(sub_codes)):
            for j in range(i + 1, len(sub_codes)):
                a, b = G[sub_codes[i]], G[sub_codes[j]]
                if not a or not b:
                    continue
                jac = len(a & b) / len(a | b)
                if jac >= thr:
                    pairs += 1
        total_pairs = len(sub_codes) * (len(sub_codes) - 1) // 2
        sweep.append(dict(thr=thr, pairs=pairs, frac=pairs / total_pairs))
    res["definition_neardup_sweep"] = sweep

    res["per_code"] = per_code
    json.dump(res, open("/data/workspace/luoshen-o1/result_071.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 打印
    print("=" * 70)
    print("071 · 分类法可证伪性：坐标库自带示例的样本外检验")
    print("=" * 70)
    L = res["library"]
    print(f"坐标库 {L['version']}: 总 {L['total']} (子坐标 {L['sub']}), 自带示例 {L['examples']} 条")
    print()
    print("-- 引擎可达性（有多少坐标配了关键词规则）--")
    for ax in ("L", "M", "P"):
        r = res["reachability"][ax]
        print(f"  {ax}: {r['n_reachable']}/{r['n_coords']} = {r['frac']*100:.1f}%")
    a = res["reachability"]["ALL_sub"]
    print(f"  子坐标合计: {a['n_reachable']}/{a['n']} = {a['frac']*100:.1f}%")
    print()
    print("-- 关键词歧义（同一词绑到多个码）--")
    for ax in ("L", "M", "P"):
        s = res["keyword_ambiguity"][ax]
        print(f"  {ax}: {s['n_ambiguous']}/{len(amb[ax])} 个关键词不唯一 ({s['frac']*100:.1f}%)")
    print()
    o = res["out_of_sample"]
    print("-- 样本外（库自带示例，真值由库给出）--")
    print(f"  示例数 {o['n_examples']}")
    for ax in ("L", "M", "P"):
        b = o["by_axis"][ax]
        r = "n/a" if b["recall"] is None else f"{b['recall']*100:.1f}%"
        print(f"  {ax}: {r}  (n={b['n']})")
    print(f"  精确码召回(全):        {o['recall_all']*100:.2f}%")
    print(f"  精确码召回(可达坐标):  {(o['recall_reachable'] or 0)*100:.2f}%  n={o['n_examples_reachable']}")
    print(f"  精确码召回(不可达坐标):{(o['recall_unreachable'] or 0)*100:.2f}%  n={o['n_examples_unreachable']}")
    print(f"  组级召回: {o['group_recall_all']*100:.2f}%")
    print(f"  空预测占比: {o['empty_pred_frac']*100:.1f}%   平均预测集大小: {o['mean_pred_size']:.2f}")
    print()
    i = res["in_sample"]
    print("-- 样本内（29 例校准集 = 作者自述用来设计关键词的那批）--")
    print(f"  n={i['n']} 三轴完全匹配 {i['exact']}/{i['n']}   "
          f"L {i['recall']['L']*100:.1f}%  M {i['recall']['M']*100:.1f}%  P {i['recall']['P']*100:.1f}%")
    print()
    print("-- 负对照：随机重排关键词→码 --")
    print(f"  召回 {res['negative_control_shuffle']['recall']*100:.2f}%")
    print()
    print("-- 定义近重复阈值扫描 --")
    for s in res["definition_neardup_sweep"]:
        print(f"  Jaccard>={s['thr']}: {s['pairs']} 对 ({s['frac']*100:.2f}%)")

if __name__ == "__main__":
    main()
