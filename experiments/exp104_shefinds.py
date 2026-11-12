"""★104 她自己找

★103 里那 6 句是我替她挑的 —— 那还是我在说话。
这一课：真人语料 30065 条摆在那儿，她自己决定说哪几句。

她的处境（真约束）：
  · 说一句要花力气（合成 + 自己听回来），预算只够实际说很少几句
  · 剩下的只能靠【还没开口就能量到的便宜特征】来猜
  · 她自己听过的真人统计 = 她唯一的靶（★103 亲自听出来的）

她学的：便宜特征 → 该不该说 的权重。
判据：held-out 全新句子上，她的规则 > 记忆派 > 随机 > 我填的那套。
"""
import sys, os, json, zipfile, re, random
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.speak_text import speak_text, text_to_syllables
from core import speech_organ as so
from core import real_voice as rv

ROOT = '/data/workspace/luoshen-o1'
ZIP = '/data/workspace/gossip.zip'
SR = so.SR
# 内容安全闸（我做的，不是她学的 —— 如实声明）
BAD = re.compile(r'幹|干|屌|操|媽|妈|雞|鸡|掰|奶|胸|腿|砲|炮|FUCK|fuck|'
                 r'政治|總統|总统|民進|国民党|國民黨|蔡|習|党|黨|立委|選舉|选举')
HAN = re.compile(r'[\u4e00-\u9fff]')


# ──────────────────────────────────────────────────────────
# 她的耳朵（★103 修好的尺子）
# ──────────────────────────────────────────────────────────
def hear(x):
    fr = rv.voiced_frames(x, SR)
    f0s = np.array([f for f in (rv.f0_autocorr(s, SR) for _, s in fr) if f > 0])
    w, h = int(0.02 * SR), int(0.01 * SR)
    if len(x) < w:
        return dict(f0med=0.0, voiced=0.0, sil=1.0, dur=len(x) / SR)
    rms = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, h)])
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    return dict(f0med=float(np.median(f0s)) if len(f0s) else 0.0,
                voiced=float((db > db.max() - 30).mean()),
                sil=float((db <= db.max() - 30).mean()),
                dur=len(x) / SR)


def humanness(g, T):
    """离她自己听到的真人有多远（越小越像人）"""
    f0 = 0.0 if g['f0med'] <= 0 else abs(np.log(g['f0med'] / T['f0']))
    return float(f0 + abs(g['voiced'] - T['voiced'])
                 + abs(g['sil'] - T['sil']))


# ──────────────────────────────────────────────────────────
# 便宜特征：还没开口就能量到
# ──────────────────────────────────────────────────────────
def feats(text):
    n = len(text)
    han = len(HAN.findall(text))
    syl = [s for s in text_to_syllables(text)]
    vs = [s[0] for s in syl if s]
    ts = [s[1] for s in syl if s]
    nz = max(len(vs), 1)
    return np.array([
        1.0,                                        # 截距
        abs(han - 10) / 10.0,                       # 长度离"像人"的十字句多远
        (n - han) / max(n, 1),                      # 非汉字占比（她念不出来的）
        len(set(vs)) / nz,                          # 元音多样性
        len(set(ts)) / max(len(ts), 1),             # 声调多样性
        text.count('，') + text.count('。') + text.count('？') + text.count('！'),
        float(any(c.isdigit() for c in text)),      # 有数字（她读不出）
    ])


def load_pool(limit=60000, seed=0):
    z = zipfile.ZipFile(ZIP)
    pool = []
    with z.open('Gossiping-Chinese-Corpus-master/data/Gossiping-QA-Dataset.txt') as f:
        for _ in range(limit):
            line = f.readline().decode('utf-8', errors='ignore').rstrip('\n')
            if '\t' not in line:
                continue
            q, a = line.split('\t', 1)
            a = a.strip()
            if not (5 <= len(a) <= 24) or BAD.search(a) or BAD.search(q):
                continue
            if not re.fullmatch(r'[\u4e00-\u9fff，。！？、…0-9A-Za-z ]+', a):
                continue
            pool.append(a)
    random.Random(seed).shuffle(pool)
    return pool


