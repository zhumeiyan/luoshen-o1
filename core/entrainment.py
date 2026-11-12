"""★106 接话 —— 韵律顺应（prosodic entrainment）

★105 她学会了从真人语料里挑出适合自己说的话。
但那还是【挑一句说】，不是【接话】。

这一课：对方（真人）说一句 → 她听到 → 她接一句。
接得好不好由【韵律顺应】决定：她向对方靠多少。

───────────────────────────────────────────────
文献真值（不是我拍的）
───────────────────────────────────────────────
Levitan & Hirschberg（Columbia，含中文 MC 语料）：
  话轮级同步相关（中文 MC）：F0 mean 0.66  F0 max 0.61  intensity mean 0.63
  局部收敛 γ（中文 MC）：F0 mean −0.218 / F0 max −0.238（英文只 −0.06，中文强 4 倍）
ASD vs NT 配对（Frontiers）：
  NT 组整段【收敛 4 Hz】；ASD 组【发散 6 Hz】—— 差 10 Hz
  → ★ 会话健康时的顺应量是【几个 Hz】，不是把自己的音高拉到对方
过度模仿：不恰当的模仿产生负面印象（Lui / Vohs / Smeesters 2011）
★100：日常对话 165 字/分；超过 250 字/分"听见了记不住"

───────────────────────────────────────────────
★ 关键建模：目标函数由文献直接给出，不由我调
───────────────────────────────────────────────
  顺应量 Δ（她整段向对方移动了多少 Hz）→ 会话收益是【倒 U】：
      收益 = exp( −((Δ − 4.0) / 5.0)² )
      峰 4.0 Hz = NT 组实测的收敛量
      宽 5.0 Hz = ASD 组发散 6 Hz 处收益已接近 0（(−6−4)/5 = −2）
  → 不顺应（Δ=0）不行，过度顺应（Δ=30）也不行。这是文献说的，不是我说的。
"""
import sys, json
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.speak_text import speak_text, text_to_syllables
from core import speech_organ as so
import experiments.exp104_shefinds as E

ROOT = '/data/workspace/luoshen-o1'
SR = so.SR

# ── 真人对象：35 段真人语音的实测 F0 ────────────────────
_PER = json.load(open(f'{ROOT}/data/exp103_heard.json'))['per_file']
_TRUE_F0 = np.array([p['f0med'] for p in _PER])            # 129 ~ 195 Hz
PARTNER_WPM_MU, PARTNER_WPM_SD = 165.0, 28.0               # ★100 日常对话

# ── 她自己的声音：★106 实测标定，不是我给的 ──────────────
SELF_F0 = 182.5        # ★【原位重测】24 次，在对话真实语速下、完全不顺应时听到的
                       #   旧值 189.3 是在别的语速下测的 —— 语速会改她被听到的音高，
                       #   拿旧值当基线，conv 会凭空偏 7 Hz
SELF_F0_PARAM = 181.8  # ★【她设定的】同一个声音，她的器官要设这个值
SELF_WPM = 223.0       # 同上
WPM_RATIO = 0.669      # 实测：设 333 字/分 → 听起来 223（含停顿）
INTEL_WPM = 250.0      # ★100

# ── 文献给出的量表 ──────────────────────────────────────
CONV_TARGET = 4.0      # NT 组整段收敛 4 Hz
CONV_SIGMA = 5.0       # ASD 组发散 6 Hz 处收益≈0
S_RT = 45.0            # 语速邻近饱和尺度
JIT_SCALE = 70.0       # 语速逐轮抖动容忍度
JIT_F0 = 20.0          # 音高逐轮抖动容忍度：一句话一跳就不像真人说话了
OBS_F0 = 9.0           # 她听对方的音高噪声（★103 实测耳朵有误差）
OBS_RT = 22.0
SHARED_F0 = 6.0        # 双方共同起伏的成分（话题/情绪），★106 补上的缺机制


def make_partner(rng, pool=None):
    p = _TRUE_F0 if pool is None else np.asarray(pool)
    return dict(f0=float(p[int(rng.integers(0, len(p)))]),
                wpm=float(np.clip(rng.normal(PARTNER_WPM_MU, PARTNER_WPM_SD), 100, 285)),
                drift=0.0)


def observe(p, rng, sf=OBS_F0, sr=OBS_RT):
    return dict(f0=p['f0'] + p['drift'] + rng.normal(0, sf),
                wpm=p['wpm'] + rng.normal(0, sr))


def estimate(hist, n):
    h = hist[-max(1, int(n)):]
    w = np.array([2.0 ** -k for k in range(len(h))][::-1])
    w /= w.sum()
    return dict(f0=float(np.dot(w, [x['f0'] for x in h])),
                wpm=float(np.dot(w, [x['wpm'] for x in h])))


