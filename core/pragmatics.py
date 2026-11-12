# -*- coding: utf-8 -*-
"""
★92 理解人（语用 + 人的节奏）

她能读到的：
  - 字面内容 lit（符号层，确定读到，但可能不等于人的真实意图）
  - 副语言线索 cue（真人语音的节奏/停顿/语气，有噪）
  - 静音的长度（她的耳朵测，有噪）
她读不到的：
  - 人的真实意图 intent（ground truth，只用于评分）
  - 人是不是说完了（只能从静音长度推断）

真人数值（本仓库实测，35 段真人中文语音 data/cn_voice + data/dialog_voice）：
  REAL_FINAL_PAUSE = [0.192 .. 2.192]，中位 0.52 s   ← 句末停顿分布（实测，双峰）
  REAL_EVENT_RATE  = 2.48 /s                        ← 语音事件率（能量包络上升段计数，偏保守）
  REAL_FTO_OK      = 0.25 s                         ← 话轮间隔舒适区上界（★71 实测 0~250ms）
  REAL_VOICED      = 0.656

★★ 这一课最反直觉的物理（也是"用自己的度量衡理解人"的真正难点）：
  她的时钟再快，也不能让她更快听懂人。
    收益（听清多少）的上界由【人的语音事件率】决定 —— 不由她的 f_clk 决定。
    代价（算多久烧多少电）才由【她的 f_clk】决定。
  所以理解人这件事上：
    收益的单位是人的（事件/秒），成本的单位是她的（t0、焦耳）。
    两套单位必须同时用，转换因子不由她定。

单位：
  t0 = 1/f_clk（她的自然时间单位，★88）
  τ 给秒（人的节奏以秒计），同时报 τ̂ = τ / t0（她的单位）
"""

import numpy as np

# ---------------------------------------------------------------- 真人数值
REAL_FINAL_PAUSE = np.array([
    0.192, 0.192, 0.192, 0.192, 0.192, 0.192, 0.200, 0.208, 0.208, 0.208,
    0.208, 0.208, 0.208, 0.216, 0.224, 0.240, 0.256, 0.520, 0.528, 0.528,
    0.528, 0.536, 0.584, 0.584, 0.592, 0.960, 0.976, 1.000, 1.008, 1.048,
    1.056, 1.056, 1.568, 1.584, 2.192])
REAL_EVENT_RATE = 2.48
REAL_FTO_OK = 0.25
REAL_VOICED = 0.656

F_CLK_DEFAULT = 2.4e9
T0_DEFAULT = 1.0 / F_CLK_DEFAULT

# ---------------------------------------------------------------- 意图类别
K = 5
NAMES = ['直接同意', '直接拒绝', '委婉拒绝', '反话', '回避']
DIRECT = np.array([True, True, False, False, False])
CUE_INFO_BY_CLASS = np.array([0.30, 0.30, 1.30, 1.20, 1.40])
LIT_STRENGTH = 2.2

# ---------------------------------------------------------------- 评分常数
W_CORRECT = 1.0
W_WRONG = -1.5          # 误解比没听懂更糟（不对称）
W_ABSTAIN = -0.15       # "我不确定"，人得重说一遍
W_INTERRUPT = -1.0      # 打断人说话（REAL：比慢更失礼）
ANCHOR_CONFLICT = 0.25
SHUFFLE_CONF = False        # 仅用于判据对照：置信度是否携带信息
FB_RATE = 0.35              # 人给出"你听懂了没有"的信号的概率（真实对话的反馈通路）
                            # abstain 时代价已付，人重说 → 一定拿到真值


def t0_of(f_clk):
    return 1.0 / f_clk


def sample_stream(n, rng, p_lit, cue_noise, f_clk=F_CLK_DEFAULT,
                  event_rate=REAL_EVENT_RATE, fto_ok=REAL_FTO_OK,
                  intra_lo=0.25, intra_hi=0.55, fb_rate=FB_RATE):
    """生成一段"人在说话"的流。intent 是 ground truth，绝不给她。"""
    intent = rng.integers(0, K, size=n)
    lit = intent.copy()
    flip = rng.random(n) >= p_lit
    if flip.any():
        others = (intent[flip][:, None] + rng.integers(1, K, size=(flip.sum(), 1))) % K
        lit[flip] = others[:, 0]

    nseg = rng.integers(1, 5, size=n)                       # 一句话分几段说完
    segd = rng.uniform(0.35, 1.10, size=(n, 4))             # 每段语音时长(s)
    Q = rng.choice(REAL_FINAL_PAUSE, size=n)                # 句末停顿（实测分布）
    u = rng.uniform(intra_lo, intra_hi, size=(n, 3))        # 句内停顿 = Q*u（建模假设：短于句末）
    intra = Q[:, None] * u
    return dict(intent=intent, lit=lit, nseg=nseg, segd=segd, Q=Q, intra=intra,
                p_lit=p_lit, cue_noise=cue_noise, f_clk=f_clk,
                event_rate=event_rate, fto_ok=fto_ok, fb_rate=fb_rate)


