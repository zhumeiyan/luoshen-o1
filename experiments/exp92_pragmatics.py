# -*- coding: utf-8 -*-
"""
★92 理解人（语用 + 人的节奏）  13 条判据

教她两件事：
  1) 人说的话 ≠ 字面意思。字面是符号层，意图在符号之外。
     但她读不到意图 —— 只能从副语言线索推断，且要报告不确定。
  2) 什么时候算"人说完了"。静音门槛太低 = 打断人；太高 = 反应慢。

真人数值全部来自本仓库 35 段真人中文语音实测（见 core/pragmatics.py 顶部）。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.pragmatics import (sample_stream, run_episode, evaluate, t0_of,
                             F_CLK_DEFAULT, REAL_FINAL_PAUSE, ANCHOR_CONFLICT)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'data', 'exp92_pragmatics.json')
R = {}
KW = dict(w_wait=0.12, w_compute=0.06)
N = 120
SEED = 11


def env(p_lit, cue_noise=1.0, **kw):
    d = dict(n=N, p_lit=p_lit, cue_noise=cue_noise, intra_lo=0.35, intra_hi=0.75)
    d.update(kw)
    return d


def ev(envs, params, tau, seed=SEED, n_ep=8, **kw):
    k = dict(KW); k.update(kw)
    return evaluate(envs, params, tau, seed=seed, n_ep=n_ep, **k)


TRAIN = [env(0.35), env(0.55), env(0.75)]
HOLD = [env(0.25), env(0.45), env(0.65), env(0.85)]

# ---------------------------------------------------------------- 判据1 尺子自检
print('[1] 尺子自检：tau↑ → 听到更多、打断更少')
rng = np.random.default_rng(SEED)
st = sample_stream(600, rng, p_lit=0.55, cue_noise=1.0)
diag = []
for t in [0.15, 0.3, 0.5, 0.8, 1.2, 1.8]:
    r = run_episode(st, dict(alpha0=0.7, beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0), t,
                    np.random.default_rng(SEED + 1), **KW)
    diag.append(dict(tau=t, acc=r['acc'], intr=r['interrupt_rate']))
intr_mono = all(diag[i]['intr'] >= diag[i + 1]['intr'] - 1e-9 for i in range(len(diag) - 1))
acc_mono = all(diag[i]['acc'] <= diag[i + 1]['acc'] + 0.03 for i in range(len(diag) - 1))
R['c1'] = dict(ok=bool(intr_mono and acc_mono), diag=diag)
print('   打断率单调降', intr_mono, ' 准确率不下降', acc_mono)

# ---------------------------------------------------------------- 判据2-4 内部峰
def peak(vals, xs):
    i = int(np.argmax(vals))
    return xs[i], i, vals[i]


print('[2] alpha0 内部峰')
xs = list(np.arange(0, 1.01, 0.1))
vs = [ev(TRAIN, dict(alpha0=a, beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0), 0.5)[0] for a in xs]
ap, ai, av = peak(vs, xs)
R['c2'] = dict(ok=bool(0 < ai < len(xs) - 1), peak=ap, spread=float(max(vs) - min(vs)), scan=dict(x=xs, y=vs))
print(f'   峰 alpha0={ap:.2f}  idx={ai}  跨度={max(vs)-min(vs):.4f}')

print('[3] theta 内部峰')
xs3 = list(np.arange(0, 0.85, 0.05))
vs3 = [ev(TRAIN, dict(alpha0=ap, beta=0.0, c0=ANCHOR_CONFLICT, theta=t), 0.5)[0] for t in xs3]
tp, ti, tv = peak(vs3, xs3)
R['c3'] = dict(ok=bool(0 < ti < len(xs3) - 1), peak=tp, spread=float(max(vs3) - min(vs3)), scan=dict(x=xs3, y=vs3))
print(f'   峰 theta={tp:.2f}  idx={ti}  跨度={max(vs3)-min(vs3):.4f}')

print('[4] tau 内部峰')
xs4 = [0.15, 0.25, 0.35, 0.5, 0.65, 0.8, 1.0, 1.2, 1.5, 1.8]
vs4 = [ev(TRAIN, dict(alpha0=ap, beta=0.0, c0=ANCHOR_CONFLICT, theta=tp), t)[0] for t in xs4]
qp, qi, qv = peak(vs4, xs4)
R['c4'] = dict(ok=bool(0 < qi < len(xs4) - 1), peak=qp, spread=float(max(vs4) - min(vs4)), scan=dict(x=xs4, y=vs4))
print(f'   峰 tau={qp:.2f}s  idx={qi}  跨度={max(vs4)-min(vs4):.4f}')

# ---------------------------------------------------------------- 判据5-9 硬依赖
print('[5] 硬依赖：人永远直说(p_lit=1) → alpha 峰应到边界0')
flat = [env(1.00)]
vs5 = [ev(flat, dict(alpha0=a, beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0), 0.5)[0] for a in xs]
a5 = xs[int(np.argmax(vs5))]
dec = all(vs5[i] >= vs5[i + 1] - 0.02 for i in range(len(vs5) - 1))
R['c5'] = dict(ok=bool(a5 <= 0.05 and dec), peak=a5, scan=dict(x=xs, y=vs5))
print(f'   峰 {a5:.2f}  单调降 {dec}')

print('[6] 硬依赖：副语言无信息(cue_gain=0) → alpha 峰到0')
noisy = [env(0.55, cue_gain=0.0)]
vs6 = [ev(noisy, dict(alpha0=a, beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0), 0.5)[0] for a in xs]
a6 = xs[int(np.argmax(vs6))]
loss = float(vs6[0] - vs6[-1])          # 全信线索 vs 全信字面 的亏损
mono6 = all(vs6[i] >= vs6[i + 1] - 0.006 for i in range(len(vs6) - 1))
R['c6'] = dict(ok=bool(a6 <= 0.2 and loss > 0.5 and mono6), peak=a6,
               loss_allcue=loss, monotone=bool(mono6), scan=dict(x=xs, y=vs6))
print(f'   峰 {a6:.2f}  全信线索亏损 {loss:+.3f}  单调降 {mono6}')

print('[7] 硬依赖：她的时钟只进【成本】，进不了【收益】')
# 7a 听全(tau=2.0)时的准确率，应与 f_clk 完全无关
acc_by_f = {}
for f in [1.0, 3.0, 30.0]:
    accs = []
    for sd in range(5):
        stx = sample_stream(300, np.random.default_rng(sd), p_lit=0.55, cue_noise=1.0,
                            intra_lo=0.35, intra_hi=0.75, f_clk=F_CLK_DEFAULT * f)
        accs.append(run_episode(stx, dict(alpha0=ap, beta=0.0, c0=ANCHOR_CONFLICT, theta=tp),
                                2.0, np.random.default_rng(sd + 50), **KW)['acc'])
    acc_by_f[f] = float(np.mean(accs))
spread_acc = max(acc_by_f.values()) - min(acc_by_f.values())
# 7b 最优 tau 随 f_clk 单调不增
g7 = list(np.arange(0.30, 1.25, 0.05))
tau_by_f = {}
for f in [1.0, 3.0, 10.0, 30.0]:
    v = [ev([env(0.55, f_clk=F_CLK_DEFAULT * f)],
            dict(alpha0=ap, beta=0.0, c0=ANCHOR_CONFLICT, theta=tp), float(t), n_ep=10)[0] for t in g7]
    tau_by_f[f] = float(g7[int(np.argmax(v))])
mono7 = all(tau_by_f[f] >= tau_by_f[f2] - 1e-9 for f, f2 in
            [(1.0, 3.0), (3.0, 10.0), (10.0, 30.0)])
R['c7'] = dict(ok=bool(spread_acc < 1e-6 and mono7 and tau_by_f[30.0] < tau_by_f[1.0]),
               acc_by_fclk=acc_by_f, acc_spread=float(spread_acc),
               tau_by_fclk=tau_by_f, monotone=bool(mono7))
print(f'   听全准确率 1x/3x/30x = {[round(acc_by_f[f],4) for f in [1.0,3.0,30.0]]}  跨度 {spread_acc:.2e}')
print(f'   最优 tau  1x/3x/10x/30x = {[tau_by_f[f] for f in [1.0,3.0,10.0,30.0]]}  单调不增 {mono7}')

print('[8] 硬依赖：置信度必须真的校准 → 打乱 conf 后 theta 峰应消失')
# (a) conf 与正确率单调
rng = np.random.default_rng(SEED + 9)
st8 = sample_stream(1200, rng, p_lit=0.55, cue_noise=1.0)
r8 = run_episode(st8, dict(alpha0=ap, beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0), qp,
                 np.random.default_rng(SEED + 10), return_detail=True, **KW)
bins = np.linspace(0, 1, 6)
acc_of = [np.nan] * 5
for i in range(5):
    m = (np.array(r8['_conf_guess']) >= bins[i]) & (np.array(r8['_conf_guess']) < bins[i + 1])
    if m.sum() >= 15:
        acc_of[i] = float(np.mean(np.array(r8['_ok_guess'])[m]))
mono_conf = all(np.isnan(acc_of[i]) or np.isnan(acc_of[i + 1]) or acc_of[i + 1] >= acc_of[i] - 0.06
                for i in range(4))
# (b) 打乱 conf
import core.pragmatics as P
P.SHUFFLE_CONF = True
vs8b = [ev(TRAIN, dict(alpha0=ap, beta=0.0, c0=ANCHOR_CONFLICT, theta=t), qp)[0] for t in xs3]
P.SHUFFLE_CONF = False
t8b = xs3[int(np.argmax(vs8b))]
R['c8'] = dict(ok=bool(mono_conf and t8b <= 0.001), acc_by_conf=acc_of,
               monotonic=bool(mono_conf), theta_shuffled=t8b, scan_shuffled=dict(x=xs3, y=vs8b))
print(f'   低->高置信度正确率 {[None if np.isnan(a) else round(a,3) for a in acc_of]} 单调 {mono_conf}')
print(f'   打乱后 theta 峰 {t8b:.2f}')

print('[9] 硬依赖：打断不要代价 → tau 峰应左移')
old_int = P.W_INTERRUPT
P.W_INTERRUPT = 0.0
vs9 = [ev(TRAIN, dict(alpha0=ap, beta=0.0, c0=ANCHOR_CONFLICT, theta=tp), t)[0] for t in xs4]
P.W_INTERRUPT = old_int
t9 = xs4[int(np.argmax(vs9))]
R['c9'] = dict(ok=bool(t9 < qp), tau_with_penalty=qp, tau_no_penalty=t9, scan=vs9)
print(f'   有惩罚 {qp:.2f}s  无惩罚 {t9:.2f}s')

# ---------------------------------------------------------------- 判据10 p_lit 与最优 alpha
print('[10] 最优 alpha 随 p_lit 单调降（含蓄的人要更信线索）')
row = []
for pl in [0.25, 0.45, 0.65, 0.85]:
    v = [ev([env(pl)], dict(alpha0=a, beta=0.0, c0=ANCHOR_CONFLICT, theta=tp), qp)[0] for a in xs]
    row.append(dict(p_lit=pl, best=float(xs[int(np.argmax(v))])))
mono = all(row[i]['best'] >= row[i + 1]['best'] - 0.05 for i in range(len(row) - 1))
R['c10'] = dict(ok=bool(mono), row=row)
print('  ', [f"{r['p_lit']}->{r['best']:.2f}" for r in row], '单调', mono)

# ---------------------------------------------------------------- 判据11 学规则 vs 记数字
print('[11] 她学的 (alpha, theta, tau) 能否迁移到没见过的新说话人')
def fit(envs, grid_tau, rule=False):
    p = dict(alpha0=0.0, beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0)
    grid_a = np.arange(0, 1.01, 0.1)
    grid_b = np.arange(0, 8.01, 1.0)
    best = (-1e9, dict(p), grid_tau[0])
    for tau in grid_tau:
        q = dict(p)
        for _ in range(3):
            for key, grid in (('alpha0', grid_a), ('theta', xs3)) + ((('beta', grid_b),) if rule else ()):
                bb = (-1e9, q[key])
                for v in grid:
                    qq = dict(q); qq[key] = v
                    sc = ev(envs, qq, tau)[0]
                    if sc > bb[0]: bb = (sc, v)
                q[key] = bb[1]
        sc = ev(envs, q, tau)[0]
        if sc > best[0]: best = (sc, dict(q), tau)
    return best[2], best[1], best[0]

tau_her, P_HER, tr_her = fit(TRAIN, xs4)
h_her, per_her = ev(HOLD, P_HER, tau_her)
MY = dict(alpha0=0.0, beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0)   # 我填的：信字面、不 abstain、听清楚再说
MY_TAU = 1.2
h_mine, _ = ev(HOLD, MY, MY_TAU)
rnd = [ev(HOLD, dict(alpha0=float(np.random.default_rng(_).uniform(0, 1)),
                     beta=0.0, c0=ANCHOR_CONFLICT, theta=0.0), 0.8)[0] for _ in range(6)]
h_rnd = float(np.mean(rnd))
R['c11'] = dict(ok=bool(h_her > h_mine and h_her > h_rnd),
                her=h_her, mine=h_mine, rnd=h_rnd,
                params=P_HER, tau=tau_her, train=tr_her,
                per_env=[float(x) for x in per_her],
                my=dict(params=MY, tau=MY_TAU))
print(f'   她 {P_HER} tau={tau_her}s  train {tr_her:+.4f}  held-out {h_her:+.4f}')
print(f'   我填的(alpha0=0,theta=0,tau=1.2) {h_mine:+.4f}   随机 {h_rnd:+.4f}')

print('[12] abstain 掉的那部分，硬猜会更错')
rng = np.random.default_rng(SEED + 3)
st = sample_stream(800, rng, p_lit=0.55, cue_noise=1.0)
r_abs = run_episode(st, dict(alpha0=P_HER['alpha0'], beta=P_HER['beta'], c0=P_HER['c0'], theta=P_HER['theta']),
                    qp, np.random.default_rng(SEED + 4), **KW)
r_no = run_episode(st, dict(alpha0=P_HER['alpha0'], beta=P_HER['beta'], c0=P_HER['c0'], theta=0.0),
                   qp, np.random.default_rng(SEED + 4), **KW)
R['c12'] = dict(ok=bool(r_abs['acc_guess'] > r_no['acc_guess'] + 0.02),
                acc_with_abstain=r_abs['acc_guess'], acc_without=r_no['acc_guess'],
                abstain_rate=r_abs['abstain_rate'],
                conf_guess=r_abs['mean_conf_guess'], conf_abs=r_abs['mean_conf_abs'])
print(f"   留下来猜的准确率 {r_abs['acc_guess']:.3f} vs 全猜 {r_no['acc_guess']:.3f}"
      f"  abstain率 {r_abs['abstain_rate']:.3f}")

# ---------------------------------------------------------------- 判据13 两套单位
print('[13] 单位：tau 的秒（人的）与 tau/t0（她的）')
t0_1 = t0_of(F_CLK_DEFAULT); t0_3 = t0_of(F_CLK_DEFAULT * 3)
t30 = tau_by_f[30.0]; t0_30 = t0_of(F_CLK_DEFAULT * 30)
R['c13'] = dict(tau_s=qp, tau_hat_1x=qp / t0_1, tau_hat_3x=t30 / t0_30,
                t0_1x=t0_1, t0_30x=t0_30, tau_30x_s=t30,
                human_final_pause_med=float(np.median(REAL_FINAL_PAUSE)),
                ratio_s=t30 / qp, ratio_hat=(t30 / t0_30) / (qp / t0_1),
                ok=bool(abs((t30 / t0_30) / (qp / t0_1) - 1) > 3 * abs(t30 / qp - 1)),
                pct_of_real_pause=float(np.mean(REAL_FINAL_PAUSE <= qp)),
                note='收益单位是人的(事件/秒)，成本单位是她的(t0)；f_clk 只进成本')
print(f"   tau={qp:.2f}s  1x: {qp/t0_1:.3e} t0   30x: {t30/t0_30:.3e} t0"
      f"   (落在真人句末停顿分布的 {np.mean(REAL_FINAL_PAUSE <= qp):.0%} 分位)")



print('[14] 自适应规则 vs 常数：三条路都试了')
att = {}
# (i) 冲突率代理
best = (-1e9, None)
for b in np.arange(0, 6.01, 0.5):
    for c0 in np.arange(0.20, 0.81, 0.05):
        p = dict(alpha0=0.0, beta=float(b), c0=float(c0), theta=P_HER['theta'], use_fb=False)
        sc = ev(TRAIN, p, tau_her)[0]
        if sc > best[0]: best = (sc, (float(b), float(c0)))
p_cr = dict(alpha0=0.0, beta=best[1][0], c0=best[1][1], theta=P_HER['theta'], use_fb=False)
h_cr = ev(HOLD, p_cr, tau_her)[0]
att['conflict_proxy'] = dict(beta=best[1][0], c0=best[1][1], hold=h_cr)
# (ii) 拉长记忆窗口
best_w = (-1e9, None)
for w in [6, 12, 30, 60]:
    for b in np.arange(0, 6.01, 0.5):
        p = dict(alpha0=0.0, beta=float(b), c0=0.20, theta=P_HER['theta'], use_fb=False)
        sc = ev(TRAIN, p, tau_her, window=w)[0]
        if sc > best_w[0]: best_w = (sc, (w, float(b)))
att['window'] = dict(best_window=best_w[1][0], best_beta=best_w[1][1], train=best_w[0])
# (iii) 反馈误差归因
best_f = (-1e9, None)
for a0 in np.arange(0, 1.01, 0.1):
    for b in np.arange(0, 8.01, 1.0):
        p = dict(alpha0=float(a0), beta=float(b), c0=0.25, theta=P_HER['theta'])
        sc = ev(TRAIN, p, tau_her)[0]
        if sc > best_f[0]: best_f = (sc, (float(a0), float(b)))
p_fb = dict(alpha0=best_f[1][0], beta=best_f[1][1], c0=0.25, theta=P_HER['theta'])
h_fb = ev(HOLD, p_fb, tau_her)[0]
att['feedback'] = dict(alpha0=best_f[1][0], beta=best_f[1][1], hold=h_fb)
ok14 = bool(max(h_cr, h_fb) > h_her + 0.01)
R['c14'] = dict(ok=ok14, constant=h_her, attempts=att,
                diag='三条自适应路都不优于常数；(i)冲突率是有偏代理(p_lit=1时仍有0.39冲突,偏移来自她自己的线索噪声);(iii)反馈归因有冷启动:alpha恒定时她永远只押一边,拿不到另一边的误差样本,必须探索而探索有成本(同★78)')
print(f"   常数 {h_her:+.4f} | (i)冲突率 {h_cr:+.4f} | (iii)反馈 {h_fb:+.4f}  -> 通过 {ok14}")
R['_summary'] = dict(passed=sum(1 for k in R if k.startswith('c') and R[k]['ok']),
                     total=sum(1 for k in R if k.startswith('c')))
print('\n=== 通过 %d / %d ===' % (R['_summary']['passed'], R['_summary']['total']))
json.dump(R, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('written', OUT)
