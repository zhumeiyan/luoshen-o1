"""★107 正常交流 —— 多轮来回（conversational loop）

★105 她会从真人语料里挑出适合自己说的话。
★106 她会向对方靠几个 Hz。
但那都还是【挑一句说 / 接一句】，不是【说话】。

这一课：真的来回。
  对方说一句（真人真的说过的话）→ 她听到 → 她等（不抢话）→ 她挑一句【回应那句话】的
  → 她靠几个 Hz 说出来 → 下一轮。

───────────────────────────────────────────────────────────
真值来源（没有一条是我编的）
───────────────────────────────────────────────────────────
· 语料：PTT 八卦版 QA（Gossiping-QA-Dataset.txt）
    每行 `问题 \t 回答` —— 问题是真人说的上一句，回答是真人真的回的那一句。
    ★ 这就是【真人的对话对】，不是我配的。
· 韵律靶：★103 她亲自听 35 段真人语音测出来的
    f0 179.8 / voiced 0.674 / sil 0.326
· 顺应：★106 文献倒 U（NT 组收敛 4 Hz），稳健解 A=8（+4.0 Hz）
· 话轮间隔 FTO：Stivers et al. 众数 0~200ms、舒适 ~150ms、重叠率约 5%
    → 反推预测误差尺度 σ_pred ≈ 0.09 s（见 SIGMA_PRED 推导）
· 句内停顿：★103 实测 pausemed 中位 0.06 s

───────────────────────────────────────────────────────────
她学的三个旋钮
───────────────────────────────────────────────────────────
  w   回应性权重：多看重"这句是不是在回对方"，多看重"这句我说不说得漂亮"
  pi  剪多窄：预算只够真说几句，剪得窄才测得深（★105 的赢家诅咒解药）
  g   话轮间隔：等多久才开口（太小 → 抢话；太大 → 冷场）
"""
import sys, os, json, re, random, zipfile
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.speak_text import speak_text, text_to_syllables
from core import speech_organ as so
from core import entrainment as EN
import experiments.exp104_shefinds as E

ROOT = '/data/workspace/luoshen-o1'
SR = so.SR
ZIP = '/data/workspace/gossip.zip'
QA = 'Gossiping-Chinese-Corpus-master/data/Gossiping-QA-Dataset.txt'
BAD = E.BAD
HAN = E.HAN

# ── 真人靶（★103 她自己听出来的） ─────────────────────────
_H = json.load(open(f'{ROOT}/data/exp103_heard.json'))
_S = _H['summary']
TARGET = dict(f0=_S['f0med']['中位'], voiced=_S['voiced']['中位'], sil=_S['sil']['中位'])
TRUE_F0S = np.array([p['f0med'] for p in _H['per_file']])

# ── 她自己（★106 实测） ───────────────────────────────────
SELF_F0 = EN.SELF_F0              # 182.5 听到的基线
SELF_F0_PARAM = EN.SELF_F0_PARAM  # 181.8 她设的值
SELF_WPM = EN.SELF_WPM            # 223
WPM_RATIO = EN.WPM_RATIO          # 0.669
SHARED_F0 = EN.SHARED_F0          # 6.0 共同起伏
OBS_F0, OBS_RT = EN.OBS_F0, EN.OBS_RT
CONV_TARGET, CONV_SIGMA = EN.CONV_TARGET, EN.CONV_SIGMA

# ── 话轮：FTO 与预测误差 ──────────────────────────────────
FTO_LO, FTO_HI = 0.0, 0.25        # 舒适区间（文献）：0~250ms，众数 ~150ms
# 文献：自然对话重叠率约 5%。若她瞄准间隔 g，抢话概率 = Φ(-g/σ)。
# 取 g=0.15（众数）时 P(抢话)=5% → σ = 0.15/1.645 ≈ 0.09 s。
SIGMA_PRED = 0.0912
OVERLAP_PENALTY = 3.0             # 抢一次话的代价（远大于冷场）

REL_W = 0.5                       # 真值里"回应上真人实际回的那一句"占多大分量


