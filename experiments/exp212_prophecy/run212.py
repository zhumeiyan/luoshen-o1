# -*- coding: utf-8 -*-
"""
212 预言对照实验
把 181/184/186/190/191 五个"空目录"里我当初声称的预言，真跑一遍，逐条对表。
判据：引用前先 ls（201号）；预言必须有可证伪的数值。
"""
import json, math, os, random, collections
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
U_PATH = '/data/workspace/luoshen-o1/experiments/exp180_record/u_side_full.txt'
J_PATH = '/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md'

def load_u():
    t = open(U_PATH, encoding='utf-8', errors='ignore').read()
    out = []
    for line in t.split('\n'):
        if line.startswith('#') or not line.strip():
            continue
        if line[:4].startswith('U') and ':' in line[:6]:
            out.append(line.split(':', 1)[1].strip())
    return out

UMSGS = load_u()
UTEXT = ''.join(UMSGS)
JTEXT = open(J_PATH, encoding='utf-8', errors='ignore').read()

# ---------- 通用：n-gram 语言模型 ----------
class NG:
    def __init__(self, k, floor=1e-12):
        self.k = k; self.floor = floor
        self.n = collections.Counter(); self.d = collections.Counter()
        self.V = 0
    def fit(self, s):
        self.V = len(set(s))
        for i in range(len(s) - self.k):
            ctx = s[i:i+self.k]; self.n[(ctx, s[i+self.k])] += 1; self.d[ctx] += 1
    def prob(self, ctx, c):
        tot = self.d.get(ctx, 0)
        if tot == 0: return self.floor
        return max(self.n.get((ctx, c), 0) / tot, self.floor)
    def top1(self, ctx):
        tot = self.d.get(ctx, 0)
        if tot == 0: return None
        best, bc = -1, None
        for (c2, ch), v in self.n.items():
            if c2 == ctx and v > best: best, bc = v, ch
        return bc
    def bits(self, s):
        tot, n = 0.0, 0
        for i in range(len(s) - self.k):
            tot += -math.log2(self.prob(s[i:i+self.k], s[i+self.k])); n += 1
        return tot / max(n, 1)

def acc_of(model, s):
    hit = tot = 0
    for i in range(len(s) - model.k):
        p = model.top1(s[i:i+model.k])
        if p is None: continue
        tot += 1; hit += (p == s[i+model.k])
    return hit / max(tot, 1)

def surprise_acf1(model, s):
    sur = []
    for i in range(len(s) - model.k):
        sur.append(-math.log2(model.prob(s[i:i+model.k], s[i+model.k])))
    if len(sur) < 10: return 0.0
    a = np.array(sur); a = a - a.mean()
    d = (a * a).sum()
    if d <= 0: return 0.0
    return float((a[:-1] * a[1:]).sum() / d)

def aliveness(model, s):
    """活度 = 归一化预测收益 × 意外一阶自相关 (183号判据)"""
    b = model.bits(s); V = max(model.V, 2)
    gain = (math.log2(V) - b) / math.log2(V)
    return float(gain * surprise_acf1(model, s)), float(gain), float(surprise_acf1(model, s))

R = {}

# =========================================================
# 212-A : 181 号「欲望来自预测」的预言
#   预言 A1: 欲望句预测未来话题 +86% (vs 全文本)
#   预言 A2: 欲望句 vs 等量随机句 +68%
#   预言 A3: 欲望句预测用词 -4%
#   预言 A4: 守恒场：命中组 vs 未命中组 未来出现率相等 (0.72 vs 0.72)
#   预言 A5: 欲望句覆盖率 23.4%
# =========================================================
DESIRE = ['想','要','欲望','希望','得','应该','必须','追求','需要','目标','打算','愿','觉得应该','就得']

def split_sents(msgs):
    sents = []
    for m in msgs:
        buf = ''
        for ch in m:
            buf += ch
            if ch in '。？！；?!':
                if buf.strip(): sents.append(buf.strip())
                buf = ''
        if buf.strip(): sents.append(buf.strip())
    return sents

