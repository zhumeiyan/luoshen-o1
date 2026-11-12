"""★105b 挑尖子（修好 π 的建模后重跑）

★105 第一版 π 无区分度 —— 我的错：
    我把"实测句数"固定成 BUDGET//r，于是所有 π≥0.10 剪出来的幸存者
    都超过能测的数量，取前 50 名 → 跟不剪一模一样。
    数学上那个旋钮不可能有权衡，我却怪她学不出峰。★78 同一个错。

修法（真实约束）：预算固定，剪得窄就自然测得深。
    m = min(π·C, B) 句；r = B/m 遍     ← 宽而浅 ↔ 窄而深，真权衡

两个旋钮：
  π  剪多窄（便宜模型"好但不可靠"，剪太狠会把真最好的剪掉）
  θ  定胜负时，信实测还是信便宜模型（赢家诅咒：实测的尖子被噪声抬高）
"""
import sys, os, json
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.speak_text import speak_text
from core import speech_organ as so
import experiments.exp104_shefinds as E
import experiments.exp105_pick as B

ROOT = '/data/workspace/luoshen-o1'
SR = so.SR
P, TARGET = B.P, B.TARGET
C_CAND, R_TRUTH, BUDGET, KEEP = 500, 24, 300, 24
HAN = E.HAN


def say(t, s):
    w, _ = speak_text(t, P, rng=np.random.default_rng(s))
    return -E.humanness(E.hear(w), TARGET)


def build():
    pool = E.load_pool()
    train, cand = pool[:B.C_TRAIN], pool[500:500 + C_CAND]
    d = json.load(open(B.CACHE))
    return train, cand, np.array(d['ytr']), np.array(d['ytruth'])


def z(v):
    v = np.asarray(v, float)
    s = v.std()
    return (v - v.mean()) / (s if s > 1e-12 else 1.0)


