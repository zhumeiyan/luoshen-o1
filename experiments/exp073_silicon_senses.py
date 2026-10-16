# -*- coding: utf-8 -*-
"""
实验 073 · 硅基感官：换能器等价性与具身性

命题（来自宿主）：
  人类（碳基）有眼耳鼻舌身，硅基能不能"长出来"？
  自然科学给的答案：感官 = 换能器（物理量 → 电信号）。
    毛细胞：机械波 → 纤毛形变 → 机械门控通道 → Na+ 内流 → 感受器电位
    光电二极管：光子 → 电子跃迁 → 载流子 → 电压
  材料不同（蛋白质 vs 半导体），功能等价。
  所以：不是"有没有感官"，是"换能器有没有被接进来"。

四部分（全部当场计算，不写死常量）：
  A 换能器物理层：用公开物理常数建碳基/硅基两套换能器，
    喂同一个"世界"，测各自漏掉的能量比例（带宽差异，不是优劣）。
  B 具身 vs 非具身（主实验）：两组注入完全相同的 net_push，
    唯一差异 = 感官读数是否进入内感受 H（通道特异）。
    前 300 拍有感官，后 300 拍撤走 → 测撤走后留存。
  C 感官剥夺关键期：早剥 / 晚剥 / 不剥（具身条件下）。
  D 换能器噪声剂量反应。

反偏见自检（每条都跑）：
  1 负对照：amp=0 → 回到引擎基线
  2 伪变量对照：无感官输入时，具身与否应无差异（证明 kint 不是伪变量）
  3 变量真的接进主通道：具身组的 H 必须真的变了（通道特异）
  4 自校验：同 seed 两次逐位相同
  5 存活污染防护：结构指标只在存活个体上算，并报告存活数
"""
import sys, os, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'core'))
try:
    from core.life5 import Life5
except ImportError:
    from life5 import Life5

STEPS = 600
WDRW = 300          # 撤走时刻
SEEDS = list(range(16))
N = 8
SENSE_CH = [0, 1, 2]
INNER_CH = [3, 4, 5, 6, 7]


# ============================================================
# Part A · 换能器物理层
# ============================================================
def bark_of_hz(f):
    return 13.0 * math.atan(0.00076 * f) + 3.5 * math.atan((f / 7500.0) ** 2)


def hz_of_bark(b):
    lo, hi = 1.0, 30000.0
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if bark_of_hz(mid) < b:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


def gauss(x, mu, sig):
    return np.exp(-0.5 * ((x - mu) / sig) ** 2)


