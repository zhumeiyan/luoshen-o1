# -*- coding: utf-8 -*-
"""
197 v2: 动态捕捉 + 记忆 + 决策 + 梦境

耦合链:
  捕捉(决策) -> 需要预测 -> 预测被观测噪声污染 -> 噪声被感知疲劳放大 -> 记忆(k阶)用来降噪
  离线期感知关闭, 只能靠重放; 且离线预算(300) >> 在线(40), 所以离线怎么用主导模型

世界: AR(2)  x_{t+1} = a1*x_t + a2*x_{t-1} + mu + sigma*noise
      mu 每天漂移 (结构a1,a2不变, 偏置漂移)
      最优预测器 w*=[a2, a1], b*=mu/(1-a1-a2)  -> k=2 是真正需要的

离线四模式:
  rest    不更新 (只恢复感知)
  replay  循环重放最近一天的原始序列    = 不否定
  dream   片段重组(+可选微扰alpha)      = 有方向否定 (保片段内k阶结构, 破长程顺序)
  noise   纯噪声                        = 全盘否定
内部适应: 同一k-gram重复暴露 -> 有效学习率衰减
"""
import numpy as np, json, os, hashlib
from collections import deque

OUT = os.path.dirname(os.path.abspath(__file__))


def simulate(seed=0, mode='rest', alpha=0.0, days=30, N_on=40, B_off=300,
             a1=0.5, a2=0.2, sigma=1.0, mu_drift=0.03,
             k=2, lr_on=0.05, lr_off=0.05,
             a_adapt=0.02, obs_noise=0.5, internal_adapt=1.0,
             seg_len=6, clipv=2.0):
    rng = np.random.default_rng(seed)
    w = np.zeros(k)
    b = 0.0
    s = 1.0
    mu = 0.0
    buffer = []
    expose = {}

    def upd(h, tgt, lr):
        """NLMS 一步更新 + clip, 返回更新前误差"""
        nonlocal w, b
        pred = float(np.dot(w, h)) + b
        err = tgt - pred
        nrm = float(np.dot(h, h)) + 1.0
        w += lr * err * h / nrm
        b += lr * err / nrm
        w = np.clip(w, -clipv, clipv)
        b = float(np.clip(b, -clipv * 5, clipv * 5))
        return pred, err

    # ---- 预填充 buffer ----
    x_prev, x = 0.0, 0.0
    for _ in range(400):
        xn = a1 * x + a2 * x_prev + mu + sigma * rng.normal()
        x_prev, x = x, xn
        buffer.append(xn)

    day_mae, day_mae_first = [], []

    for day in range(days):
        mu += mu_drift * rng.normal()           # 偏置漂移
        hist = deque(maxlen=k)

        errs, errs_first = [], []
        for t in range(N_on):
            x_true = a1 * x + a2 * x_prev + mu + sigma * rng.normal()
            s *= np.exp(-a_adapt)               # 感知适应(疲劳)
            obs = x_true + obs_noise * rng.normal() / max(s, 1e-3)
            if len(hist) == k:
                h = np.array(hist, dtype=float)
                pred, _ = upd(h, obs, lr_on)
                e = abs(pred - x_true)          # 用真值评估捕捉质量
                errs.append(e)
                if t < 10:
                    errs_first.append(e)
            hist.append(obs)
            buffer.append(obs)
            x_prev, x = x, x_true

        day_mae.append(float(np.mean(errs)) if errs else float('nan'))
        day_mae_first.append(float(np.mean(errs_first)) if errs_first else float('nan'))

        # ---------------- 离线 ----------------
        s = min(1.0, s + 0.35 * (1.0 - s) + 0.30)     # 感知恢复
        if mode == 'rest':
            continue

        recent = np.array(buffer[-N_on:])
        if len(recent) < k + 1:
            continue

        if mode == 'replay':
            # 循环重放原始序列 -> 同一k-gram反复出现
            seq = np.resize(recent, B_off + k)
        elif mode == 'dream':
            n_seg = max(1, len(recent) // seg_len)
            segs = [recent[i * seg_len:(i + 1) * seg_len] for i in range(n_seg)]
            parts = []
            while sum(len(p) for p in parts) < B_off + k:
                parts.append(segs[rng.integers(n_seg)])
            seq = np.concatenate(parts)[:B_off + k]
            if alpha > 0:
                seq = seq + alpha * rng.normal(size=seq.shape)
        elif mode == 'noise':
            seq = rng.normal(np.mean(recent), np.std(recent) + 1e-9, size=B_off + k)
        else:
            continue

        for i in range(len(seq) - k):
            h = seq[i:i + k]
            tgt = seq[i + k]
            key = hashlib.md5(np.round(h, 1).tobytes() + np.round(tgt, 1).tobytes()).digest()[:8]
            cnt = expose.get(key, 0)
            eff = lr_off / (1.0 + internal_adapt * cnt)
            upd(h, tgt, eff)
            expose[key] = cnt + 1

    return {
        'mode': mode, 'alpha': alpha, 'seed': seed,
        'mae_curve': [round(v, 4) for v in day_mae],
        'steady': round(float(np.mean(day_mae[-10:])), 4),
        'wake': round(float(np.mean(day_mae_first[-10:])), 4),   # 唤醒后前10拍
        'w': [round(float(v), 4) for v in w], 'b': round(float(b), 4),
    }


def oracle_mae(seed=0, N=4000, a1=0.5, a2=0.2, sigma=1.0):
    """用真实参数预测的MAE下界"""
    rng = np.random.default_rng(seed)
    xp, x = 0.0, 0.0
    es = []
    for _ in range(N):
        xt = a1 * x + a2 * xp + sigma * rng.normal()
        es.append(abs(a1 * x + a2 * xp - xt))
        xp, x = x, xt
    return round(float(np.mean(es)), 4)


if __name__ == '__main__':
    res = {}
    modes = ['rest', 'replay', 'dream', 'noise']

    print('[A] 四模式 × 5种子  (MAE越低越好)')
    A = {}
    for m in modes:
        runs = [simulate(seed=s, mode=m, alpha=0.0) for s in range(5)]
        A[m] = {
            'steady': round(float(np.mean([r['steady'] for r in runs])), 4),
            'std': round(float(np.std([r['steady'] for r in runs])), 4),
            'wake': round(float(np.mean([r['wake'] for r in runs])), 4),
            'per_seed': [r['steady'] for r in runs],
            'w': [r['w'] for r in runs],
        }
        print(f'  {m:7s} steady={A[m]["steady"]:.4f} ±{A[m]["std"]:.4f}  '
              f'wake={A[m]["wake"]:.4f}')
    res['A'] = A
    res['oracle'] = oracle_mae()
    print(f'  oracle (真参数) = {res["oracle"]:.4f}')

    # B: 分离"重组"与"荒诞(噪声)"两个成分
    print('[B] 梦境成分分离: 重组 × 噪声')
    B = []
    for alpha in [0.0, 0.2, 0.5, 1.0, 2.0]:
        for m in ['replay', 'dream']:
            runs = [simulate(seed=s, mode=m, alpha=alpha) for s in range(5)]
            st = float(np.mean([r['steady'] for r in runs]))
            B.append({'mode': m, 'alpha': alpha, 'steady': round(st, 4),
                      'std': round(float(np.std([r['steady'] for r in runs])), 4)})
            print(f'  {m:7s} alpha={alpha:<4} steady={st:.4f}')
    res['B'] = B

    # C: 内部适应是否是 replay 变差的机制
    print('[C] 内部适应强度')
    C = []
    for ia in [0.0, 0.5, 1.0, 3.0]:
        row = {'internal_adapt': ia}
        for m in ['replay', 'dream']:
            runs = [simulate(seed=s, mode=m, alpha=0.0, internal_adapt=ia) for s in range(5)]
            row[m] = round(float(np.mean([r['steady'] for r in runs])), 4)
        C.append(row)
        print(f'  ia={ia:<4} replay={row["replay"]:.4f}  dream={row["dream"]:.4f}')
    res['C'] = C

    # D: 世界漂移幅度 × 模式
    print('[D] 漂移幅度 × 模式')
    D = []
    for md in [0.0, 0.03, 0.10]:
        row = {'mu_drift': md}
        for m in ['replay', 'dream']:
            runs = [simulate(seed=s, mode=m, alpha=0.0, mu_drift=md) for s in range(5)]
            row[m] = round(float(np.mean([r['steady'] for r in runs])), 4)
        D.append(row)
        print(f'  drift={md:<5} replay={row["replay"]:.4f}  dream={row["dream"]:.4f}')
    res['D'] = D

    # E: 学习曲线
    E = {}
    for m in modes:
        runs = [simulate(seed=s, mode=m, alpha=0.0) for s in range(5)]
        E[m] = [round(float(np.mean([r['mae_curve'][d] for r in runs])), 4)
                for d in range(30)]
    res['E'] = E

    with open(os.path.join(OUT, 'result197.json'), 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print('saved result197.json')
