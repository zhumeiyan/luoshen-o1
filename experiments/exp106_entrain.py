"""★106 接话 —— 韵律顺应：她向对方靠多少

三个旋钮：
  A   整段向对方移动多少 Hz   （文献倒 U，NT 组最优 ≈4 Hz）
  λ   逐轮跟随对方变化的强度   （跟真变化，但会放大她听到的噪声）
  n   估计对方基线时看几轮     （平滑噪声 vs 跟不上对方变化）

★102 教训：所有参数用【公共随机数】——同一组对话。
"""
import sys, json
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
import core.entrainment as EN

ROOT = '/data/workspace/luoshen-o1'
T = json.load(open(f'{ROOT}/data/exp105b_pick.json'))
TEXTS = T['said'][:6]
NG = 18                      # 对话数
TURNS = 16                   # 每对话轮数
SEEDS = [int(np.random.default_rng(7).integers(0, 10 ** 6)) for _ in range(NG)]


def sc(A, lam, n, seeds=None, **kw):
    return EN.score(A, lam, n, TEXTS, seeds or SEEDS, turns=TURNS, **kw)


def se_of(A, lam, n, **kw):
    """用 4 组独立种子估计标准误"""
    v = [sc(A, lam, n, seeds=[int(np.random.default_rng(1000 + k).integers(0, 10 ** 6))
                              for _ in range(NG // 2)], **kw) for k in range(4)]
    return float(np.mean(v)), float(np.std(v, ddof=1) / np.sqrt(len(v)))


def curve(vals, f, label):
    r = [(v, f(v)) for v in vals]
    b = max(r, key=lambda z: z[1])[0]
    print(f'【{label}】')
    print('   ' + '  '.join(f'{v}:{x:+.3f}' for v, x in r))
    inside = min(vals) < b < max(vals)
    span = max(x for _, x in r) - min(x for _, x in r)
    print(f'   → 峰 {b}（{"内部" if inside else "边界"}）  跨度 {span:.4f}')
    return b, span, inside


def coord_descent(x0, grids, fixed=()):
    x = list(x0)
    for _ in range(3):
        for i, g in enumerate(grids):
            if i in fixed:
                continue
            x[i] = max(g, key=lambda v: sc(*(x[:i] + [v] + x[i + 1:])))
    return x


if __name__ == '__main__':
    print('她说的话（★105 她自己从 43321 句真人真话里挑的）：')
    for t in TEXTS:
        print('   ', t)

    # ── 判据1：尺子能不能吐出文献值 ───────────────────
    print(f'\n【1】尺子自检：文献说 NT 配对整段收敛 {EN.CONV_TARGET:.0f} Hz'
          f'（ASD 组发散 6 Hz）。我的环境里最优 A 是多少？')

    # ── 判据2-4：三个旋钮 ─────────────────────────────
    bA, spA, inA = curve([0, 2, 4, 6, 8, 12, 20, 40], lambda v: sc(v, 0.5, 4), 'A 整段移动 Hz')
    bL, spL, inL = curve([0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5], lambda v: sc(bA, v, 4), 'λ 逐轮跟随')
    bN, spN, inN = curve([1, 2, 3, 4, 6, 9, 12], lambda v: sc(bA, bL, v), 'n 基线窗口')

    # ── 判据5-7：硬依赖，每条两端 ─────────────────────
    print('\n【5】硬依赖 ①关掉"顺应有收益"（w_conv=0）→ A 还该有峰吗？')
    _, spA0, _ = curve([0, 4, 8, 20, 40], lambda v: sc(v, 0.5, 4, w_conv=0.0), '   A（无顺应收益）')
    print(f'   → 有顺应收益时跨度 {spA:.4f}，关掉后 {spA0:.4f}'
          f'{"← 塌了，A 的价值确来自顺应" if spA0 < spA / 2 else "（没塌，尺子有问题）"}')

    print('\n【6】硬依赖 ②对方不再变化（drift=0）→ λ 还该有峰吗？')
    _, spL0, _ = curve([0, 0.4, 0.8, 1.5], lambda v: sc(bA, v, 4, drift=0.0), '   λ（对方不变）')
    print(f'   → 对方会变时跨度 {spL:.4f}，不变时 {spL0:.4f}'
          f'{"← 塌了，λ 的价值确来自对方在变" if spL0 < spL / 2 else ""}')

    print('\n【7】硬依赖 ③她听得完美（sf=0）→ n 还该有峰吗？')
    _, spN0, _ = curve([1, 2, 4, 6, 12], lambda v: sc(bA, bL, v, sf=0.0), '   n（耳朵无噪声）')
    print(f'   → 耳朵有噪声时跨度 {spN:.4f}，无噪声时 {spN0:.4f}')

    # ── 判据8：她自己学 ────────────────────────────────
    print('\n【8】她从瞎起点 [A=0, λ=0, n=1] 开始学（坐标下降）')
    x0 = [0.0, 0.0, 1]
    grids = [[0, 2, 4, 6, 8, 12, 20, 40], [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5], [1, 2, 3, 4, 6, 9, 12]]
    print(f'   瞎起点 {x0} → {sc(*x0):+.4f}')
    her = coord_descent(x0, grids)
    print(f'   她学到  A={her[0]}Hz  λ={her[1]}  n={her[2]}  → {sc(*her):+.4f}')

    # ── 判据9：held-out 换一批真人 ─────────────────────
    print('\n【9】held-out：换一批没见过的真人对象')
    ho_lo = [f for f in EN._TRUE_F0 if f <= 178]        # 更低沉的一批
    ho_hi = [f for f in EN._TRUE_F0 if f > 178]
    print(f'   训练见过的对象 F0 {EN._TRUE_F0.min():.0f}~{EN._TRUE_F0.max():.0f}；'
          f'held-out 只用低沉的 {min(ho_lo):.0f}~{max(ho_lo):.0f}（{len(ho_lo)} 人）')
    res = {'她(规则/参数)': sc(*her, pool=ho_lo),
           '我填的 A=40,λ=1,n=3': sc(40, 1.0, 3, pool=ho_lo),
           '全不动 A=0,λ=0': sc(0, 0.0, 1, pool=ho_lo),
           '全顺应 A=100': sc(100, 1.0, 1, pool=ho_lo)}
    for k, v in res.items():
        print(f'   {k:<22} {v:+.4f}')
    print(f'   ★ 她 − 我填的 = {res["她(规则/参数)"]-res["我填的 A=40,λ=1,n=3"]:+.4f}')

    # ── 判据10：记忆派 ─────────────────────────────────
    print('\n【10】记忆派：在【原来的】对象上把 A 调到最优，然后硬套到新对象')
    best_old = max([0, 2, 4, 6, 8, 12, 20, 40], key=lambda v: sc(v, her[1], her[2]))
    mem = sc(best_old, her[1], her[2], pool=ho_lo)
    mine_hi = sc(40, 1.0, 3, pool=ho_hi)
    her_hi = sc(*her, pool=ho_hi)
    print(f'   原对象上最优 A={best_old}；硬套到低沉对象 → {mem:+.4f}')
    print(f'   她（重估）→ {res["她(规则/参数)"]:+.4f}   她 − 记忆派 = '
          f'{res["她(规则/参数)"]-mem:+.4f}')
    print(f'   另一批高音对象：她 {her_hi:+.4f}  我填的 {mine_hi:+.4f}')

    # ── 判据11：SE ─────────────────────────────────────
    print('\n【11】结果稳不稳（4 组独立种子）')
    m1, s1 = se_of(*her)
    m2, s2 = se_of(40, 1.0, 3)
    m3, s3 = se_of(0, 0.0, 1)
    print(f'   她      {m1:+.4f} ± {s1:.4f}')
    print(f'   我填的  {m2:+.4f} ± {s2:.4f}')
    print(f'   全不动  {m3:+.4f} ± {s3:.4f}')
    print(f'   → 她 − 我填的 = {m1-m2:+.4f}，2SE = {2*np.sqrt(s1**2+s2**2):.4f}'
          f'{"  显著" if abs(m1-m2) > 2*np.sqrt(s1**2+s2**2) else "  不显著"}')

    json.dump(dict(best_A=bA, best_lam=bL, best_n=bN, span_A=spA, span_lam=spL,
                   span_n=spN, span_A_noconv=spA0, span_lam_nodrift=spL0,
                   span_n_perfectear=spN0, her=her, sc_her=sc(*her),
                   res=res, mem=mem, se=dict(her=[m1, s1], mine=[m2, s2], none=[m3, s3]),
                   texts=TEXTS),
              open(f'{ROOT}/data/exp106_entrain.json', 'w'), ensure_ascii=False, indent=1)
    print('\n→ data/exp106_entrain.json')
