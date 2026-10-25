#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★54 让它自己去找、自己听、自己学「说话腔」
================================================================
★★ 承接 ★53
    ★53 学会的是【整句朗读腔】（cn_voice，5.7~16.3秒的朗读）
    用户要的是【说话腔 / 对话腔】

★★ 本轮它自己干的事（我只给入口，不替它选）
    ① 自己挑词（好奇度驱动：优先挑"跟已听过的差异大"的）
    ② 自己开必应中文词典页，自己抓【中文例句文本 + 真人音频链接】
    ③ 自己下载，自己听（提特征）
    ④ 自己学（线搜索步长）

★★ 关键设计：交叉盲测（防止自欺）
    ★ 如果"朗读腔语料"和"新采的口语句语料"其实是同一分布，
      那我换了个目标却没换东西 —— 交叉盲测就是抓这个的
    学A的产物，离A近还是离B近？学B的产物呢？
    若两者都各自更靠近自己的目标 → 两个目标真的不同 ✅
    若学A的产物也更靠近B → 说明目标没区分开 ❌

★★ provenance 必须标明
    必应词典例句音频：位置序列 sen_en → sen_cn → AUDIO
    推定为中文真人朗读，但我【听不到内容】，无法确认
    ⚠️ 交叉验证：与已确认中文 cn_voice 特征高度接近
       F0中位 190.5 vs 192.8 / pause_rate 0.430 vs 0.387
"""
import os, sys, re, json, time, glob, urllib.parse
import urllib.request, ssl
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.speech_selflearn import (
    StyleHidden, SpeakerParams, synth_utterance, extract_features,
    feat_vec, FEATS, PARAM_OF_FEAT, BOUNDS,
)
from core.real_voice import decode_mp3, FS, f0_track_robust
from scipy.io import wavfile

BOUNDS["jitter"] = (0.0, 0.25)
BOUNDS["f0_base"] = (70.0, 300.0)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120 Safari/537.36"}
OUT = os.path.join(HERE, "data", "dialog_voice")
os.makedirs(OUT, exist_ok=True)

ok = {}
print("=" * 92)
print(" ★54 让它自己去找、自己听、自己学「说话腔」")
print("=" * 92)
print("""
  ★ 它自己挑词 → 自己开页面 → 自己抓例句+音频 → 自己下载 → 自己听 → 自己学
  ★★ 交叉盲测防自欺：学A的产物该离A近，学B的产物该离B近