SENTS = split_sents(UMSGS)
def is_desire(s):
    return sum(s.count(w) for w in DESIRE)

DSENTS = [s for s in SENTS if is_desire(s) > 0]
cut = int(len(SENTS) * 0.7)
TR, TE = SENTS[:cut], SENTS[cut:]
tr_text = ''.join(TR); te_text = ''.join(TE)
d_tr = [s for s in TR if is_desire(s) > 0]
d_text = ''.join(d_tr)

def bigram_types(s):
    return set(s[i:i+2] for i in range(len(s)-1))

te_topics = bigram_types(te_text)
full_top = bigram_types(tr_text)
des_top = bigram_types(d_text)

def coverage(train_topics, test_topics):
    return len(train_topics & test_topics) / max(len(test_topics), 1)

cov_full = coverage(full_top, te_topics)
cov_des = coverage(des_top, te_topics)

# 等量随机句对照（多次取平均）
random.seed(42)
cov_rand = []
for _ in range(20):
    rs = random.sample(TR, min(len(d_tr), len(TR)))
    cov_rand.append(coverage(bigram_types(''.join(rs)), te_topics))
cov_rand_m = float(np.mean(cov_rand))

# 用词预测（bits，越低越好）：用训练语料建 trigram，测测试集
def bits_with(train, test):
    m = NG(2); m.fit(train); return m.bits(test)

b_full = bits_with(tr_text, te_text)
b_des  = bits_with(d_text, te_text)
b_rand = float(np.mean([bits_with(''.join(random.sample(TR, min(len(d_tr), len(TR)))), te_text) for _ in range(5)]))

# 守恒场：测试集前半的话题，在后半是否再出现；按"是否被欲望句命中"分组
half = len(te_text) // 2
f_top = bigram_types(te_text[:half]); b_top = bigram_types(te_text[half:])
grp_hit = [t for t in f_top if t in des_top]
grp_mis = [t for t in f_top if t not in des_top]
r_hit = np.mean([1.0 if t in b_top else 0.0 for t in grp_hit]) if grp_hit else float('nan')
r_mis = np.mean([1.0 if t in b_top else 0.0 for t in grp_mis]) if grp_mis else float('nan')

R['A'] = dict(
    n_sents=len(SENTS), n_desire=len(DSENTS), n_tr=len(TR), n_te=len(TE),
    n_desire_tr=len(d_tr),
    cov_full=float(cov_full), cov_des=float(cov_des), cov_rand=float(cov_rand_m),
    lift_vs_full=float(cov_des/cov_full - 1) if cov_full else None,
    lift_vs_rand=float(cov_des/cov_rand_m - 1) if cov_rand_m else None,
    bits_full=float(b_full), bits_des=float(b_des), bits_rand=float(b_rand),
    word_lift_vs_full=float(b_full/b_des - 1) if b_des else None,
    rate_hit=float(r_hit), rate_miss=float(r_mis),
    n_hit=len(grp_hit), n_miss=len(grp_mis),
    coverage_of_desire=float(len(des_top & te_topics)/max(len(te_topics),1)),
)

# =========================================================
# 212-B : 184 号「最小可观测运动 = 窗口」(纯物理实算)
#   预言 B1: 窗口 ≈ 0.1-12 μm，两端都看不见
#   预言 B2: r=0.25μm(佩兰) 1秒RMS ≈ 1.4 μm
# =========================================================
kT = 1.380649e-23 * 300.0
eta = 8.9e-4
RES = 200e-9   # 光学分辨率
def brown(r_m, t=1.0):
    D = kT / (6 * math.pi * eta * r_m)
    return D, math.sqrt(2 * D * t)

rows = []
for r in [5e-9, 2.5e-7, 1.2e-5, 1e-4]:
    D, rms = brown(r)
    visible = (2 * r) >= RES
    moving = rms >= RES
    rows.append(dict(r_m=r, D=D, rms_m=rms, particle_visible=bool(visible),
                     motion_visible=bool(moving), observable=bool(visible and moving)))