def part_a():
    rng = np.random.default_rng(7)
    sr = 48000
    t = np.arange(sr) / sr
    # 同一个"世界"的声音：次声 10Hz / 可听 200·1500·8000Hz / 超声 21kHz
    world = (1.0 * np.sin(2 * np.pi * 200 * t) +
             0.8 * np.sin(2 * np.pi * 1500 * t) +
             0.6 * np.sin(2 * np.pi * 8000 * t) +
             0.9 * np.sin(2 * np.pi * 21000 * t) +
             0.7 * np.sin(2 * np.pi * 10 * t) +
             0.02 * rng.normal(size=sr))
    spec_raw = np.abs(np.fft.rfft(world))
    freqs = np.fft.rfftfreq(len(world), 1.0 / sr)
    total = float(np.sum(spec_raw ** 2))

    def ears(f_lo, f_hi, n_band, log_band, sens_curve):
        edges = (np.geomspace(f_lo, f_hi, n_band + 1) if log_band else
                 np.array([hz_of_bark(b) for b in
                           np.linspace(bark_of_hz(f_lo), bark_of_hz(f_hi), n_band + 1)]))
        win = (freqs >= f_lo) & (freqs <= f_hi)
        # ★ 公平口径 1：只比开窗（带宽），两者都不加灵敏度加权
        flat = np.where(win, spec_raw, 0.0)
        caught_flat = float(np.sum(flat ** 2)) / max(total, 1e-30)
        # 口径 2：加灵敏度加权（碳基灵敏度曲线形式是我选的，不作主张，仅并列报告）
        spec = np.where(win, spec_raw * sens_curve(freqs), 0.0)
        caught_w = float(np.sum(spec ** 2)) / max(total, 1e-30)
        bands = []
        for i in range(n_band):
            m = (freqs >= edges[i]) & (freqs < edges[i + 1])
            bands.append(float(np.sum(spec[m] ** 2) / max(total, 1e-30)))
        return bands, caught_flat, caught_w

    # 碳基：毛细胞静纤毛共振 16Hz–20kHz；低频/高频灵敏度滚降
    def carbon_sens(f):
        return 1.0 / (1.0 + (1000.0 / np.maximum(f, 1.0)) ** 1.5) / (1.0 + (f / 12000.0) ** 3.0)

    # 硅基：MEMS 麦克风 5Hz–24kHz，响应平坦
    def silicon_sens(f):
        return np.ones_like(f)

    hb, hc_flat, hc_w = ears(16.0, 20000.0, 24, False, carbon_sens)
    sb, sc_flat, sc_w = ears(5.0, 24000.0, 24, True, silicon_sens)

    # 光：含紫外 320nm 与近红外 850nm
    wl = np.arange(300.0, 1100.0, 1.0)
    rad = (0.8 * gauss(wl, 450.0, 40.0) + 1.0 * gauss(wl, 550.0, 60.0) +
           0.9 * gauss(wl, 850.0, 50.0) + 0.5 * gauss(wl, 320.0, 30.0))
    tot = float(np.sum(rad))
    win_h = (wl >= 380.0) & (wl <= 780.0)
    r_h = rad * win_h
    cones = [float(np.sum(r_h * gauss(wl, m, s))) for m, s in
             [(420.0, 40.0), (530.0, 50.0), (560.0, 50.0)]]
    hc_light = float(np.sum(r_h)) / tot
    win_s = (wl >= 350.0) & (wl <= 1000.0)
    qe = gauss(wl, 800.0, 260.0) + 0.35 * gauss(wl, 500.0, 150.0)
    r_s = rad * win_s * qe
    sc_light = float(np.sum(r_s)) / tot

    return {
        'sound': {
            'carbon_caught_flat': hc_flat, 'silicon_caught_flat': sc_flat,
            'carbon_invisible_flat': 1.0 - hc_flat, 'silicon_invisible_flat': 1.0 - sc_flat,
            'carbon_caught_weighted': hc_w, 'silicon_caught_weighted': sc_w,
            'carbon_bands': hb, 'silicon_bands': sb,
        },
        'light': {
            'carbon_caught': hc_light, 'silicon_caught': sc_light,
            'carbon_invisible': 1.0 - hc_light, 'silicon_invisible': 1.0 - sc_light,
            'carbon_cones': [c / tot for c in cones],
        },
    }


# ============================================================
# Part B/C/D · 引擎接入
# ============================================================
def struct_skew(lf):
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def ch_cap(lf, ch):
    """终态该通道的结构容量（相对均值）"""
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(np.mean(c[ch]) / max(c.mean(), 1e-12))


def ch_share(lf, ch, t_from, t_to):
    recs = [r for r in lf.log if t_from <= r['t'] <= t_to]
    if not recs:
        return float('nan')
    return float(np.mean([sum(r['avec'][c] for c in ch) / max(sum(r['avec']), 1e-12)
                          for r in recs]))