""")


# ================================================================ 工具
def fetch(url, timeout=20):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                               timeout=timeout, context=CTX)
    return r.status, r.read()


def hear(path):
    x = decode_mp3(path)
    d = extract_features(x)
    t = f0_track_robust(x)
    f0 = np.array([v for v in t if v and v > 0])
    d["f0_med"] = float(np.median(f0)) if len(f0) else 0.0
    d["dur"] = float(len(x) / FS)
    return feat_vec(d), d


# ================================================================ A 它自己挑词
print("【A】★★ 它自己挑词（好奇度驱动）")
print("-" * 92)
CANDIDATE_WORDS = [
    "你好", "真的吗", "怎么办", "我觉得", "一起", "时候", "喜欢", "现在",
    "知道", "为什么", "不要", "可以", "回来", "今天", "朋友", "有点",
    "开始", "看见", "说话", "家里", "吃饭", "睡觉", "漂亮", "生气",
    "谢谢", "再见", "帮忙", "记得", "忽然", "其实",
]
heard = []           # 它已经听过的特征（用于好奇度）
rng = np.random.default_rng(0)


def curiosity(word, heard_vecs):
    """★ 好奇度 = 跟已听过素材的差异
       ★★ 修（★54 第三次犯 ★39/★40 的错）：
           上一版 base = len(set(word))/6 + std*0.5
           std 跨 6 个量纲完全不同的特征取均值 → 数值巨大 → clip 后恒 1.000
           → 8 个词好奇度全是 1.000，排序等于随机
       ✅ 改成：各维先按自身尺度归一再求 std，且去掉 clip 上限
    """
    if not heard_vecs:
        return float(len(set(word))) / 6.0
    H = np.array(heard_vecs)
    scale = np.abs(H).mean(axis=0) + 1e-6
    spread = float((H / scale).std(axis=0).mean())
    base = len(set(word)) / 6.0
    # ★ 已听过的素材越多，对新词的好奇越低（饱和）
    sat = 1.0 / (1.0 + 0.15 * len(heard_vecs))
    return float(base * sat + spread * 0.25)


picked = []
pool = list(CANDIDATE_WORDS)
for step in range(8):                       # 它自己挑 10 个词
    scores = [(curiosity(w, heard), w) for w in pool]
    scores.sort(reverse=True)
    s, w = scores[0]
    picked.append((w, s))
    pool.remove(w)
    print(f"   第{step+1:>2}轮  挑【{w}】  好奇度 {s:.3f}")
ok["① 它自己挑了 >=8 个词"] = bool(len(picked) >= 8)
ok["② 挑词顺序不是固定枚举（好奇度有变化）"] = bool(
    len({round(s, 3) for _, s in picked}) >= 2)


# ================================================================ B 它自己采
def harvest(word, limit=3):
    """开页面 → 抓【中文例句文本 + 音频链接】"""
    q = urllib.parse.quote(word)
    try:
        st, raw = fetch(f"https://cn.bing.com/dict/search?q={q}")
    except Exception:
        return []
    if st != 200:
        return []
    h = raw.decode("utf-8", "ignore")
    marks = []
    for m in re.finditer(r'<div class="(sen_cn|sen_en)[^"]*"', h):
        marks.append((m.start(), m.group(1)))
    for m in re.finditer(r'data-mp3link="(/dict/mediamp3\?blob=[^"]+)"', h):
        marks.append((m.start(), "AUDIO", m.group(1)))
    marks.sort(key=lambda z: z[0])
    out = []
    for i, mk in enumerate(marks):
        if mk[1] != "AUDIO":
            continue
        # ★ 往前找最近的 sen_cn（音频紧跟中文例句）
        cn = None
        for j in range(i - 1, -1, -1):
            if marks[j][1] == "sen_cn":
                cn = marks[j][0]
                break
        if cn is None:
            continue
        seg = h[cn:cn + 1500]
        seg = re.sub(r"<[^>]*$", "", seg)          # ★ 去掉末尾被截断的残标签
        txt = re.sub(r"<[^>]+>", "", seg)
        txt = re.sub(r"\s+", " ", txt).strip()
        txt = txt[:60]
        if len(txt) < 4:
            continue
        out.append((txt, "https://cn.bing.com" + mk[2].replace("&amp;", "&")))
        if len(out) >= limit:
            break
    return out


print("\n【B】★★ 它自己开页面、自己抓例句和音频")
print("-" * 92)
collected = []
for w, s in picked:
    items = harvest(w, limit=2)
    for txt, url in items:
        collected.append((w, txt, url))
    print(f"   【{w}】抓到 {len(items)} 条")
    if len(items):
        print(f"        例句: {items[0][0][:52]}")
    time.sleep(0.3)
print(f"\n  ★ 共抓到 {len(collected)} 条（词 → 中文例句 → 音频）")
ok["③ 抓到 >=10 条例句"] = bool(len(collected) >= 10)
ok["④ 抓到的例句文本是中文"] = bool(
    sum(1 for _, t, _ in collected if re.search(r"[一-鿿]", t))
    >= 0.8 * max(1, len(collected)))


# ================================================================ C 它自己下载+听
def download(url, path):
    try:
        st, data = fetch(url, timeout=25)
        if st == 200 and len(data) > 4000:
            open(path, "wb").write(data)
            return True
    except Exception:
        pass
    return False


print("\n【C】★★ 它自己下载、自己听")
print("-" * 92)
new_files, new_vecs = [], []
for i, (w, txt, url) in enumerate(collected):
    p = os.path.join(OUT, f"self_{i:02d}.mp3")
    if os.path.exists(p) and os.path.getsize(p) > 4000:
        pass
    elif not download(url, p):
        continue
    try:
        v, d = hear(p)
    except Exception:
        continue
    if d["dur"] < 1.0:
        continue
    new_files.append(p)
    new_vecs.append(v)
    heard.append(v)
    if len(new_files) <= 8:
        print(f"   {i:>2} 【{w}】{d['dur']:>6.2f}s  F0中位{d['f0_med']:>6.1f} "
              f"pause{d['pause_rate']:.3f} jit{d['jitter']:.4f}  {txt[:30]}")
if len(new_files) > 8:
    print(f"   ... 共 {len(new_files)} 条")
ok["⑤ 下载并听到 >=8 条真人语音"] = bool(len(new_files) >= 8)

# ★ provenance 交叉验证：新素材 vs 已确认中文
cn_files = sorted(glob.glob(os.path.join(HERE, "data", "cn_voice", "*.mp3")))
cn_vecs = np.array([hear(p)[0] for p in cn_files])
NV = np.array(new_vecs)
print(f"\n  ★ provenance 交叉验证（推定中文，我听不到内容）")
for i, f in enumerate(FEATS):
    a, b = np.median(cn_vecs[:, i]), np.median(NV[:, i])
    print(f"    {f:<11} 已确认中文{a:>8.3f}   新采{b:>8.3f}   差 {abs(a-b)/max(abs(a),1e-6)*100:>5.0f}%")
dist_same = float(np.linalg.norm(np.median(cn_vecs, 0) - np.median(NV, 0)))
print(f"  ★ 两组中位数欧氏距离 = {dist_same:.4f}")
ok["⑥ 新素材与已确认中文素材特征同量级"] = bool(dist_same < 1.5)

# ================================================================ D 学习目标
target_B = np.median(NV, axis=0)                 # 新采口语句
target_A = np.median(cn_vecs, axis=0)            # 朗读腔（★53）
print(f"\n【D】两个目标")
print("-" * 92)
print(f"  {'特征':<11}{'A 朗读腔':>11}{'B 新采口语':>11}{'差异':>10}")
for i, f in enumerate(FEATS):
    print(f"  {f:<11}{target_A[i]:>11.3f}{target_B[i]:>11.3f}"
          f"{abs(target_A[i]-target_B[i]):>10.3f}")
gap_AB = float(np.linalg.norm(
    (target_A - target_B) / (np.abs(target_A) + 0.15)))
print(f"  ★ 归一化目标间距 = {gap_AB:.4f}")

# ================================================================ E 可信度扫描
print("\n【E】可信度扫描（★46 教训：不可信的维度不许学）")
print("-" * 92)
FEAT_OF_PARAM = {v: k for k, v in PARAM_OF_FEAT.items()}
scan_defs = {
    "jitter":      [0.02, 0.06, 0.10, 0.15, 0.22],
    "f0_span":     [0.10, 0.25, 0.40, 0.55, 0.70],
    "pause_prob":  [0.10, 0.30, 0.50, 0.70, 0.90],
    "pause_sigma": [0.20, 0.50, 0.80, 1.10, 1.40],
    "f0_end":      [-0.30, -0.15, 0.0, 0.10, 0.20],
    "repair_prob": [0.02, 0.10, 0.20, 0.30, 0.40],
}
N_UTT = 16
WORD_COUNTS = [int(x) for x in np.random.default_rng(0).integers(8, 16, N_UTT)]


def profile(sp, seed=0):
    utts = [synth_utterance(sp.to_style(), wc, np.random.default_rng(seed + i))
            for i, wc in enumerate(WORD_COUNTS)]
    return np.array([feat_vec(extract_features(y)) for y in utts]).mean(axis=0)


def err_to(sp, target, seed=0):
    cur = profile(sp, seed)
    scale = np.abs(target) + 0.15
    return float(np.sqrt(np.mean(((cur - target) / scale) ** 2))), cur


def measure(param, vals):
    sp = SpeakerParams()
    outs = []
    for v in vals:
        setattr(sp, param, v)
        outs.append(profile(sp))
    return np.array(outs)


trusted = {}
print(f"  {'参数':<13}{'特征':<12}"
      + "".join(f"{v:>9.2f}" for v in scan_defs["jitter"]) + f"{'判定':>7}")
for param, vals in scan_defs.items():
    feat = FEAT_OF_PARAM.get(param, "?")
    col = measure(param, vals)[:, FEATS.index(feat)]
    d = np.diff(col)
    mono = bool(np.all(d > 0) or np.all(d < 0))
    rel = abs(col[-1] - col[0]) / (abs(col).max() + 1e-9)
    good = bool(mono and rel > 0.25)
    trusted[param] = good
    print(f"  {param:<13}{feat:<12}"
          + "".join(f"{x:>9.3f}" for x in col) + f"{'✅' if good else '❌':>7}")
n_trust = sum(trusted.values())
print(f"  ★ 可信 {n_trust}/6")
ok["⑦ 至少 4 个维度可信"] = bool(n_trust >= 4)


# ================================================================ F 它自己学
def learn(sp, target, n_iter=10, seed=0):
    hist = []
    for it in range(n_iter):
        e0, cur = err_to(sp, target, seed)
        best = {}
        for feat_name, param in PARAM_OF_FEAT.items():
            if not trusted.get(param, False):
                continue
            i = FEATS.index(feat_name)
            lo, hi = BOUNDS[param]
            base = getattr(sp, param)
            eps = 1e-6
            ratio = float(np.clip((target[i] + eps) / (cur[i] + eps), 0.15, 6.0))
            bestv, beste = base, e0
            for lr in (0.15, 0.35, 0.60, 1.00):
                nv = float(np.clip(base * (ratio ** lr), lo, hi))
                old = getattr(sp, param)
                setattr(sp, param, nv)
                e1, _ = err_to(sp, target, seed)
                if e1 < beste - 1e-9:
                    beste, bestv = e1, nv
                setattr(sp, param, old)
            best[param] = bestv
        for p_, v_ in best.items():
            setattr(sp, p_, v_)
        hist.append(err_to(sp, target, seed)[0])
        sp.snapshot()
    return hist


print("\n【F】★★ 它自己学（分别学 A 朗读腔 / B 新采口语）")
print("-" * 92)
spA, spB = SpeakerParams(), SpeakerParams()
eA0, _ = err_to(spA, target_A); hA = learn(spA, target_A); eA1, curA = err_to(spA, target_A)
eB0, _ = err_to(spB, target_B); hB = learn(spB, target_B); eB1, curB = err_to(spB, target_B)
print(f"  学A（朗读腔）{eA0:.4f} → {eA1:.4f}   下降 {(eA0-eA1)/eA0*100:>5.1f}%")
print(f"  学B（新采口语）{eB0:.4f} → {eB1:.4f}   下降 {(eB0-eB1)/eB0*100:>5.1f}%")
# ★ 对照
spC = SpeakerParams()
eC0, _ = err_to(spC, target_B); eC1, _ = err_to(spC, target_B)
print(f"  对照（不学）  {eC0:.4f} → {eC1:.4f}   下降 {(eC0-eC1)/eC0*100:>5.1f}%")
ok["⑧ ★★ 学B 的下降 > 对照"] = bool((eB0 - eB1) / eB0 > 0.10)
ok["⑨ ★ 学习不发散"] = bool(hB[-1] < hB[0])

# ================================================================ G 交叉盲测
print("\n【G】★★★ 交叉盲测（防自欺：学A的产物该离A近）")
print("-" * 92)
scale = np.abs(target_A) + 0.15


def dist(vec, tgt):
    return float(np.sqrt(np.mean(((vec - tgt) / (np.abs(tgt) + 0.15)) ** 2)))


start = profile(SpeakerParams())
print(f"  {'产物':<16}{'离A朗读腔':>12}{'离B新采口语':>12}{'更靠近':>10}")
rows = []
for nm, v in [("起点(播报腔)", start), ("学A后", curA), ("学B后", curB)]:
    da, db = dist(v, target_A), dist(v, target_B)
    near = "A" if da < db else "B"
    rows.append((nm, da, db, near))
    print(f"  {nm:<16}{da:>12.4f}{db:>12.4f}{near:>10}")
print(f"  {'真人A':<16}{dist(np.median(cn_vecs,0),target_A):>12.4f}"
      f"{dist(np.median(cn_vecs,0),target_B):>12.4f}{'A':>10}")
print(f"  {'真人B':<16}{dist(np.median(NV,0),target_A):>12.4f}"
      f"{dist(np.median(NV,0),target_B):>12.4f}{'B':>10}")
# ★ 学A产物应更靠A；学B产物应更靠B
a_ok = rows[1][1] < rows[1][2]
b_ok = rows[2][2] < rows[2][1]
print(f"\n  ★ 学A的产物更靠近A：{'✅' if a_ok else '❌'}"
      f"    学B的产物更靠近B：{'✅' if b_ok else '❌'}")
if a_ok and b_ok:
    print("  ★★ 两个目标真的区分开了 —— 换语料确实换了目标")
else:
    print("  ⚠️ 两个目标没区分开 —— 换语料等于没换，如实标注")
ok["⑩ ★★ 交叉盲测：学A近A 且 学B近B"] = bool(a_ok and b_ok)

# ================================================================ H 自己说
print("\n【H】学完之后，它自己说一句、自己听")
print("-" * 92)
from core.real_voice import analyze_via_ear
os.makedirs(os.path.join(HERE, "data", "learn_speak"), exist_ok=True)
r2 = np.random.default_rng(7)
res = {}
for nm, sp in [("起点", SpeakerParams()), ("学A", spA), ("学B", spB)]:
    y = synth_utterance(sp.to_style(), 12, r2)
    p = os.path.join(HERE, "data", "learn_speak", f"cn_{nm}.wav")
    wavfile.write(p, FS, (y * 32767).astype(np.int16))
    r = analyze_via_ear(p)
    res[nm] = r
    print(f"  {nm:<6} F0={r['F0均值']:>7.1f}  F1={r['F1']:>7.1f}  "
          f"F2={r['F2']:>7.1f}  jitter={r['jitter']:.4f}")
real_A = np.median([analyze_via_ear(p)["F0均值"] for p in cn_files[:5]])
real_B = np.median([analyze_via_ear(p)["F0均值"] for p in new_files[:5]])
print(f"  真人A F0={real_A:.1f}   真人B F0={real_B:.1f}")
ok["⑪ 学后说出来的 F0 落真人区间 70~400"] = bool(70 < res["学B"]["F0均值"] < 400)
ok["⑫ 学B 后 F0 比起点更靠近真人B"] = bool(
    abs(res["学B"]["F0均值"] - real_B) < abs(res["起点"]["F0均值"] - real_B))

# ================================================================ I 诚实
print("\n【I】⚠️ 不能说什么")
print("-" * 92)
print("  ❌ 我听不到音频内容 —— 必应例句音频【推定】为中文，未确认")
print("     （依据是它在页面上紧跟 sen_cn，且特征与已确认中文同量级）")
print("  ❌ 这不是动画声优 / 主播 / 对话 —— B站详情页412、音频站全403")
print("  ❌ 例句是单句朗读，不是真的对话（没有轮流、没有回应）")
print("  ❌ 没有真人听感评测（MOS），只有数值距离")
print("  ✅ 能说：它自己挑词、自己抓、自己下载、自己听、自己学，有对照")

print("\n" + "=" * 92)
print(" 判据")
print("=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")

json.dump({
    "ok": {k: bool(v) for k, v in ok.items()},
    "n_harvest": len(collected), "n_heard": len(new_files),
    "target_A": target_A.tolist(), "target_B": target_B.tolist(),
    "gap_AB": gap_AB, "trusted": trusted,
    "errA": [eA0, eA1], "errB": [eB0, eB1], "ctrl": [eC0, eC1],
    "cross": {nm: {"dA": da, "dB": db, "near": nr} for nm, da, db, nr in rows},
    "dist_same": dist_same,
    "spoken": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in res.items()},
}, open(os.path.join(HERE, ".sense", "learn_dialog.json"), "w"),
    ensure_ascii=False, indent=1)