def respond_index(stream, i, tau):
    """
    她在第几个停顿开口：第一个长度 ≥ tau 的停顿。
    返回 (idx, interrupted)
      idx < nseg-1 → 那是句内停顿，人还要接着说 → 打断
    """
    ns = int(stream['nseg'][i])
    for j in range(ns - 1):
        if stream['intra'][i, j] >= tau:
            return j, True
    return ns - 1, False


def heard_speech(stream, i, idx):
    return float(np.sum(stream['segd'][i, :idx + 1]))


def observe(stream, i, tau, rng, cue_gain=1.0, sil_noise=0.06):
    """
    她听到的副语言线索。精度只由【人的事件率 × 她实际听到的时长】决定。
    与她的 f_clk 无关 —— 这是这一课的物理核心。
    """
    idx, inter = respond_index(stream, i, tau)
    # 她测到的静音长度有噪（★83 修过的耳朵，MAE 0.0091；这里给更保守的噪声）
    S = heard_speech(stream, i, idx)
    n_eff = max(1.0, S * stream['event_rate'])
    it = int(stream['intent'][i])
    sd = stream['cue_noise'] / np.sqrt(n_eff)
    info = CUE_INFO_BY_CLASS[it] * cue_gain
    logit = np.full(K, 0.0)
    logit[it] = info
    # 只听了一半 → 线索整体变弱（后半句才是关键）
    frac = (idx + 1) / int(stream['nseg'][i])
    logit = logit + rng.normal(0.0, sd / max(frac, 0.3), size=K)
    return logit - logit.max(), inter, idx


def posterior(lit, cue_logit, alpha):
    lit_logit = np.full(K, -LIT_STRENGTH)
    lit_logit[lit] = 0.0
    z = (1.0 - alpha) * lit_logit + alpha * cue_logit
    z = z - z.max()
    p = np.exp(z)
    return p / p.sum()


def wait_cost(tau, fto_ok, w_wait=0.45):
    """应答延迟：超过真人舒适话轮间隔上界（250ms）开始扣分。"""
    over = max(0.0, tau - fto_ok)
    return w_wait * over / max(fto_ok, 1e-6)


def compute_cost(tau, heard, f_clk, w_compute=0.30):
    """她自己的算力/能耗 ∝ f_clk ×（听 + 想）的时长。她的时钟只出现在这里。"""
    return w_compute * (f_clk / F_CLK_DEFAULT) * (heard + tau)


def judge(stream, i, params, tau, rng, state=None, cue_gain=1.0):
    alpha0 = params['alpha0']; beta = params['beta']; theta = params['theta']
    c0 = params.get('c0', ANCHOR_CONFLICT)
    cr = state['conflict_rate'] if state is not None else c0
    if params.get('use_fb', True) and state is not None and 'e_lit' in state:
        # 有反馈时的规则：哪边错得多，就少信哪边
        alpha = float(np.clip(alpha0 + beta * (state['e_lit'] - state['e_cue']), 0.0, 1.0))
    else:
        # 无反馈时只能靠冲突率这个有偏代理
        alpha = float(np.clip(alpha0 + beta * (cr - c0), 0.0, 1.0))
    lit = int(stream['lit'][i])
    cue, inter, idx = observe(stream, i, tau, rng, cue_gain=cue_gain)
    p = posterior(lit, cue, alpha)
    conf = float(p.max())
    if SHUFFLE_CONF:                      # 尺子对照：把置信度换成无信息的
        conf = float(rng.random())
    conflict = int(np.argmax(cue) != lit)
    branch = 'lit' if alpha < 0.5 else 'cue'
    if conf < theta:
        return dict(act='abstain', g=None, conf=conf, conflict=conflict,
                    inter=inter, idx=idx, heard=heard_speech(stream, i, idx),
                    alpha=alpha, branch=branch)
    return dict(act='guess', g=int(np.argmax(p)), conf=conf, conflict=conflict,
                inter=inter, idx=idx, heard=heard_speech(stream, i, idx),
                alpha=alpha, branch=branch)


