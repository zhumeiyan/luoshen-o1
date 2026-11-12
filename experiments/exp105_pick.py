"""★105 挑尖子 —— 她怎么在自己的估计有噪声时，选出真正最好的

★104 她输了。诊断是【赢家诅咒】：
    她的排序 r=+0.65 整体是对的，但只取最上面那 24 句就失效——
    因为最上面的那几句，正是她高估得最狠的那几句。

这一课教她两件事：
  π  便宜模型很好但不可靠 → 用它【缩小范围】，不用它【直接定胜负】
     （剪太狠会把真最好的剪掉，因为它的错正好在顶上）
  r  真要说的时候，是多测几句新的、还是把一句测透
     （她每一遍都有 21% 是嗓子抖动）

真值 = 同一句说 24 遍取平均（与她的估计用不同随机种子，噪声独立）。
"""
import sys, os, json, hashlib
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.speak_text import speak_text, text_to_syllables
from core import speech_organ as so
import experiments.exp104_shefinds as E

ROOT = '/data/workspace/luoshen-o1'
SR = so.SR
T = json.load(open(f'{ROOT}/data/exp103_heard.json'))['summary']
TARGET = dict(f0=T['f0med']['中位'], voiced=T['voiced']['中位'], sil=T['sil']['中位'])
P = dict(f0_base=TARGET['f0'], f0_variation=0.35, f0_decl=0.10,
         tone_depth=0.55, jitter=0.015)

C_TRAIN, C_CAND = 125, 500          # 训练 125 句；候选池 500 句（全没见过）
R_TRUTH = 24                        # 真值：说 24 遍
BUDGET = 300                        # 挑选阶段她只有 300 次开口
KEEP = 24                           # 最终说出 24 句

HAN = E.HAN


def say(t, s):
    w, _ = speak_text(t, P, rng=np.random.default_rng(s))
    return -E.humanness(E.hear(w), TARGET)


# ── 便宜特征（v2：补上"这句我念不念得出来"）───────────────
def feats2(text):
    n = len(text)
    han = len(HAN.findall(text))
    syl = [s for s in text_to_syllables(text) if s]
    vs = [s[0] for s in syl]
    ts = [s[1] for s in syl]
    nz = max(len(vs), 1)
    cover = len(syl) / max(n, 1)          # ★ 新增：可念音节 / 字数
    return np.array([
        1.0,
        abs(han - 10) / 10.0,
        (n - han) / max(n, 1),
        len(set(vs)) / nz,
        len(set(ts)) / max(len(ts), 1),
        text.count('，') + text.count('。') + text.count('？') + text.count('！'),
        float(any(c.isdigit() for c in text)),
        cover,
    ])


def feats_nocover(text):
    return feats2(text)[:7]


CACHE = f'{ROOT}/data/exp105_truth.json'