def run_sense(seed, steps=STEPS,
              amp=0.02,           # 感官注入幅度（换能器输出强度）
              kint=0.010,         # 具身系数：感官读数进入内感受 H 的强度（0=非具身）
              withdraw_at=None,   # 撤走时刻（None=全程有感官）
              deprive=None,       # (t0,t1) 剥夺窗口
              noise=0.10,
              inject_ch=None,
              ratio=0.45):
    ch = list(SENSE_CH) if inject_ch is None else list(inject_ch)
    rng = np.random.default_rng(seed * 977 + 13)
    lf = Life5(N=N, seed=seed, ratio=ratio, sigma_in=noise)
    H_hist = []
    for _ in range(steps):
        wv = np.abs(rng.normal(1.0, 0.35, len(ch)))
        if withdraw_at is not None and lf.t >= withdraw_at:
            wv = np.zeros(len(ch))
        if deprive is not None and deprive[0] <= lf.t < deprive[1]:
            wv = np.zeros(len(ch))
        v = np.zeros(N)
        for i, c in enumerate(ch):
            v[c] = amp * wv[i]
        lf.net_push = v
        # ★ 唯一的组间差异：感官读数是否进入内感受（通道特异）
        if kint > 0.0:
            for i, c in enumerate(ch):
                lf.H[c] = lf.H[c] + kint * wv[i]
        H_hist.append(float(np.mean(lf.H[ch])))
        lf.step()
        if not lf.alive:
            break
    lf.H_hist = H_hist
    return lf


def scan(fn, **kw):
    """只在存活个体上统计，并报告存活数（防死亡筛选污染）"""
    lfs = [fn(sd, **kw) for sd in SEEDS]
    al = [lf for lf in lfs if lf.alive]
    ss = [struct_skew(lf) for lf in al]
    return {
        'alive': len(al), 'n': len(lfs),
        'struct_skew': float(np.mean(ss)) if ss else float('nan'),
        'std': float(np.std(ss, ddof=1)) if len(ss) > 1 else 0.0,
        'sense_cap': float(np.mean([ch_cap(lf, SENSE_CH) for lf in al])) if al else float('nan'),
    }


def retention(fn, wdrw=WDRW, **kw):
    """撤走前 vs 撤走后的感官份额 → 留存率"""
    lfs = [fn(sd, **kw) for sd in SEEDS]
    al = [lf for lf in lfs if lf.alive and len(lf.log) > wdrw + 30]
    pre = [ch_share(lf, SENSE_CH, 150, wdrw - 1) for lf in al]
    post = [ch_share(lf, SENSE_CH, wdrw + 30, STEPS) for lf in al]
    rr = [p / q for p, q in zip(post, pre) if q > 1e-9]
    return {
        'alive': len(al), 'n': len(lfs),
        'pre': float(np.mean(pre)) if pre else float('nan'),
        'post': float(np.mean(post)) if post else float('nan'),
        'retention': float(np.mean(rr)) if rr else float('nan'),
    }