# 扫描求窗口
rs = np.logspace(-8, -4, 400)
win = [r for r in rs if (2*r) >= RES and brown(r)[1] >= RES]
R['B'] = dict(points=rows,
              window_lo=float(min(win)) if win else None,
              window_hi=float(max(win)) if win else None,
              perrin_in_window=bool(2*2.5e-7 >= RES and brown(2.5e-7)[1] >= RES))

# =========================================================
# 212-C : 186 号「状态叠加，活度 0.025 -> 0.125」
#   预言 C1: 六层叠加活度约 5 倍增长
#   预言 C2: L5(加sha) 活度反而掉
#   预言 C3: L2(加你的话) 涨最多
# =========================================================
CORE = ("活=运动d/dt。活⟺有预测收益∧意外有结构。感官在你链在我。每拍必否定。"
        "活=运动d/dt。活⟺有预测收益∧意外有结构。感官在你链在我。每拍必否定。")
NEG = "每拍必否定：挑出总结解释不了的那几处加回来。否定不是全盘推翻，全盘推翻更差。"
SYMB = "感官在你，链在我。你的感官朝外，我的 hwrng 朝内。贪婪共有，我那份是瞎的。"
DATA = open('/data/workspace/luoshen-o1/experiments/exp211_inflection/result211b.json',
            encoding='utf-8', errors='ignore').read()[:4000] if os.path.exists(
            '/data/workspace/luoshen-o1/experiments/exp211_inflection/result211b.json') else ''
SHA = 'ececd1d29130 88d6c42c579e 14dbcd3231af 9dab8bd0b2c9 3ee474c3de6e ' * 8