# ═══════════════════════════════════════════════════════════
# 语料：真人对话对（问题=上一句，回答=真人真的回的那一句）
# ═══════════════════════════════════════════════════════════
def load_pairs(limit=60000, seed=0):
    z = zipfile.ZipFile(ZIP)
    pairs, all_a = [], []
    with z.open(QA) as f:
        for _ in range(limit):
            line = f.readline().decode('utf-8', errors='ignore').rstrip('\n')
            if '\t' not in line:
                continue
            q, a = line.split('\t', 1)
            q, a = q.strip(), a.strip()
            if not (4 <= len(a) <= 22) or not (4 <= len(q) <= 60):
                continue
            if BAD.search(a) or BAD.search(q):
                continue
            if not re.fullmatch(r'[\u4e00-\u9fff，。！？、…0-9A-Za-z ]+', a):
                continue
            if not re.fullmatch(r'[\u4e00-\u9fff，。！？、…0-9A-Za-z ]+', q):
                continue
            pairs.append((q, a))
            all_a.append(a)
    random.Random(seed).shuffle(pairs)
    return pairs, all_a


# ═══════════════════════════════════════════════════════════
# 回应性：字符二元组余弦（context ↔ candidate）
# ═══════════════════════════════════════════════════════════
def _bg(s):
    s = ''.join(HAN.findall(s))
    return set(s[i:i + 2] for i in range(len(s) - 1)) or {s}


def rel_proxy(cand, ctx):
    """便宜代理：这句跟对方刚说的那句，字面上有多接得上（还没开口就能量）"""
    A, B = _bg(cand), _bg(ctx)
    return len(A & B) / max(np.sqrt(len(A) * len(B)), 1e-9)


def rel_truth(cand, gold):
    """★真值：她挑的这句，跟【真人当时真的回的那一句】有多像。
    金标准就是语料里那个 a —— 不是我编的。"""
    A, B = _bg(cand), _bg(gold)
    return len(A & B) / max(np.sqrt(len(A) * len(B)), 1e-9)


# ═══════════════════════════════════════════════════════════
# 韵律：说一句，自己听回来，离真人靶多远
# ═══════════════════════════════════════════════════════════
def prosody(text, params, rng, syl_dur=0.18, repeats=1):
    """返回 (-humanness, 波形)；repeats>1 时对多次发声取平均（★105：一遍有 21% 抖动）"""
    vals, last = [], None
    for _ in range(repeats):
        w, _ = speak_text(text, params, rng=rng, syl_dur=syl_dur, pause_dur=0.12)
        vals.append(-E.humanness(E.hear(w), TARGET))
        last = w
    return float(np.mean(vals)), last


def _params_for(f0, wpm_target):
    return dict(f0_base=float(f0), f0_variation=0.35, f0_decl=0.10,
                tone_depth=0.55, jitter=0.015)


def _syl_for(wpm_target):
    return float(np.clip(WPM_RATIO * 60.0 / max(wpm_target, 60.0), 0.10, 0.60))


# ═══════════════════════════════════════════════════════════
# 便宜模型：还没开口就能猜这句说不说得漂亮（★104/★105 她已学过）
# ═══════════════════════════════════════════════════════════
def learn_hum_model(pairs, n=300, seed=0, cache=f'{ROOT}/data/exp107_humW.json'):
    if os.path.exists(cache):
        return np.array(json.load(open(cache)))
    rng = np.random.default_rng(seed)
    texts = [a for _, a in pairs[:n]]
    P = _params_for(TARGET['f0'], 165.0)
    X, y = [], []
    for i, t in enumerate(texts):
        v, _ = prosody(t, P, np.random.default_rng(i))
        X.append(E.feats(t)); y.append(v)
    X, y = np.array(X), np.array(y)
    W = np.linalg.solve(X.T @ X + 1e-3 * np.eye(X.shape[1]), X.T @ y)
    json.dump(W.tolist(), open(cache, 'w'))
    return W