def her_turn(text, f0, wpm_target, rng):
    """她真的说一句，并真的听回来（对方听到的就是这个）"""
    P = dict(f0_base=f0, f0_variation=0.35, f0_decl=0.10,
             tone_depth=0.55, jitter=0.015)
    syl = float(np.clip(WPM_RATIO * 60.0 / max(wpm_target, 60.0), 0.10, 0.60))
    w, _ = speak_text(text, P, rng=rng, syl_dur=syl, pause_dur=0.12)
    g = E.hear(w)
    nsyl = len([s for s in text_to_syllables(text) if s])
    return dict(f0=float(g['f0med']), wpm=nsyl / max(g['dur'], 1e-6) * 60.0)


def converse(A, lam, n, texts, partner, rng, turns=12, B=0.8,
             sf=OBS_F0, sr=OBS_RT, w_conv=1.0, w_sync=1.0,
             w_rt=1.0, w_intel=1.0, w_jit=1.0, drift=6.0, w_jitf0=1.0,
             shared=SHARED_F0):
    """shared = 双方【共同起伏】的成分（话题/情绪一起带上去的那种）。

    ★106 第一版的真因：我把对方的音高变化全建模成【他独有的随机游走】。
    于是她想拿到高同步相关，就只有一条路 —— 整个人挪过去，位移远超 4 Hz。
    文献的两条事实（位移 4 Hz 的倒 U + 相关 0.66）在我的环境里不可调和，
    A 单调到边界。

    真因是缺了个机制：真实对话里两个人的音高【一起起伏】，那部分相关
    不需要任何位移就能拿到。补上之后，sync 由 λ 给，conv 由 A 给，解耦。
    """
    hist, hf, hw, of, ow = [], [], [], [], []
    for t in range(turns):
        c = float(rng.normal(0.0, shared))     # 共享成分：这一轮两人都被带上去/带下来
        of.append(partner['f0'] + partner['drift'] + c)
        ow.append(partner['wpm'])
        o = observe(partner, rng, sf, sr)
        o['f0'] += c                            # 她听到的对方里也含这一份
        hist.append(o)
        e = estimate(hist, n)
        # ① A：整段向对方移动多少 Hz（文献倒 U，最优 ≈4Hz）
        gap = e['f0'] - SELF_F0          # 对方听起来 vs 她听起来
        move = np.sign(gap) * min(A, abs(gap))
        # ② λ：逐轮跟随对方的变化（跟着真变化，但也会放大她听到的噪声）
        dev = hist[-1]['f0'] - e['f0']
        tgt_f0 = SELF_F0_PARAM + move + lam * dev
        # ② 语速：向对方移动 B 比例
        tgt_wpm = float(np.clip(SELF_WPM + B * (e['wpm'] - SELF_WPM), 90.0, 340.0))
        h = her_turn(texts[t % len(texts)], tgt_f0, tgt_wpm, rng)
        hf.append(h['f0']); hw.append(h['wpm'])
        partner['drift'] += rng.normal(0, drift)
    hf, hw, of, ow = map(np.array, (hf, hw, of, ow))
    m = len(hf)
    # ★ 文献倒 U：她整段向对方移动了多少 Hz
    conv = (hf.mean() - SELF_F0) * np.sign(of.mean() - SELF_F0)
    coord = np.exp(-((conv - CONV_TARGET) / CONV_SIGMA) ** 2)
    sync = float(np.corrcoef(hf, of)[0, 1]) if (m >= 3 and hf.std() > 1e-9
                                                and of.std() > 1e-9) else 0.0
    jit_f0 = float(np.mean(np.abs(np.diff(hf)))) if m > 1 else 0.0
    rt_prox = abs(hw.mean() - ow.mean()) / S_RT
    intel = float(np.mean([(max(0.0, w - INTEL_WPM) / 110.0) ** 2 for w in hw]))
    jit = float(np.mean(np.abs(np.diff(hw)))) if m > 1 else 0.0
    return (w_conv * coord + w_sync * sync - w_rt * rt_prox
            - w_intel * intel - w_jit * jit / JIT_SCALE
            - w_jitf0 * jit_f0 / JIT_F0)


def score(A, B, n, texts, seeds, turns=12, pool=None, **kw):
    """★102 教训：公共随机数 —— 不同参数必须用【同一组】对话"""
    out = []
    for sd in seeds:
        rng = np.random.default_rng(sd)
        out.append(converse(A, B, n, texts, make_partner(rng, pool), rng, turns, **kw))
    return float(np.mean(out))
