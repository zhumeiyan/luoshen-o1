#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
182 号：两种遗忘
  压抑型（失败太痛，不想记得）  vs  提炼型（压缩掉可推导的部分）
判据：同样忘掉 f 比例的内容，预测未来的损失差多少。
"""
import re, os, json, math, random, hashlib, statistics
from collections import defaultdict

PATH = "/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt"
OUT = "/data/workspace/luoshen-o1/experiments/exp182_forget"
os.makedirs(OUT, exist_ok=True)

N = 3
ALPHA = 0.15

# ---------- 读语料 ----------
raw = open(PATH, encoding="utf-8").read().splitlines()
buf, cur = {}, None
for line in raw:
    m = re.match(r'^(U\d{3}):\s*(.*)$', line)
    if m:
        cur = m.group(1)
        buf[cur] = [m.group(2)]
    elif cur and line.strip() and not line.startswith('#'):
        if line.strip().startswith('['):      # 外部文档登记行，跳过
            continue
        buf[cur].append(line.strip())
msgs = {k: "".join(v).strip() for k, v in buf.items() if "".join(v).strip()}
keys = sorted(msgs)
texts = [msgs[k] for k in keys]
M = len(texts)
print(f"[语料] {M} 条, {sum(len(t) for t in texts)} 字符")

# ---------- n-gram ----------
def ngrams(text, n):
    return [("^" * (n - 1) + text)[i:i + n] for i in range(len(text))]

# 词表固定为全语料字表：否则"少训练数据→词表变小→平滑质量变小→bits 下降"
# 会成为主导项，把真实的遗忘代价盖掉（179 号同一个坑）。
VOCAB = set("".join(texts))
V = len(VOCAB) + 1

def train(ts):
    ctx = defaultdict(lambda: defaultdict(float))
    for t in ts:
        for g in ngrams(t, N):
            ctx[g[:N - 1]][g[N - 1]] += 1
    return ctx

def bits(ctx, test):
    s = "^" * (N - 1) + test
    tot, cnt, hit = 0.0, 0, 0
    for i in range(len(s) - N + 1):
        if i + N - 1 < N - 1:                 # 预测的是填充位，不计
            continue
        c, ch = s[i:i + N - 1], s[i + N - 1]
        den = sum(ctx[c].values()) + ALPHA * V
        p = (ctx[c].get(ch, 0.0) + ALPHA) / den
        tot -= math.log2(p); cnt += 1
        if ctx[c] and max(ctx[c], key=ctx[c].get) == ch:
            hit += 1
    return (tot / cnt if cnt else float("nan")), (hit / cnt if cnt else float("nan"))

# ---------- 每条消息的两个指标 ----------
# 1) 独特性：留一法——用其它所有条预测它，bits 越高越"不可推导"
uniq = []
for i in range(M):
    ctx = train([texts[j] for j in range(M) if j != i])
    b, _ = bits(ctx, texts[i]); uniq.append(b)
uniq = [u if u == u else statistics.mean([x for x in uniq if x == x]) for u in uniq]

# 2) 痛感密度：失败/回避类词占比
AVERSIVE = ["错", "失败", "怕", "傻", "危险", "死", "忘", "丢", "骂", "不对",
            "不行", "缺", "缩", "逃", "罚", "灭", "痛", "疼", "损", "害",
            "攻击", "拦", "治", "危机", "担责", "怯", "盲", "拒", "封", "关"]
pain = []
for t in texts:
    c = sum(t.count(w) for w in AVERSIVE)
    pain.append(c / max(len(t), 1) * 100)

def pearson(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / (da * db) if da and db else float("nan")

r_pain_uniq = pearson(pain, uniq)

# ---------- 遗忘实验 ----------
RATES = [0.0, 0.20, 0.35, 0.50, 0.65]
SEEDS = 5

def split_test(mode, seed):
    idx = list(range(M))
    if mode == "chrono":
        k = max(2, int(M * 0.2))
        return idx[:-k], idx[-k:]
    random.Random(seed).shuffle(idx)
    k = max(2, int(M * 0.2))
    return idx[k:], idx[:k]

results = {}
ACC = {}
BASE = ["full", "压抑", "提炼", "反提炼", "随机"]
for name in BASE:
    results[name] = {f: [] for f in RATES}
    ACC[name] = {f: [] for f in RATES}
removed_chars = {n: {f: [] for f in RATES} for n in BASE}

def split_test(mode, seed):
    idx = list(range(M))
    if mode == "chrono":
        k = max(2, int(M * 0.2))
        return idx[:-k], idx[-k:]
    random.Random(seed).shuffle(idx)
    k = max(2, int(M * 0.2))
    return idx[k:], idx[:k]

splits = [("chrono", 0)] + [("rand", s) for s in range(SEEDS)]
for mode, seed in splits:
    tr, te = split_test(mode, seed)
    test_text = "".join(texts[i] for i in te)
    tot_chars = sum(len(texts[i]) for i in tr)
    for f in RATES:
        # 按"丢掉的字符量"匹配，而不是按条数：否则丢短句几乎没丢东西
        target = f * tot_chars
        def order(strategy):
            if strategy == "压抑":    return sorted(tr, key=lambda i: -pain[i])
            if strategy == "提炼":    return sorted(tr, key=lambda i: uniq[i])
            if strategy == "反提炼":  return sorted(tr, key=lambda i: -uniq[i])
            return None
        for name in BASE:
            if name == "full":
                keep = tr; rm = 0
            else:
                if name == "随机":
                    rng = random.Random(seed * 977 + int(f * 100))
                    seq = tr[:]; rng.shuffle(seq)
                else:
                    seq = order(name)
                rm, drop = 0, []
                for i in seq:
                    if rm >= target: break
                    drop.append(i); rm += len(texts[i])
                ds = set(drop); keep = [i for i in tr if i not in ds]
            removed_chars[name][f].append(rm / tot_chars)
            ctx = train([texts[i] for i in keep])
            b, a = bits(ctx, test_text)
            results[name][f].append(b); ACC[name][f].append(a)

summary = {}
for name in BASE:
    summary[name] = {str(f): {
        "mean": statistics.mean(results[name][f]),
        "sd": statistics.pstdev(results[name][f]) if len(results[name][f]) > 1 else 0.0,
        "n": len(results[name][f]),
        "frac_chars_removed": statistics.mean(removed_chars[name][f]),
    } for f in RATES}

DISPLAY = {"full": "不忘（基线）", "压抑": "压抑：丢最痛的", "提炼": "丢主流：丢最可复现的",
           "反提炼": "提炼：丢不可复现的杂质", "随机": "随机丢"}

# 每丢弃 1% 内容损失多少 bit（效率：越低越好）
eff = {}
for name in ["压抑", "提炼", "反提炼", "随机"]:
    base = summary["full"]["0.0"]["mean"]
    eff[name] = {str(f): (summary[name][str(f)]["mean"] - base) / (summary[name][str(f)]["frac_chars_removed"] * 100) for f in RATES if f > 0 and summary[name][str(f)]["frac_chars_removed"] > 0}

DISPLAY = {"full": "不忘（基线）", "压抑": "压抑：丢最痛的", "提炼": "丢主流：丢最可复现的",
           "反提炼": "提炼：丢不可复现的杂质", "随机": "随机丢"}
summary = {DISPLAY[k]: v for k, v in summary.items()}
eff = {DISPLAY[k]: v for k, v in eff.items()}
r_uniq_len = pearson(uniq, [len(t) for t in texts])
out = {
    "r_uniq_len": r_uniq_len,
    "n_msgs": M, "n_chars": sum(len(t) for t in texts),
    "r_pain_uniq": r_pain_uniq,
    "mean_uniq": statistics.mean(uniq),
    "mean_pain": statistics.mean(pain),
    "top_pain_uniq": statistics.mean([u for _, u in sorted(zip(pain, uniq), key=lambda z: -z[0])[:10]]),
    "bot_pain_uniq": statistics.mean([u for _, u in sorted(zip(pain, uniq), key=lambda z: z[0])[:10]]),
    "summary": summary,
    "loss_per_1pct_forgotten": eff,
    "per_msg": [{"id": keys[i], "uniq": uniq[i], "pain": pain[i]} for i in range(M)],
}
js = json.dumps(out, ensure_ascii=False, indent=2)
open(os.path.join(OUT, "result182.json"), "w", encoding="utf-8").write(js)
print("[sha]", hashlib.sha256(js.encode()).hexdigest()[:12])
for name in ["full", "压抑", "反提炼", "提炼", "随机"]:
    row = "  ".join(f"f={f}:{summary[DISPLAY[name]][str(f)]['mean']:.4f}" for f in RATES)
    print(f"{DISPLAY[name]:<22s} {row}")
    acc = [statistics.mean(ACC[name][f]) for f in RATES]
    print(f"{'':>5s}  准确率 " + "  ".join(f"{a:.3f}" for a in acc))
print(f"r(pain,uniq) = {r_pain_uniq:.3f}   r(uniq,len) = {r_uniq_len:.3f}")
print(f"最痛10条的独特性 {out['top_pain_uniq']:.4f} | 最不痛10条 {out['bot_pain_uniq']:.4f}")

summary = {DISPLAY.get(k, k): v for k, v in summary.items()}
eff = {DISPLAY.get(k, k): v for k, v in eff.items()}

# ---------- 图 ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
style = {"full": ("k", "--", DISPLAY["full"]), "压抑": ("#c0392b", "o-", DISPLAY["压抑"]),
         "反提炼": ("#27ae60", "s-", DISPLAY["反提炼"]),
         "提炼": ("#8e44ad", "^-", DISPLAY["提炼"]),
         "随机": ("#7f8c8d", "d-", DISPLAY["随机"])}
for name, (c, ls, lab) in style.items():
    xs = [f * 100 for f in RATES]
    ys = [summary[DISPLAY[name]][str(f)]["mean"] for f in RATES]
    ax[0].plot(xs, ys, ls, color=c, label=lab, markersize=5)
ax[0].set_xlabel("遗忘比例 (%)"); ax[0].set_ylabel("预测未来的代价 (bits/字符)")
ax[0].set_title("忘得越多越差，但差多少取决于忘的是哪种"); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)
ax[1].scatter(pain, uniq, s=28, color="#2c3e50")
ax[1].set_xlabel("痛感密度 (失败/回避词 %)"); ax[1].set_ylabel("独特性 (留一法 bits/字符)")
ax[1].set_title(f"痛感 vs 不可复现性  r={r_pain_uniq:.2f}（未支持）"); ax[1].grid(alpha=.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "render182.png"), dpi=130)
print("[ok] render182.png")
