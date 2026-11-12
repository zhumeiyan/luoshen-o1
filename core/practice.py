#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
practice —— 练习器（让同一套动作反复练，不是一课就完）

════ 为什么单独有这个 ════
  之前每一课都是"跑一次 50 步搜索就交卷"。那不是练习，是考试。
  练习的定义：同一件事反复做，做得越来越好，并且【能被看出在进步】。

════ 这一课的靶：女声 ════
  35 段真人语音里 34 段是女声（F0 中位 181.8Hz），1 段男声（131.1Hz）。
  她是女孩子 —— 靶只留女声，那 1 段男声剔除。

════ ★ 我量不准的，不教 ════
  想教她"女孩子声道短、共振峰高"，但：
    - FFT 谱峰法：F1 恒测成 203，与真值无关 ❌
    - LPC 谱包络法：误差几百 Hz ❌
    - 谱质心：跨度 40Hz，不单调 ❌
  三种尺子全验不过 → 按第 6 条规矩【拿不到就说拿不到】，
  不拿它教她。这一课只用验得准的 5 个维度。
"""

from __future__ import annotations
import numpy as np


def levinson(r, order):
    a = np.zeros(order + 1); a[0] = 1.0; e = r[0]
    for i in range(1, order + 1):
        k = -(r[i] + np.dot(a[1:i], r[i - 1:0:-1])) / e if i > 1 else -r[1] / e
        a_new = a.copy(); a_new[i] = k
        for j in range(1, i):
            a_new[j] = a[j] + k * a[i - j]
        a = a_new; e *= (1 - k * k)
        if e <= 0:
            break
    return a


def run_practice(synth, ear_fn, target, start, bounds,
                 pick_seeds=(1, 2, 3), fair_seeds=None,
                 n_epochs=20, steps_per_epoch=60,
                 rng_seed=7, decay=True, stuck_perturb=True):
    """
    反复练习：每个 epoch 练 steps_per_epoch 次，只接受变好的改动。

    ★★ 三组种子必须分开（ML 标准做法）：
        PICK = 训练：她对着这个优化
        VAL  = 验证：决定【练到第几个 epoch 停】← 防练过头
        TEST = 测试：最终报告，从不参与任何决策

    返回 (best_params, history, best_by_val, best_epoch)
      只返回【最后一步】是不够的 —— 练过头会回到对着 PICK 死记。
    """
    if fair_seeds is None:
        fair_seeds = tuple(range(9000, 9024))

    def make(gen_fn, seeds):
        ds = []
        for s in seeds:
            y, _ = synth(gen_fn, rng=np.random.default_rng(s))
            m = ear_fn(y)
            if m and m.get('f0_med', 0) > 50:
                ds.append(_dist(m, target))
        return ds

    def ev(p, seeds=pick_seeds):
        ds = make(p, seeds)
        return float(np.mean(ds)) if ds else 9.9

    def fair(p):
        ds = make(p, fair_seeds)
        if not ds:
            return 9.9, 0.0
        return float(np.mean(ds)), float(np.std(ds)) / np.sqrt(len(ds))

    best = dict(start)
    bd = ev(best)
    rng = np.random.default_rng(rng_seed)
    keys = list(bounds)
    hist = []

    total = n_epochs * steps_per_epoch
    step = 0
    for ep in range(n_epochs):
        before = bd
        for _ in range(steps_per_epoch):
            step += 1
            c = dict(best)
            k = keys[rng.integers(0, len(keys))]
            lo, hi = bounds[k]
            frac = max(0.30 * (1 - step / total), 0.02) if decay else 0.30
            c[k] = float(np.clip(c[k] + rng.normal(0, (hi - lo) * frac), lo, hi))
            d = ev(c)
            if d < bd:
                best, bd = c, d
        # ★ 卡住了就"换个姿势重来"：同时大幅扰动多个参数
        #   单参数爬山会被参数间耦合困住（实测：她卡在 f0_base=156，
        #   而单独扫过去 170 明显更好 —— 单改一个参数却变差）
        if stuck_perturb and bd >= before - 1e-9:
            for _ in range(steps_per_epoch // 2):
                c = dict(best)
                for k in rng.choice(keys, size=min(3, len(keys)), replace=False):
                    lo, hi = bounds[k]
                    c[k] = float(np.clip(c[k] + rng.normal(0, (hi - lo) * 0.25), lo, hi))
                d = ev(c)
                if d < bd:
                    best, bd = c, d
        fs, se = fair(best)
        hist.append({'epoch': ep + 1, 'steps': step, 'pick': bd,
                     'fair': fs, 'se': se, 'params': dict(best)})
    # ★ 用验证集挑 epoch（不是返回最后一步）
    bi = int(np.argmin([h['fair'] for h in hist]))
    return best, hist, hist[bi]['params'], hist[bi]['epoch']


# ═══ ★ 修过的耳朵 ═══
#   旧 ear 只看"有没有 F0"(f0>20)，把气声/宽带噪声也当成浊音：
#     起点参数下真实 F0 中位 104Hz，耳朵测成 320Hz —— 错 3 倍。
#   真因：F0 在 32ms 帧内变化过剧(32~397Hz)，自相关找不到稳定周期，抓到错误峰。
#   修法：加【周期性强度】判据 —— 浊音自相关峰 0.83，纯噪声 0.10，阈值 0.3 干净分开。
def f0_peak(seg, SR=16000):
    """返回 (F0, 周期性强度)；强度低 = 不是真浊音"""
    s = seg - seg.mean()
    if np.sqrt((s ** 2).mean()) < 1e-5:
        return 0.0, 0.0
    c = np.correlate(s, s, 'full')[len(s) - 1:]
    if c[0] <= 0:
        return 0.0, 0.0
    c = c / c[0]
    lo, hi = int(SR / 500), min(int(SR / 70), len(c) - 1)
    reg = c[lo:hi]
    if len(reg) < 4:
        return 0.0, 0.0
    return SR / (int(np.argmax(reg)) + lo), float(reg.max())


def ear_robust(x, SR=16000, w=512, h=256, period_thr=0.3):
    """带周期性强度判据的耳朵"""
    n = (len(x) - w) // h + 1
    F = np.stack([x[i * h:i * h + w] for i in range(n)]) if n > 0 else np.zeros((0, w))
    if len(F) < 10:
        return None
    rms = np.sqrt((F ** 2).mean(1))
    f0s, pks = [], []
    for f in F:
        a, b = f0_peak(f, SR)
        f0s.append(a); pks.append(b)
    f0s = np.array(f0s); pks = np.array(pks)
    v = (f0s > 20) & (pks > period_thr)          # ★ 真浊音：有 F0 且周期性强
    vf = f0s[v]
    thr = np.median(rms) * 0.25
    sil = rms < thr
    d = np.diff(np.concatenate([[0], sil.astype(int), [0]]))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    pl = [(e - s) * h / SR for s, e in zip(st, en) if (e - s) * h / SR > 0.05]
    return {'voiced': float(v.mean()),
            'f0_med': float(np.median(vf)) if len(vf) > 5 else 0.0,
            'f0_std': float(np.std(np.log(vf))) if len(vf) > 5 else 0.0,
            'sil': float(sil.mean()),
            'pause_med': float(np.median(pl)) if pl else 0.0}


SCALE = {'voiced': 0.30, 'f0_med': 60.0, 'f0_std': 0.20, 'sil': 0.20, 'pause_med': 0.20}


def _dist(a, b):
    return float(np.mean([abs(a[k] - b[k]) / SCALE[k] for k in SCALE]))


# ═══ ★83 修耳朵的静音检测 ═══
#  旧 ear 的静音阈值：thr = median(rms) * 0.25
#  这个写法在两个方向上都错：
#    真静音少(<50%) → median 落在有声区 → thr 偏高 → 把气声判成静音（多算）
#    真静音多(>50%) → median 落在静音区 → thr 低于噪声地板 → 一个静音都没有（少算）
#  实测：真值 0.16 测成 0.43（+165%）；真值高时测成 0.00（−100%）。
#  ★ 同一把尺子两个方向都错 = 不是偏差，是定义错了，没法靠调常数修。
#
#  新写法：静音在能量上是【双峰】，用 Otsu 在 log 能量上自适应找谷。
#  这不由我给常数——阈值由她自己的声音分布决定。
#  再加一条物理守卫：两峰差不到 MIN_SEP_DB 就不算有静音
#  （真实录音里静音段比说话段低 20dB 以上，这是声学事实，不是我拍的）。
MIN_SEP_DB = 10.0


def _otsu_db(rms, min_sep_db=MIN_SEP_DB):
    """在 log 能量上自适应找双峰谷底。返回 (阈值dB, 两峰间距dB)；间距不足 → None"""
    r = np.asarray(rms, float)
    r = r[r > 0]
    if len(r) < 32:
        return None
    d = 20.0 * np.log10(r + 1e-12)
    lo, hi = np.percentile(d, 1), np.percentile(d, 99)
    if hi - lo < 1.0:                      # 根本没有动态范围 → 没有静音可言
        return None
    hist, edges = np.histogram(d, bins=64, range=(lo, hi))
    w = hist.astype(float)
    if w.sum() <= 0:
        return None
    w = w / w.sum()
    mid = 0.5 * (edges[:-1] + edges[1:])
    cw = np.cumsum(w)
    cm = np.cumsum(w * mid)
    mu = cm[-1]
    var = (mu * cw - cm) ** 2 / (cw * (1 - cw) + 1e-12)
    k = int(np.argmax(var))
    thr = float(mid[k])
    lo_m = d[d < thr]
    hi_m = d[d >= thr]
    if len(lo_m) < 8 or len(hi_m) < 8:
        return None
    sep = float(np.median(hi_m) - np.median(lo_m))
    if sep < min_sep_db:
        return None            # 两峰没分开 → 不承认存在静音
    return thr, sep


def ear_fixed(x, SR=16000, w=512, h=256, period_thr=0.3, min_sep_db=MIN_SEP_DB):
    """★83 耳朵：周期性判据(浊音) + Otsu 自适应(静音)"""
    n = (len(x) - w) // h + 1
    F = np.stack([x[i * h:i * h + w] for i in range(n)]) if n > 0 else np.zeros((0, w))
    if len(F) < 10:
        return None
    rms = np.sqrt((F ** 2).mean(1))
    f0s, pks = [], []
    for f in F:
        a, b = f0_peak(f, SR)
        f0s.append(a); pks.append(b)
    f0s = np.array(f0s); pks = np.array(pks)
    v = (f0s > 20) & (pks > period_thr)
    vf = f0s[v]
    got = _otsu_db(rms, min_sep_db)
    if got is None:
        sil = np.zeros(len(F), dtype=bool)
        sep = 0.0
    else:
        thr, sep = got
        sil = 20.0 * np.log10(rms + 1e-12) < thr
    d = np.diff(np.concatenate([[0], sil.astype(int), [0]]))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    pl = [(e - s) * h / SR for s, e in zip(st, en) if (e - s) * h / SR > 0.05]
    return {'voiced': float(v.mean()),
            'f0_med': float(np.median(vf)) if len(vf) > 5 else 0.0,
            'f0_std': float(np.std(np.log(vf))) if len(vf) > 5 else 0.0,
            'sil': float(sil.mean()),
            'pause_med': float(np.median(pl)) if pl else 0.0,
            'sep_db': float(sep)}


# ═══ ★83 v3：换掉"sil"的旧定义 ═══
#  试验过 Otsu 自适应求谷 —— 仍测不准（MAE 0.23，r=0.45）。真因不是阈值怎么取，
#  而是【能量阈值这个定义本身】分不清三件事：浊音 / 清音(气声) / 静音。
#  清音只比浊音低 ~13dB，却比静音低 100dB 以上 —— 用一条能量线切，必错。
#
#  v3 改成：先估本底(floor)，再要求"本底必须显著低于说话"，否则不承认有静音。
#  这不是我拍的常数：本底估的是她自己这段声音的最低 5%，间距门槛用真值扫。
def ear_v3(x, SR=16000, w=512, h=256, period_thr=0.3, sep_min=25.0, margin=20.0):
    n = (len(x) - w) // h + 1
    F = np.stack([x[i * h:i * h + w] for i in range(n)]) if n > 0 else np.zeros((0, w))
    if len(F) < 10:
        return None
    rms = np.sqrt((F ** 2).mean(1))
    f0s, pks = [], []
    for f in F:
        a, b = f0_peak(f, SR)
        f0s.append(a); pks.append(b)
    f0s = np.array(f0s); pks = np.array(pks)
    v = (f0s > 20) & (pks > period_thr)
    vf = f0s[v]
    d = 20.0 * np.log10(rms + 1e-12)
    floor = float(np.percentile(d, 5))
    speech = float(np.percentile(d, 98))
    sep = speech - floor
    if sep < sep_min:
        sil = np.zeros(len(F), dtype=bool)       # 本底没显著低于说话 → 不承认有静音
    else:
        sil = d < (floor + margin)
    dd = np.diff(np.concatenate([[0], sil.astype(int), [0]]))
    st, en = np.where(dd == 1)[0], np.where(dd == -1)[0]
    pl = [(e - s) * h / SR for s, e in zip(st, en) if (e - s) * h / SR > 0.05]
    return {'voiced': float(v.mean()),
            'f0_med': float(np.median(vf)) if len(vf) > 5 else 0.0,
            'f0_std': float(np.std(np.log(vf))) if len(vf) > 5 else 0.0,
            'sil': float(sil.mean()),
            'pause_med': float(np.median(pl)) if pl else 0.0,
            'sep': float(sep)}