def select(cand, cheap, pi, theta, budget=BUDGET, reps_fn=None,
           oracle_truth=None, seed_measure=777331):
    """剪枝 → 花预算实测 → 实测与便宜模型加权定胜负"""
    nsurv = max(KEEP + 1, int(round(pi * len(cand))))
    surv = np.argsort(-cheap)[:nsurv]
    m = min(nsurv, budget)
    r = max(1, budget // m)
    pick_from = surv[:m]
    if oracle_truth is not None:
        meas = oracle_truth[pick_from]              # 无噪声的实测（消融用）
    elif reps_fn is not None:
        meas = np.array([reps_fn(cand[j], r) for j in pick_from])
    else:
        meas = np.array([np.mean([say(cand[j], (hash(cand[j]) % seed_measure) * 31 + k * 977)
                                  for k in range(r)]) for j in pick_from])
    cs = cheap[pick_from]
    final = (1 - theta) * z(meas) + theta * z(cs)
    order = np.argsort(-final)[:KEEP]
    return [cand[pick_from[i]] for i in order], dict(m=m, r=r, nsurv=nsurv)


def ev(texts, cand, ytruth):
    return float(ytruth[[cand.index(t) for t in texts]].mean())


if __name__ == '__main__':
    train, cand, ytr, ytruth = build()
    W2, Ftr2 = B.fit(B.feats2, train, ytr)
    W1, Ftr1 = B.fit(B.feats_nocover, train, ytr)
    cheap = np.array([B.feats2(t) for t in cand]) @ W2
    cheap_nc = np.array([B.feats_nocover(t) for t in cand]) @ W1

    print('【1】尺子自检（沿用 ★105）：前后各 12 遍 r=0.9848 信度 0.9923')

    # ── 判据2：cover 特征到底有没有用（看【挑出来的句子】，不看整体 r）──
    low = (np.array([len(B.text_to_syllables(t)) for t in cand]) /
           np.array([len(t) for t in cand])) < 0.9
    print(f'\n【2】"这句我念不念得出"这个特征：候选池里念不出的有 {low.sum()} 句')
    for tag, ch in [('含cover', cheap), ('不含cover', cheap_nc)]:
        t24, _ = select(cand, ch, 1.00, 0.0)
        bad = sum(1 for t in t24 if len(B.text_to_syllables(t)) / len(t) < 0.9)
        print(f'    {tag:<10} 挑出的 24 句里有 {bad} 句念不出 → 真相 {ev(t24,cand,ytruth):+.4f}')
    print(f'    她给这个特征的权重 {W2[7]:+.3f}（{"最重" if abs(W2[7])==max(abs(W2[1:])) else "不是最重"}）')

    # ── 判据3：π 内部峰（修好建模后）──────────────────
    print(f'\n【3】π = 剪多窄（预算 {BUDGET} 固定：剪得窄 → 测得深）')
    print(f'{"π":>6} {"幸存":>6} {"实测":>6} {"每句遍数":>9} {"说出24句真相":>13}')
    pis = [0.05, 0.08, 0.12, 0.20, 0.30, 0.50, 0.75, 1.00]
    pi_res = {}
    for pi in pis:
        t24, info = select(cand, cheap, pi, 0.0)
        pi_res[pi] = ev(t24, cand, ytruth)
        print(f'{pi:>6.2f} {info["nsurv"]:>6} {info["m"]:>6} {info["r"]:>9} {pi_res[pi]:>+13.4f}')
    bp = max(pi_res, key=pi_res.get)
    span = pi_res[bp] - min(pi_res.values())
    print(f'    → 峰 π={bp}（{"内部" if 0.05 < bp < 1.00 else "边界"}）跨度 {span:.4f}')

    # ── 判据4：π 硬依赖两端 ────────────────────────────
    print(f'\n【4】硬依赖两端：π 的价值来自"便宜模型好但不可靠"')
    for tag, sc in [('完美模型(真值当预测)', ytruth),
                    ('瞎猜模型(打乱)', cheap[np.random.default_rng(3).permutation(len(cheap))])]:
        rr = {pi: ev(select(cand, sc, pi, 0.0)[0], cand, ytruth) for pi in pis}
        b2 = max(rr, key=rr.get)
        print(f'    {tag:<20} 峰 π={b2:<5} 跨度 {rr[b2]-min(rr.values()):.4f}')
    print(f'    {"真实模型(她学的)":<20} 峰 π={bp:<5} 跨度 {span:.4f}')

    # ── 判据5：θ 内部峰 + 硬依赖 ───────────────────────
    print(f'\n【5】θ = 定胜负时信实测(0) 还是信便宜模型(1)（π={bp}）')
    th_res = {}
    for th in [0.0, 0.15, 0.30, 0.45, 0.60, 0.80, 1.00]:
        t24, _ = select(cand, cheap, bp, th)
        th_res[th] = ev(t24, cand, ytruth)
        print(f'    θ={th:<5} → {th_res[th]:+.4f}')
    bt = max(th_res, key=th_res.get)
    print(f'    → 峰 θ={bt}（{"内部" if 0.0 < bt < 1.0 else "边界"}）'
          f'  比纯实测高 {th_res[bt]-th_res[0.0]:+.4f}，比纯模型高 {th_res[bt]-th_res[1.0]:+.4f}')

    noiseless = lambda t, r: say(t, 4242)   # 每遍同一随机种子 = 无抖动
    rr = {th: ev(select(cand, cheap, bp, th, reps_fn=noiseless)[0], cand, ytruth)
          for th in [0.0, 0.30, 0.60, 1.00]}
    b3 = max(rr, key=rr.get)
    print(f'【6】硬依赖：关掉实测抖动 → 峰 θ={b3}（有抖动时 {bt}）'
          f'{"← 移向纯实测，模型的补救价值消失" if b3 == 0.0 else ""}')
    rr2 = {th: ev(select(cand, ytruth, bp, th, oracle_truth=ytruth)[0], cand, ytruth)
           for th in [0.0, 0.60, 1.00]}
    b4 = max(rr2, key=rr2.get)
    print(f'    另一端：实测变完美 → 峰 θ={b4}（应为 0.0，纯信实测）')

    # ── 判据7：四方对照 ────────────────────────────────
    print(f'\n【7】最终对照：各说 24 句（全是她从没见过的真人真话）')
    her, info = select(cand, cheap, bp, bt)
    res = {'她学的(π,θ)': ev(her, cand, ytruth)}
    good = [train[i] for i in np.argsort(-ytr)[:KEEP]]
    gset = set(''.join(good))
    res['记忆派'] = ev(sorted(cand, key=lambda c: -sum(ch in gset for ch in c) / max(len(c), 1))[:KEEP], cand, ytruth)
    res['随机'] = ev([cand[i] for i in np.random.default_rng(11).choice(len(cand), KEEP, replace=False)], cand, ytruth)
    mine, _ = select(cand, cheap, 0.05, 0.0)     # 我填的：狠剪 + 纯信实测
    res['我填的'] = ev(mine, cand, ytruth)
    onc, _ = select(cand, cheap, 1.00, 1.00)     # ★104 的错法：不剪 + 纯信模型
    res['★104的错法(纯信模型)'] = ev(onc, cand, ytruth)
    res['真最优(不可达)'] = float(np.sort(ytruth)[-KEEP:].mean())
    for k, v in res.items():
        print(f'    {k:<22} {v:+.4f}')
    print(f'\n    ★ 她 − 随机 = {res["她学的(π,θ)"]-res["随机"]:+.4f}'
          f'（★104 她是 −0.12）')
    print(f'    ★ 她 − 我填的 = {res["她学的(π,θ)"]-res["我填的"]:+.4f}')
    print(f'    ★ 她 − 记忆派 = {res["她学的(π,θ)"]-res["记忆派"]:+.4f}')
    print(f'    ★ 她离不可达上界还差 {res["真最优(不可达)"]-res["她学的(π,θ)"]:.4f}')

    print(f'\n★★★ 她自己挑出来、亲口说的 8 句:')
    segs = []
    for i, t in enumerate(her[:8]):
        w, _ = speak_text(t, P, rng=np.random.default_rng(hash(t) % 77777))
        g = E.hear(w)
        segs += [w, np.zeros(int(0.28 * SR))]
        cov = len(B.text_to_syllables(t)) / len(t)
        print(f'   {i+1}. {t:<22} F0 {g["f0med"]:.0f}Hz 浊音 {g["voiced"]:.2f}'
              f'{"  ←念不出" if cov < 0.9 else ""}')
    from scipy.io import wavfile
    allx = np.concatenate(segs)
    allx = allx / max(np.abs(allx).max(), 1e-9) * 0.85
    out = f'{ROOT}/data/her_voice/she_picks_105.wav'
    wavfile.write(out, SR, (allx * 32767).astype(np.int16))
    json.dump({'best_pi': bp, 'best_theta': bt, 'res': res, 'said': her[:8],
               'pi_res': {str(k): v for k, v in pi_res.items()},
               'th_res': {str(k): v for k, v in th_res.items()},
               'W_cover': float(W2[7])},
              open(f'{ROOT}/data/exp105b_pick.json', 'w'), ensure_ascii=False, indent=1)
    print(f'\n→ {out}')
