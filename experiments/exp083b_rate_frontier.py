# -*- coding: utf-8 -*-
"""
exp083b: 12.5Hz 是工程妥协还是信息最优？—— 固定 token 预算下的时间/频率权衡

【为什么这样设计】
  v2 的分类任务在所有 SNR 下都饱和到 1.0（我的合成韵律差异太大），
  无法检验 12.5Hz。改用不依赖分类器的纯信息度量：重构误差。

【关键洞察】
  真实 codec 的总带宽是固定的：bitrate = 帧率 x log2(码本大小)。
  所以帧率不是自由参数——帧率升高，码本必须变小。
  真正的权衡是：时间分辨率（多少帧） vs 频率分辨率（每帧多细）。
  Mimi 公开数字：12.5Hz x 8 码本，1.1 kbps。

【实验】固定每秒 token 预算 B，扫帧率，K 随之确定，测 mel 重构误差。
  若误差在某个中间帧率最低 -> 12.5Hz 有结构性理由；
  若单调 -> 12.5Hz 纯粹是延迟/带宽的工程妥协。
"""
import os, sys, json, math
import numpy as np
from sklearn.cluster import KMeans
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util
spec = importlib.util.spec_from_file_location("e83", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "exp083_audio_token_not_text.py"))
e83 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e83)

SR, NFIX = e83.SR, 64
BUDGET = 50.0      # 每秒 token 数（对应 12.5Hz x 4bit 量级）
RATES = [6.25, 12.5, 25.0, 50.0]

def main():
    # 用四类韵律各若干条，构造一个真实的音频池
    ys, y = [], []
    for li, st in enumerate(e83.LABELS):
        for j in range(25):
            ys.append(e83.synth(st, 1000 + li * 100 + j)); y.append(li)
    y = np.array(y)
    print(f"[data] n={len(ys)}")

    M100 = [e83.stft_mel(v) for v in ys]          # 100Hz 基准
    # 基准：以 100Hz 原始信号自身的方差为归一
    allraw = np.vstack(M100); base_var = float(np.var(allraw))
    print(f"[baseline] 原始 mel 方差 = {base_var:.4f}")

    print("\n=== 固定预算 B=%.0f token/s：帧率 ↑ 则码本 ↓ ===" % BUDGET)
    rows = []
    for rate in RATES:
        bits = BUDGET / rate
        K = int(2 ** bits)
        cap = 256
        k = int(round(100.0 / rate))
        Mp, Mpool = [], []
        for M in M100:
            n = (M.shape[0] // k) * k
            Mp.append(M[:n].reshape(n // k, k, M.shape[1]).mean(1) if n else M)
        allf = np.vstack(Mp)
        K_eff = max(2, min(K, cap, len(allf) // 4))
        km = KMeans(n_clusters=K_eff, n_init=8, random_state=0).fit(allf)
        # 重构：每帧用码本中心替代
        err, tot = 0.0, 0
        for M in Mp:
            rec = km.cluster_centers_[km.predict(M)]
            err += float(np.sum((M - rec) ** 2)); tot += M.size
        mse = err / tot
        nmse = mse / base_var
        rows.append(dict(rate=rate, bits=round(bits, 2), K=K_eff,
                         mse=round(mse, 5), nmse=round(nmse, 5),
                         frames_per_sec=rate, tokens_per_sec=round(rate * math.log2(K_eff), 1)))
        print(f"  rate={rate:>6}Hz  bits/frame={bits:>5.2f}  K={K_eff:>4}  "
              f"MSE={mse:.5f}  归一化={nmse:.5f}  实际带宽={rate*math.log2(K_eff):.1f} tok/s")

    best = min(rows, key=lambda r: r['nmse'])
    print(f"\n[最优] rate={best['rate']}Hz  nmse={best['nmse']:.5f}  (K={best['K']})")

    # 肘部分析：每翻一倍帧率，误差下降多少
    print("\n[边际收益] 帧率翻倍带来的误差下降")
    for i in range(1, len(rows)):
        d = rows[i - 1]['nmse'] - rows[i]['nmse']
        print(f"  {rows[i-1]['rate']:>6} -> {rows[i]['rate']:>6}Hz : 下降 {d:+.5f}")

    out = dict(timestamp=__import__('time').strftime("%Y-%m-%d %H:%M:%S"),
        budget_tokens_per_sec=BUDGET, base_var=round(base_var, 4),
        rows=rows, best=best,
        note="固定总预算；帧率与码本大小此消彼长。若最优在中间帧率 -> 12.5Hz 有结构性理由；若单调 -> 工程妥协。")
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result_083b.json')
    json.dump(out, open(p, 'w'), ensure_ascii=False, indent=2)
    print("[saved]", p)

if __name__ == '__main__':
    main()