def run_episode(stream, params, tau, rng, w_wait=0.45, w_compute=0.30,
                cue_gain=1.0, window=12, return_detail=False, kw_decay=0.10):
    n = len(stream['intent'])
    score = 0.0
    n_c = n_w = n_a = n_i = 0
    conflict_hist = []
    ok_guess, conf_guess, conf_abs = [], [], []
    fb_rate = stream.get('fb_rate', FB_RATE)
    decay = kw_decay if False else 0.10
    e_lit = e_cue = 0.0
    n_lit = n_cue = 0.0
    state = {'conflict_rate': ANCHOR_CONFLICT, 'e_lit': 0.0, 'e_cue': 0.0}
    for i in range(n):
        state['e_lit'] = e_lit if n_lit > 0.5 else 0.0
        state['e_cue'] = e_cue if n_cue > 0.5 else 0.0
        d = judge(stream, i, params, tau, rng, state, cue_gain=cue_gain)
        conflict_hist.append(d['conflict'])
        if len(conflict_hist) > window:
            conflict_hist.pop(0)
        state['conflict_rate'] = float(np.mean(conflict_hist))
        if d['inter']:
            score += W_INTERRUPT; n_i += 1
        score -= wait_cost(tau, stream['fto_ok'], w_wait)
        score -= compute_cost(tau, d['heard'], stream['f_clk'], w_compute)
        truth = int(stream['intent'][i])
        got_fb = False
        if d['act'] == 'abstain':
            score += W_ABSTAIN; n_a += 1; conf_abs.append(d['conf'])
            got_fb = True                       # 人重说 → 一定拿到真值
        else:
            conf_guess.append(d['conf'])
            if d['g'] == truth:
                score += W_CORRECT; n_c += 1; ok_guess.append(1)
            else:
                score += W_WRONG; n_w += 1; ok_guess.append(0)
            got_fb = bool(rng.random() < fb_rate)
        if got_fb:
            # 误差归因：这一票押在字面还是线索？押错了就记在那边的账上
            if d['act'] == 'abstain':
                wrong = 1.0        # 没听懂，两边都算没接住
                e_lit = (1 - decay) * e_lit + decay * wrong; n_lit = (1 - decay) * n_lit + decay
                e_cue = (1 - decay) * e_cue + decay * wrong; n_cue = (1 - decay) * n_cue + decay
            else:
                wrong = 0.0 if d['g'] == truth else 1.0
                if d['branch'] == 'lit':
                    e_lit = (1 - decay) * e_lit + decay * wrong; n_lit = (1 - decay) * n_lit + decay
                else:
                    e_cue = (1 - decay) * e_cue + decay * wrong; n_cue = (1 - decay) * n_cue + decay
    out = dict(score=score / n,
               acc=n_c / max(1, n_c + n_w),
               acc_guess=float(np.mean(ok_guess)) if ok_guess else float('nan'),
               abstain_rate=n_a / n, interrupt_rate=n_i / n,
               wrong_rate=n_w / n,
               mean_conf_guess=float(np.mean(conf_guess)) if conf_guess else float('nan'),
               mean_conf_abs=float(np.mean(conf_abs)) if conf_abs else float('nan'))
    if return_detail:
        out['_conf_guess'] = conf_guess; out['_ok_guess'] = ok_guess
    return out


def evaluate(envs, params, tau, seed=0, n_ep=6, **kw):
    rng = np.random.default_rng(seed)
    per = []
    for e in envs:
        vals = []
        for _ in range(n_ep):
            st = sample_stream(e['n'], rng, p_lit=e['p_lit'], cue_noise=e['cue_noise'],
                               f_clk=e.get('f_clk', F_CLK_DEFAULT),
                               event_rate=e.get('event_rate', REAL_EVENT_RATE),
                               fto_ok=e.get('fto_ok', REAL_FTO_OK),
                               intra_lo=e.get('intra_lo', 0.25),
                               intra_hi=e.get('intra_hi', 0.55),
                               fb_rate=e.get('fb_rate', FB_RATE))
            vals.append(run_episode(st, params, tau, rng,
                                    cue_gain=e.get('cue_gain', 1.0), **kw)['score'])
        per.append(float(np.mean(vals)))
    return float(np.mean(per)), per