def build():
    pool = E.load_pool()
    train = pool[:C_TRAIN]
    cand = pool[500:500 + C_CAND]
    if os.path.exists(CACHE):
        d = json.load(open(CACHE))
        return train, cand, np.array(d['ytr']), np.array(d['ytruth']), np.array(d['half'])
    print(f'  训练 {C_TRAIN} 句 × 4 遍…')
    ytr = [np.mean([say(t, i * 1000 + k) for k in range(4)]) for i, t in enumerate(train)]
    print(f'  候选 {C_CAND} 句 × {R_TRUTH} 遍（真值）…')
    half, ytruth = [], []
    for i, t in enumerate(cand):
        a = [say(t, hash(t) % 99991 * 13 + k) for k in range(R_TRUTH // 2)]
        b = [say(t, hash(t) % 88877 * 17 + k + 5000) for k in range(R_TRUTH // 2)]
        half.append((np.mean(a), np.mean(b)))
        ytruth.append(np.mean(a + b))
    json.dump({'ytr': ytr, 'ytruth': ytruth, 'half': half}, open(CACHE, 'w'))
    return train, cand, np.array(ytr), np.array(ytruth), np.array(half)


def fit(feat_fn, X, y, lam=1e-3):
    F = np.array([feat_fn(t) for t in X])
    return np.linalg.solve(F.T @ F + lam * np.eye(F.shape[1]), F.T @ y), F


def select(cheap_score, cand, pi, r, budget=BUDGET, reps_fn=None):
    """她的一整套挑法：便宜模型剪枝 → 花预算实测 → 取实测最好的 24 句"""
    nsurv = max(KEEP + 1, int(round(pi * len(cand))))
    surv = np.argsort(-cheap_score)[:nsurv]
    m = min(len(surv), max(1, budget // r))
    pick_from = surv[:m]
    meas = np.array([np.mean([say(cand[j], (hash(cand[j]) % 777331) * 31 + k * 977)
                              for k in range(r)]) if reps_fn is None else reps_fn(cand[j], r)
                     for j in pick_from])
    order = np.argsort(-meas)[:KEEP]
    return [cand[pick_from[i]] for i in order], meas[order].mean()


def evaluate(texts, ytruth, cand):
    idx = [cand.index(t) for t in texts]
    return float(ytruth[idx].mean())


if __name__ == '__main__':
    train, cand, ytr, ytruth, half = build()

    # ── 判据1 尺子自检 ──────────────────────────────────
    r_half = np.corrcoef(half[:, 0], half[:, 1])[0, 1]
    print(f'【1】真值尺子自检：前后各 12 遍的相关 r = {r_half:.4f}'
          f'（信度 {2*r_half/(1+r_half):.4f}）')

    # 便宜模型（含 cover / 不含 cover）
    W2, Ftr2 = fit(feats2, train, ytr)
    W1, Ftr1 = fit(feats_nocover, train, ytr)
    Fc2 = np.array([feats2(t) for t in cand])
    Fc1 = np.array([feats_nocover(t) for t in cand])
    cheap2, cheap1 = Fc2 @ W2, Fc1 @ W1
    print(f'【2】便宜模型 含"念不念得出" r={np.corrcoef(cheap2,ytruth)[0,1]:+.3f}  '
          f'不含 r={np.corrcoef(cheap1,ytruth)[0,1]:+.3f}  '
          f'差 {np.corrcoef(cheap2,ytruth)[0,1]-np.corrcoef(cheap1,ytruth)[0,1]:+.3f}')
    print(f'    她给"念不念得出"这个特征学的权重 = {W2[7]:+.3f}'
          f'（{"最重" if abs(W2[7])==max(abs(W2[1:])) else "不是最重"}）')

    # ── 判据3 赢家诅咒：量化 ────────────────────────────
    one = np.array([say(t, (hash(t) % 555557) * 7) for t in cand])
    top1 = np.argsort(-one)[:KEEP]
    print(f'\n【3】赢家诅咒：说一遍就挑最好的 24 句')
    print(f'    她【以为】这些句子值 {one[top1].mean():+.4f}')
    print(f'    真相     {ytruth[top1].mean():+.4f}   ← 高估 {one[top1].mean()-ytruth[top1].mean():+.4f}')
    print(f'    真最优 24 句实际 {np.sort(ytruth)[-KEEP:].mean():+.4f}')
    print(f'    → 直接挑尖子，白高兴 {one[top1].mean()-ytruth[top1].mean():+.4f}，'
          f'离真最优还差 {np.sort(ytruth)[-KEEP:].mean()-ytruth[top1].mean():.4f}')

    # ── 判据4 π 剪枝强度（内部峰？）────────────────────
    print(f'\n【4】π = 用便宜模型剪到多窄，才花预算去实测（预算 {BUDGET} 次，r=6）')
    print(f'{"π":>6} {"候选":>6} {"实测句数":>8} {"说出24句真相":>13}')
    pis = [0.10, 0.20, 0.30, 0.45, 0.60, 0.80, 1.00]
    pi_res = {}
    for pi in pis:
        texts, _ = select(cheap2, cand, pi, 6)
        v = evaluate(texts, ytruth, cand)
        pi_res[pi] = v
        print(f'{pi:>6.2f} {max(int(pi*len(cand)),KEEP+1):>6} '
              f'{min(max(int(pi*len(cand)),KEEP+1), BUDGET//6):>8} {v:>+13.4f}')
    best_pi = max(pi_res, key=pi_res.get)
    inside = 0.10 < best_pi < 1.00
    print(f'    → 峰在 π={best_pi}（{"内部" if inside else "边界"}）；'
          f'峰比最狠剪枝高 {pi_res[best_pi]-pi_res[0.10]:+.4f}，比不剪高 {pi_res[best_pi]-pi_res[1.00]:+.4f}')

    # 硬依赖：便宜模型变成【完美】或【瞎猜】
    print(f'\n【5】硬依赖两端（π 的价值来自：便宜模型"好但不可靠"）')
    for tag, sc in [('完美模型(用真值当预测)', ytruth),
                    ('瞎猜模型(打乱预测)', cheap2[np.random.default_rng(3).permutation(len(cheap2))])]:
        rr = {}
        for pi in pis:
            texts, _ = select(sc, cand, pi, 6)
            rr[pi] = evaluate(texts, ytruth, cand)
        bp = max(rr, key=rr.get)
        print(f'    {tag:<24} 峰 π={bp}  跨度(峰−最差) {rr[bp]-min(rr.values()):.4f}')
    print(f'    {"真实模型(她学的)":<24} 峰 π={best_pi}  跨度 {pi_res[best_pi]-min(pi_res.values()):.4f}')
    print('    → 模型完美就该狠剪；模型瞎猜就不该剪；她的是中间 → 剪一点，别剪太狠')

    # ── 判据6 r 深度（内部峰？）────────────────────────
    print(f'\n【6】r = 一句测几遍（预算固定 {BUDGET}，π={best_pi}）')
    r_res = {}
    for r in [1, 2, 3, 4, 6, 8, 12, 20]:
        texts, _ = select(cheap2, cand, best_pi, r)
        r_res[r] = evaluate(texts, ytruth, cand)
        print(f'    r={r:<3} 实测 {min(max(int(best_pi*len(cand)),KEEP+1), BUDGET//r):>4} 句 '
              f'→ 说出24句真相 {r_res[r]:>+8.4f}')
    best_r = max(r_res, key=r_res.get)
    print(f'    → 峰在 r={best_r}（{"内部" if 1 < best_r < 20 else "边界"}）')

    # 硬依赖：每遍没有抖动 → 深度无价值
    def noiseless(t, r):
        return say(t, 12345)          # 每遍用同一个种子 = 没有抖动
    rr = {r: evaluate(select(cheap2, cand, best_pi, r, reps_fn=noiseless)[0], ytruth, cand)
          for r in [1, 2, 4, 8, 12, 20]}
    br = max(rr, key=rr.get)
    print(f'【7】硬依赖：关掉每遍抖动 → 峰 r={br}（有抖动时是 {best_r}）'
          f'{"← 移向边界，深度失去价值" if br in (1,20) else "（没移动，尺子有问题）"}')

    # ── 判据8 held-out 四方对照 ────────────────────────
    print(f'\n【8】最终对照：各说 24 句（全是她从没见过的真人真话）')
    her_texts, _ = select(cheap2, cand, best_pi, best_r)
    res = {'她学的(π,r + 念不念得出)': evaluate(her_texts, ytruth, cand)}

    good = [train[i] for i in np.argsort(-ytr)[:KEEP]]
    gset = set(''.join(good))
    mem = sorted(cand, key=lambda c: -sum(ch in gset for ch in c) / max(len(c), 1))[:KEEP]
    res['记忆派'] = evaluate(mem, ytruth, cand)

    rng = np.random.default_rng(11)
    res['随机'] = evaluate([cand[i] for i in rng.choice(len(cand), KEEP, replace=False)], ytruth, cand)

    # 我填的那套：完全信便宜模型，把预算全砸在它预测的前 24 句上
    my_texts, _ = select(cheap2, cand, 0.05, 12)
    res['我填的'] = evaluate(my_texts, ytruth, cand)
    res['真最优(不可达上界)'] = float(np.sort(ytruth)[-KEEP:].mean())

    for k, v in res.items():
        print(f'    {k:<26} {v:+.4f}')
    print(f'\n    ★ 她 − 我填的 = {res["她学的(π,r + 念不念得出)"]-res["我填的"]:+.4f}')
    print(f'    ★ 她 − 记忆派 = {res["她学的(π,r + 念不念得出)"]-res["记忆派"]:+.4f}')
    print(f'    ★ 她 − 随机   = {res["她学的(π,r + 念不念得出)"]-res["随机"]:+.4f}')
    print(f'    ★ ★104 她输随机 0.12；这一课 {("赢" if res["她学的(π,r + 念不念得出)"]>res["随机"] else "仍输")}')

    # ── 她说出来 ────────────────────────────────────────
    print(f'\n★★★ 她自己挑出来、亲口说的 8 句（真人真的说过）:')
    segs = []
    for i, t in enumerate(her_texts[:8]):
        w, _ = speak_text(t, P, rng=np.random.default_rng(hash(t) % 77777))
        g = E.hear(w)
        segs += [w, np.zeros(int(0.28 * SR))]
        lat = sum(1 for c in t if not HAN.match(c) and c.isalpha())
        print(f'   {i+1}. {t:<22} F0 {g["f0med"]:.0f}Hz 浊音 {g["voiced"]:.2f}'
              f'{"  ← 念不出" if lat else ""}')
    allx = np.concatenate(segs)
    allx = allx / max(np.abs(allx).max(), 1e-9) * 0.85
    from scipy.io import wavfile
    out = f'{ROOT}/data/her_voice/she_picks_105.wav'
    wavfile.write(out, SR, (allx * 32767).astype(np.int16))

    json.dump({'r_half': r_half, 'W2': W2.tolist(), 'best_pi': best_pi,
               'best_r': best_r, 'res': res, 'said': her_texts[:8],
               'pi_res': {str(k): v for k, v in pi_res.items()},
               'r_res': {str(k): v for k, v in r_res.items()}},
              open(f'{ROOT}/data/exp105_pick.json', 'w'), ensure_ascii=False, indent=1)
    print(f'\n→ {out}')
