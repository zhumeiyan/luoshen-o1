"""
Saffran 统计学习范式（统计学习 = 前语言阶段的切词机制）

不是我编的模型，是领域标准范式：
  Saffran, Aslin & Newport (1996) —— 8月龄婴儿靠音节间的转移概率，
  在没有空格的连续语流里切出词。

流的设计（照 Saffran）：
  12 个音节 → 4 个三音节"词"，音节不重复
  词内  TP = 1.00   （位置1→2、2→3 完全确定）
  词边界 TP = 1/3   （位置3→下一词位置1，4选1）
  连续播放，无边界标记

测验项：
  word      完整词        TP 全程高
  part-word 跨界串        含一个低 TP 的边界 bigram
  non-word  同音节乱序    频次与 word 完全相同，只有顺序不同
             ↑ 这个控制项是关键：如果只靠"哪个音节常见"，
               word 和 non-word 得分会一样
"""
import sys, os, json, re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_PY = os.path.join(ROOT, '.pylibs')
if _PY not in sys.path:
    sys.path.insert(0, _PY)


# ────────────────────────────────────────────
# 1. 真实音节：从 KdConv 三个领域统计（REAL）
# ────────────────────────────────────────────
def real_syllables(topk=200, domains=('film', 'music', 'travel')):
    """从真人对话里统计真实汉字的无调拼音频次。REAL。"""
    try:
        from pypinyin import lazy_pinyin, Style
    except ImportError:
        os.system('pip install -q --target=' + _PY + ' pypinyin')
        from pypinyin import lazy_pinyin, Style

    from collections import Counter
    c = Counter()
    n_chars = 0
    for dom in domains:
        p = f'/data/workspace/kdconv/{dom}_train.json'
        if not os.path.exists(p):
            continue
        for dlg in json.load(open(p)):
            for m in dlg.get('messages', dlg.get('dialog', [])):
                msg = m.get('message', '')
                han = re.findall(r'[\u4e00-\u9fff]', msg)
                n_chars += len(han)
                if han:
                    for s in lazy_pinyin(''.join(han), style=Style.NORMAL):
                        if s and re.fullmatch(r'[a-z]+', s):
                            c[s] += 1
    return [s for s, _ in c.most_common(topk)], n_chars, c


# ────────────────────────────────────────────
# 2. 流的构造
# ────────────────────────────────────────────
def make_words(syls, n_word=4, wlen=3, rng=None):
    """12 音节 → 4 个三音节词，音节不重复（Saffran 式）"""
    rng = rng or np.random.default_rng(0)
    need = n_word * wlen
    pool = list(syls[:max(need, len(syls))])
    rng.shuffle(pool)
    pool = pool[:need]
    return [tuple(pool[i * wlen:(i + 1) * wlen]) for i in range(n_word)]


def make_stream(words, n_rep, rng=None):
    """随机排列词，串成连续流（无边界标记）"""
    rng = rng or np.random.default_rng(1)
    seq = []
    for _ in range(n_rep):
        order = rng.permutation(len(words))
        for o in order:
            seq.extend(words[o])
    return seq


def measure_tp(seq, words):
    """实测流的 TP 结构（REAL 验证，不是假设）"""
    wset = {w: i for i, w in enumerate(words)}
    L = len(words[0])
    inside, boundary = [], []
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        # 判断是否跨越词边界：a 在词内的位置
        pos_a = None
        for w in words:
            if a in w:
                # 同一音节在不同词里位置相同（构造保证不重复音节）
                pos_a = w.index(a)
                break
        if pos_a is not None and pos_a < L - 1:
            # 词内转移：b 必须是同一词的下一个音节
            for w in words:
                if a in w and pos_a + 1 < L and w[pos_a + 1] == b:
                    inside.append(1.0)
                    break
            else:
                inside.append(0.0)
        else:
            boundary.append(1.0 if any(
                w[0] == b and w != next((x for x in words if a in x), None)
                for w in words) else 0.0)
    return (float(np.mean(inside)) if inside else 0.0,
            float(np.mean(boundary)) if boundary else 0.0)


# ────────────────────────────────────────────
# 3. 测验项
# ────────────────────────────────────────────
def test_items(words, rng=None):
    """生成 word / part-word / non-word 三类测验串"""
    rng = rng or np.random.default_rng(2)
    L = len(words[0])
    nw = len(words)

    words_l = [list(w) for w in words]

    # part-word：跨界串（词A 后 k 个 + 词B 前 L-k 个）
    parts = []
    for i in range(nw):
        for j in range(nw):
            if i == j:
                continue
            for k in (1, 2):
                parts.append(words_l[i][L - k:] + words_l[j][:k])

    # non-word：与某个 word 用完全相同的音节，只换顺序（频次控制）
    # 且保证它不等于任何 word，也不等于任何 part-word
    partset = {tuple(p) for p in parts}
    nonwords = []
    for w in words_l:
        for _ in range(60):
            c = list(w)
            rng.shuffle(c)
            t = tuple(c)
            if t not in wset_of(words) and t not in partset:
                nonwords.append(list(t))
                break
    return words_l, parts, nonwords


def wset_of(words):
    return {tuple(w) for w in words}


# ────────────────────────────────────────────
# 4. 她：统计学习器
# ────────────────────────────────────────────
class Learner:
    """
    她。两个旋钮都是真实的权衡：
      alpha 平滑先验   太小→小样本噪声大；太大→抹平真实差异
      W    记忆窗口    太短→统计不准；太长→流结构换了适应慢
    """

    def __init__(self, alpha=0.5, W=None):
        self.alpha = float(alpha)
        self.W = W

    def fit(self, seq):
        self.counts = {}
        self.hist = []
        for a, b in zip(seq[:-1], seq[1:]):
            self.counts.setdefault(a, {}).setdefault(b, 0.0)
            self.counts[a][b] += 1.0
            self.hist.append((a, b))
        if self.W:
            self.hist = self.hist[-int(self.W):]
            self.counts = {}
            for a, b in self.hist:
                self.counts.setdefault(a, {}).setdefault(b, 0.0)
                self.counts[a][b] += 1.0
        return self

    def _p(self, a, b):
        d = self.counts.get(a, {})
        tot = sum(d.values()) + self.alpha * max(len(d), 1)
        return (d.get(b, 0.0) + self.alpha) / (tot if tot > 0 else 1.0)

    def score(self, seq):
        """串的得分 = 内部 bigram 转移概率的几何平均"""
        if len(seq) < 2:
            return 0.0
        lp = [np.log(self._p(a, b) + 1e-12) for a, b in zip(seq[:-1], seq[1:])]
        return float(np.exp(np.mean(lp)))