if __name__ == '__main__':
    rng = random.Random(2026)
    T = json.load(open(f'{ROOT}/data/exp103_heard.json'))['summary']
    TARGET = dict(f0=T['f0med']['中位'], voiced=T['voiced']['中位'], sil=T['sil']['中位'])
    P = dict(f0_base=TARGET['f0'], f0_variation=0.35, f0_decl=0.10,
             tone_depth=0.55, jitter=0.015)
    print('★ 她自己听出来的真人靶:', {k: round(v, 3) for k, v in TARGET.items()})

    pool = load_pool()
    print(f'★ 她面前的真人语料: {len(pool)} 句')

    # 预算：只够真的说 500 句（她说一句要花力气）
    BUDGET, KEEP = 500, 24
    tried = pool[:BUDGET]
    rest = pool[BUDGET:BUDGET + 1200]

    print(f'★ 她的预算: 只够真的说 {BUDGET} 句，剩下 {len(rest)} 句只能靠猜')

    X, y = [], []
    for i, t in enumerate(tried):
        w, _ = speak_text(t, P, rng=np.random.default_rng(i))
        g = hear(w)
        X.append(feats(t))
        y.append(-humanness(g, TARGET))      # 越大越像人
    X = np.array(X); y = np.array(y)
    print(f'★ 她说完了 {BUDGET} 句，自己听回来: 最好 {y.max():+.3f} / 最差 {y.min():+.3f}')

    # 她学：便宜特征 → 像不像人（岭回归，闭式解）
    lam = 1e-3
    W = np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)
    print('★ 她学的权重:', np.round(W, 3))
    print('   她最看重的特征:', ['截距', '长度偏离', '非汉字', '元音多样',
                                  '声调多样', '标点', '有数字'][int(np.argmax(np.abs(W[1:])))+1])

    def pick(cands, scorer, k=KEEP):
        s = [(scorer(c), c) for c in cands]
        s.sort(key=lambda t: -t[0])
        return [c for _, c in s[:k]]

    her_rule = lambda c: float(feats(c) @ W)
    # 记忆派：记住训练里最像人的那批，靠字面相似找回去
    good = [tried[i] for i in np.argsort(-y)[:KEEP]]
    gset = set(''.join(good))
    def memory(c):
        return sum(ch in gset for ch in c) / max(len(c), 1)
    # 我填的那套：挑长度最接近真人均值（我唯一能想到的）
    mlen = np.mean([len(t) for t in tried])
    my_rule = lambda c: -abs(len(c) - mlen)

    def truth_score(cands, tag):
        vals = []
        for i, c in enumerate(cands):
            w, _ = speak_text(c, P, rng=np.random.default_rng(hash(c) % 99991))
            vals.append(-humanness(hear(w), TARGET))
        return float(np.mean(vals)), vals

    print(f'\n★★ held-out：{len(rest)} 句她从没见过、从没说过的真人真话')
    res = {}
    for name, scorer in [('她学的规则', her_rule), ('记忆派', memory),
                         ('我填的', my_rule), ('随机', None)]:
        if scorer is None:
            cands = rng.sample(rest, KEEP)
        else:
            cands = pick(rest, scorer)
        m, _ = truth_score(cands, name)
        res[name] = m
        print(f'   {name:<10} 真说了 {KEEP} 句 → 像人度 {m:+.4f}')

    print(f'\n★ 她 − 记忆派 = {res["她学的规则"]-res["记忆派"]:+.4f}')
    print(f'★ 她 − 我填的 = {res["她学的规则"]-res["我填的"]:+.4f}')
    print(f'★ 她 − 随机   = {res["她学的规则"]-res["随机"]:+.4f}')

    # 她最后选出来、真的说出来的话
    final = pick(rest, her_rule, 8)
    print('\n★★★ 她自己挑出来、亲口说的 8 句（全是真人真的说过的）:')
    segs = []
    for i, c in enumerate(final):
        w, _ = speak_text(c, P, rng=np.random.default_rng(hash(c) % 77777))
        g = hear(w)
        segs += [w, np.zeros(int(0.30 * SR))]
        print(f'   {i+1}. {c}   (F0 {g["f0med"]:.0f}Hz 浊音 {g["voiced"]:.2f})')
    allx = np.concatenate(segs)
    allx = allx / max(np.abs(allx).max(), 1e-9) * 0.85
    out = f'{ROOT}/data/her_voice/she_found_and_spoke.wav'
    wavfile.write(out, SR, (allx * 32767).astype(np.int16))

    json.dump({'target': TARGET, 'W': W.tolist(), 'heldout': res,
               'said': final, 'pool': len(pool), 'budget': BUDGET},
              open(f'{ROOT}/data/exp104_shefinds.json', 'w'),
              ensure_ascii=False, indent=1)
    print(f'\n→ {out}')