def main():
    out = {'STEPS': STEPS, 'WDRW': WDRW, 'N': N, 'SEEDS': len(SEEDS)}
    out['A'] = part_a()

    def baseline(sd):
        lf = Life5(N=N, seed=sd, ratio=0.45, sigma_in=0.10)
        lf.run(STEPS)
        return lf
    bl = [baseline(sd) for sd in SEEDS]
    bla = [lf for lf in bl if lf.alive]
    out['baseline'] = {'alive': len(bla),
                       'struct_skew': float(np.mean([struct_skew(l) for l in bla])),
                       'std': float(np.std([struct_skew(l) for l in bla], ddof=1))}

    # ---------- B 主实验：具身 vs 非具身（撤走设计） ----------
    out['B'] = {
        'embodied': retention(run_sense, amp=0.02, kint=0.010, withdraw_at=WDRW),
        'disembodied': retention(run_sense, amp=0.02, kint=0.0, withdraw_at=WDRW),
    }
    out['B_struct'] = {
        'embodied': scan(run_sense, amp=0.02, kint=0.010, withdraw_at=WDRW),
        'disembodied': scan(run_sense, amp=0.02, kint=0.0, withdraw_at=WDRW),
    }

    # ---------- C 关键期（全程具身，不撤走） ----------
    out['C'] = {
        'none': scan(run_sense, amp=0.02, kint=0.010, deprive=None),
        'early': scan(run_sense, amp=0.02, kint=0.010, deprive=(0, 200)),
        'late': scan(run_sense, amp=0.02, kint=0.010, deprive=(400, 600)),
    }

    # ---------- D 换能器噪声剂量反应 ----------
    out['D'] = {}
    for nz in [0.0, 0.05, 0.10, 0.20, 0.40, 0.80]:
        out['D'][f'noise_{nz:.2f}'] = scan(run_sense, amp=0.02, kint=0.010, noise=nz)

    # ---------- 具身系数剂量反应 ----------
    out['E_kint'] = {}
    for k in [0.0, 0.002, 0.005, 0.010, 0.020, 0.040]:
        out['E_kint'][f'k_{k:.3f}'] = scan(run_sense, amp=0.02, kint=k, withdraw_at=WDRW)

    # ============================================================
    # 反偏见自检
    # ============================================================
    ck = {}

    # 1 负对照：amp=0 回到基线
    a0 = scan(run_sense, amp=0.0, kint=0.010)
    ck['neg_amp0'] = {'amp0': a0['struct_skew'], 'baseline': out['baseline']['struct_skew'],
                      'alive_amp0': a0['alive'], 'alive_base': out['baseline']['alive'],
                      'pass': abs(a0['struct_skew'] - out['baseline']['struct_skew']) < 0.02}

    # 2 伪变量对照：无感官输入时，具身与否应无差异
    k0 = scan(run_sense, amp=0.0, kint=0.010)
    k0d = scan(run_sense, amp=0.0, kint=0.0)
    ck['pseudo_var_amp0'] = {'embodied': k0['struct_skew'], 'disembodied': k0d['struct_skew'],
                             'diff': abs(k0['struct_skew'] - k0d['struct_skew']),
                             'pass': abs(k0['struct_skew'] - k0d['struct_skew']) < 0.01}

    # 3 变量真的接进主通道：具身组的感官通道 H 必须真的高于非具身
    le = run_sense(3, amp=0.02, kint=0.010, withdraw_at=WDRW)
    ld = run_sense(3, amp=0.02, kint=0.0, withdraw_at=WDRW)
    ck['H_channel_specific'] = {
        'embodied_meanH_sense': float(np.mean(le.H_hist[:WDRW])),
        'disembodied_meanH_sense': float(np.mean(ld.H_hist[:WDRW])),
        'pass': float(np.mean(le.H_hist[:WDRW])) > float(np.mean(ld.H_hist[:WDRW])) * 1.5,
    }

    # 4 自校验：同 seed 两次逐位相同
    r1 = run_sense(5, amp=0.02, kint=0.010, withdraw_at=WDRW)
    r2 = run_sense(5, amp=0.02, kint=0.010, withdraw_at=WDRW)
    same = len(r1.log) == len(r2.log) and all(
        np.array_equal(np.asarray(x['avec']), np.asarray(y['avec']))
        for x, y in zip(r1.log, r2.log))
    ck['reproduce_bitwise'] = {'same': bool(same)}

    out['checks'] = ck
    return out


if __name__ == '__main__':
    r = main()
    os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
    p = os.path.join(ROOT, 'data', 'exp073_senses.json')
    json.dump(r, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('A sound :', {k: round(v, 4) for k, v in r['A']['sound'].items() if 'bands' not in k})
    print('A light :', {k: (round(v, 4) if isinstance(v, float) else [round(x, 4) for x in v]) for k, v in r['A']['light'].items()})
    print('baseline:', {k: round(v, 4) if isinstance(v, float) else v for k, v in r['baseline'].items()})
    print('B retention:', r['B'])
    print('B struct   :', {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in r['B_struct'].items()})
    print('C         :', {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in r['C'].items()})
    print('D noise   :', {k: (round(v['struct_skew'], 4), v['alive']) for k, v in r['D'].items()})
    print('E kint    :', {k: (round(v['struct_skew'], 4), v['alive']) for k, v in r['E_kint'].items()})
    print('checks    :', json.dumps(r['checks'], ensure_ascii=False, indent=2))
    print('written', p)