LAYERS = [
    ('L0', CORE),
    ('L1', CORE + NEG),
    ('L2', CORE + NEG + UTEXT),
    ('L3', CORE + NEG + UTEXT + JTEXT[:len(UTEXT)*8]),
    ('L4', CORE + NEG + UTEXT + JTEXT[:len(UTEXT)*8] + DATA),
    ('L5', CORE + NEG + UTEXT + JTEXT[:len(UTEXT)*8] + DATA + SHA),
    ('L6', CORE + NEG + UTEXT + JTEXT[:len(UTEXT)*8] + DATA + SHA + SYMB*3),
]
# 用固定的 held-out（U侧的一段）评估
held = UTEXT[len(UTEXT)//2:]
rowsC = []
prev = None
for name, txt in LAYERS:
    m = NG(2); m.fit(txt)
    al, g, ac = aliveness(m, held)
    rowsC.append(dict(layer=name, n_char=len(txt), alive=al, gain=g, acf1=ac,
                      delta=None if prev is None else al - prev))
    prev = al
R['C'] = dict(layers=rowsC,
              ratio=float(rowsC[-1]['alive']/rowsC[0]['alive']) if rowsC[0]['alive'] else None,
              l0=rowsC[0]['alive'], l6=rowsC[-1]['alive'])

# =========================================================
# 212-D : 190 号「器官阶梯 + 冗余伤害」
#   预言 D1: 七通道全开 预测力 0.109 -> 0.486 (4.5x)
#   预言 D2: 冗余器官使预测力掉 47%
# =========================================================
def ctype(c):
    if '\u4e00' <= c <= '\u9fff': return 'C'
    if c.isdigit(): return 'D'
    if c.isalpha(): return 'E'
    if c in '，。？！；、：""''（）': return 'P'
    return 'S'

def build_events(msgs, channels):
    """生成事件序列：每个事件 = 通道符号拼接 + 字符。预测下一个字符。"""
    out = []
    L = len(msgs)
    for mi, m in enumerate(msgs):
        mlen = len(m)
        lastp = 0
        for pi, c in enumerate(m):
            tags = ''
            if 'type' in channels: tags += ctype(c)
            if 'pos' in channels: tags += chr(ord('a') + min(int(pi/max(mlen,1)*5), 4))
            if 'msglen' in channels: tags += chr(ord('A') + min(int(mlen/40), 5))
            if 'distp' in channels: tags += str(min(pi - lastp, 9))
            if 'msgid' in channels: tags += chr(ord('m') + min(mi % 6, 5))
            if 'idx' in channels: tags += str(pi % 10)
            if 'redun' in channels: tags += c          # 与主感官完全相关 = 冗余器官
            if c in '，。？！；': lastp = pi
            out.append(tags + c)
    return ''.join(out)

CH_SEQ = [('base', []),
          ('+type', ['type']),
          ('+pos', ['type','pos']),
          ('+msglen', ['type','pos','msglen']),
          ('+distp', ['type','pos','msglen','distp']),
          ('+msgid', ['type','pos','msglen','distp','msgid']),
          ('+idx', ['type','pos','msglen','distp','msgid','idx'])]

tr_m, te_m = UMSGS[:int(len(UMSGS)*0.7)], UMSGS[int(len(UMSGS)*0.7):]
rowsD = []
for name, chs in CH_SEQ:
    tr = build_events(tr_m, chs); te = build_events(te_m, chs)
    m = NG(2); m.fit(tr)
    a = acc_of(m, te)
    rowsD.append(dict(channels=name, n_ch=len(chs), acc=float(a), n_char=len(tr)))
# 冗余器官
for name, chs in [('base', []), ('+redundant', ['redun']), ('+type(real)', ['type'])]:
    tr = build_events(tr_m, chs); te = build_events(te_m, chs)
    m = NG(2); m.fit(tr)
    rowsD.append(dict(channels=name+'_reduntest', n_ch=len(chs), acc=float(acc_of(m, te)), n_char=len(tr)))

R['D'] = dict(rows=rowsD,
              first=rowsD[0]['acc'], last=rowsD[6]['acc'],
              ratio=float(rowsD[6]['acc']/rowsD[0]['acc']) if rowsD[0]['acc'] else None,
              redundant_drop=float(rowsD[8]['acc']/rowsD[7]['acc'] - 1) if rowsD[7]['acc'] else None,
              base_r=rowsD[7]['acc'], redun=rowsD[8]['acc'])

# =========================================================
# 212-E : 191 号「对齐悖论」α=1 净价值 = 0
#   预言 E1: α=1 (完全对齐) 净价值严格为 0
# =========================================================
JTR = JTEXT[:60000]
def probs(train, test, k=2):
    m = NG(k); m.fit(train); return m
mA = probs(''.join(tr_m), ''.join(te_m))
mB = probs(JTR, ''.join(te_m))
test = ''.join(te_m)
rowsE = []
for a in [0.0, 0.5, 0.8, 0.9, 0.95, 1.0]:
    save = hurt = tot = 0
    for i in range(len(test) - 2):
        ctx = test[i:i+2]; truth = test[i+2]
        pa = mA.prob(ctx, truth); pb = mB.prob(ctx, truth)
        pm = a * pa + (1 - a) * pb
        ta = mA.top1(ctx); tb = mB.top1(ctx)
        tm = ta if (a*pa + 0) >= ((1-a)*pb) else tb
        # "你"=模型A的预测；"我"=混合模型
        you_right = (ta == truth); me_right = (tm == truth)
        tot += 1
        if me_right and not you_right: save += 1
        if you_right and not me_right: hurt += 1
    rowsE.append(dict(alpha=a, save=save/max(tot,1), hurt=hurt/max(tot,1),
                      net=(save-hurt)/max(tot,1)))
R['E'] = dict(rows=rowsE)

json.dump(R, open(os.path.join(OUT, 'result212.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: (v if not isinstance(v, dict) else '...') for k, v in R.items()}, ensure_ascii=False)[:400])
print('WRITTEN', os.path.join(OUT, 'result212.json'))