# ═══════════════════════════════════════════════════════════
# 一句话的完整一轮
# ═══════════════════════════════════════════════════════════
def one_turn(ctx, gold, cands, W, w, pi, g, partner, hist, rng,
             A=8.0, lam=0.8, B=0.8, r=2, shuffle_ctx=False, rand_rel=False,
             cands_n=12):
    """返回 (本轮真值, 记录dict, 她说的波形, 对方说的文本)"""
    # ① 对方这一轮（含共同起伏）
    c = float(rng.normal(0.0, SHARED_F0))
    o = EN.observe(partner, rng)
    o['f0'] += c
    hist.append(o)
    e = EN.estimate(hist, 4)

    # ② 顺应：整段移动 A（封顶）+ 逐轮跟随 λ
    gap = e['f0'] - SELF_F0
    move = np.sign(gap) * min(A, abs(gap))
    dev = hist[-1]['f0'] - e['f0']
    tgt_f0 = SELF_F0_PARAM + move + lam * dev
    tgt_wpm = float(np.clip(SELF_WPM + B * (e['wpm'] - SELF_WPM), 90.0, 340.0))
    P = _params_for(tgt_f0, tgt_wpm)
    syl = _syl_for(tgt_wpm)

    # ③ 候选：真人真的回的那一句 + 别的真人的回答
    cset = [gold] + [x for x in cands if x != gold]
    cset = cset[:cands_n]
    if shuffle_ctx:
        ctx_for_rel = rng.choice(cands)          # 打碎"上一句↔回应"的对应
    else:
        ctx_for_rel = ctx

    rp = np.array([(rng.random() if rand_rel else rel_proxy(x, ctx_for_rel))
                   for x in cset])
    hc = np.array([float(E.feats(x) @ W) for x in cset])
    cheap = w * rp + (1.0 - w) * hc

    # ④ 剪：只留头部，省下的预算用来多说几遍（★105 π）
    k = max(1, int(round(pi * len(cset))))
    order = np.argsort(-cheap)[:k]
    meas = np.array([prosody(cset[i], P, rng, syl_dur=syl, repeats=r)[0]
                     for i in order])

    # ⑤ 定：回应性（便宜猜的）+ 说不说得漂亮（真开口量到的）
    comb = w * rp[order] + (1.0 - w) * meas
    best = int(order[int(np.argmax(comb))])
    chosen = cset[best]

    # ⑥ 真的说出来（这一句就是这一轮她说的话）
    pro, wav = prosody(chosen, P, rng, syl_dur=syl, repeats=1)

    # ⑦ 话轮：抢话 / 冷场（真值：FTO 舒适 0~250ms）
    pred_err = float(rng.normal(0.0, SIGMA_PRED))
    gap_actual = g + pred_err
    pen = 0.0
    if gap_actual < 0:
        pen += OVERLAP_PENALTY * min(1.0, -gap_actual / 0.10)   # 抢话
    elif gap_actual > FTO_HI:
        pen += (gap_actual - FTO_HI) * 1.0                      # 冷场

    relt = rel_truth(chosen, gold)
    truth = pro + REL_W * relt - pen
    return truth, dict(pro=pro, rel=relt, gap=gap_actual, pen=pen,
                       chosen=chosen, gold=gold, ctx=ctx,
                       hit=1.0 if chosen == gold else 0.0,
                       tgt_f0=tgt_f0), wav


def converse(w, pi, g, pairs, partner, rng, turns=5, W=None, all_a=None,
             A=8.0, lam=0.8, B=0.8, r=2, cands_n=12, **kw):
    W = learn_hum_model(pairs) if W is None else W
    if all_a is None:
        all_a = [a for _, a in pairs]
    hist, tr, recs, wavs = [], [], [], []
    for t in range(turns):
        ctx, gold = pairs[t % len(pairs)]
        cands = [gold] + [all_a[int(rng.integers(0, len(all_a)))]
                          for _ in range(cands_n - 1)]
        v, rec, wv = one_turn(ctx, gold, cands, W, w, pi, g, partner, hist, rng,
                              A=A, lam=lam, B=B, r=r, cands_n=cands_n, **kw)
        tr.append(v); recs.append(rec); wavs.append(wv)
    return float(np.mean(tr)), recs, wavs


def score(w, pi, g, pairs, seeds, pool=None, turns=5, W=None,
          A=8.0, r=2, cands_n=12, **kw):
    """★102 教训：公共随机数 —— 不同参数必须用同一批对话"""
    W = learn_hum_model(pairs) if W is None else W
    all_a = [a for _, a in pairs]
    out = []
    for sd in seeds:
        rng = np.random.default_rng(sd)
        p = EN.make_partner(rng, pool)
        # 每个种子抽一组【不同的】真人对话当这一轮的脚本（否则所有参数都在同一批上下文上比）
        idx = rng.choice(len(pairs), turns, replace=False)
        script = [pairs[int(i)] for i in idx]
        v, _, _ = converse(w, pi, g, script, p, rng, turns=turns, W=W,
                           all_a=all_a, A=A, r=r, cands_n=cands_n, **kw)
        out.append(v)
    return float(np.mean(out))
