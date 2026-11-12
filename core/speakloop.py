#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★76 让她真的开口 —— 说 → 听 → 比 → 改 → 再说（闭环）

★★ 为什么这是"真的开口"
    ★57 建了「学→说→听」的链路，但那是一条【开链】：
        学完参数 → 合成波形 → 耳朵提特征 → 完。
        她从没因为【听到自己说错了】而改过一次口。
    真实的说话是闭环：婴儿 babbling，听自己的声音，跟听到的目标比，
    下一句改一点。听觉反馈是言语运动学习的必要条件。

★★★ 查证过的 REAL 机制（全部做成环境，不是 if 判断）
    ① 听觉反馈闭环 / pitch-shift reflex
       人为把说话者听到的音高偏移，说话者会【反向】补偿；
       补偿通常不完全（REAL 补偿量远小于偏移量）。
       → 判据：反馈 +10% → 她的 F0 必须下降，且不补偿满。
    ② DAF 延迟听觉反馈（delayed auditory feedback）
       延迟约 200 ms 时言语崩解最严重；
       ★ 且【不是越延迟越糟】—— 更长延迟(400ms)反而被当成别人的声音，效应减弱。
       → REAL 是非单调的，峰在 200ms。
    ③ 语音抑制 corollary discharge / speech suppression
       自己说话时，自己的听觉灵敏度被下调（镫骨肌反射 + 传出抑制）
       → 听自己比听别人更钝 → 自听闭环更难。
    ④ 语后聋 → 言语逐渐退化
       听觉反馈长期缺失 → 产出漂移、清晰度下降。
       → 判据：闭环关掉，长期漂移必须显著。
"""
import numpy as np
from core.speak import synth_utterance, f0_from_ear, SR
from core.speech_selflearn import SpeakerParams
from core.vocal_anatomy import daf_breakdown, speech_suppression

# 耳朵的两种状态（真走 ear_anatomy，不是开关）
EAR_OK      = dict(x_lo=0.05, asym=0.6, ohc=True)    # 基频能被编码
EAR_DAMAGED = dict(x_lo=0.18, asym=0.6, ohc=True)    # ★ 最低通道 249Hz，不含基频
                                                      #   → 只能靠二次谐波 → 听到 2 倍
EAR_DEAF    = None                                    # 听不到


def _hear(y, ear=EAR_OK, seed=0):
    """走真耳朵听 F0。返回 (听到值, 是否听到)"""
    if ear is None:
        # 语后聋：听不到自己的声音 → 只能凭感觉（无信息）
        rng = np.random.default_rng(seed * 7919 + 13)
        return None, False
    import core.speak as _sp
    sig = _sp.an_lowchan.__code__
    names = sig.co_varnames[:sig.co_argcount]
    orig = _sp.an_lowchan.__defaults__          # ★ 只存【有默认值】的尾部参数
    ofs = sig.co_argcount - len(orig)           #    所以要减掉位置参数的偏移
    vals = list(orig); vals[names.index("x_lo") - ofs] = ear["x_lo"]
    _sp.an_lowchan.__defaults__ = tuple(vals)
    try:
        v = f0_from_ear(y, SR, asym=ear["asym"], ohc=ear["ohc"])
    finally:
        _sp.an_lowchan.__defaults__ = orig
    if not len(v):
        return None, False
    return float(np.median(v)), True


def speak_once(f0_act, dur=0.5, seed=0):
    sp = SpeakerParams(f0_base=float(f0_act), jitter=0.004)
    return synth_utterance(sp, dur, seed=seed)


def closed_loop(target, lam, theta, R,
                start_off=0.30, ear=EAR_OK, daf_ms=0.0,
                self_suppress=False, shift=0.0, oracle=True,
                dur=0.5, seed=0):
    """
    让她把一个目标音高说出来，说错就听回来改，再说。

    lam    修正增益：听到差多少 → 下次调多少（0=不改，>1=超调）
    theta  满意阈值：听到的相对误差小于它就停（log 尺度）
    R      最多说几次

    daf_ms    延迟听觉反馈（REAL 峰在 200ms）
    self_suppress  说话时听觉被自己的发声抑制（听自己更钝）
    shift     人为偏移反馈音高（pitch-shift 实验；+0.10 = 反馈抬高 10%）
    oracle    关闭 → 听到的误差方向与真实无关（假反馈）
    """
    rng = np.random.default_rng(seed)
    f0 = float(target) * float(np.exp(rng.uniform(-start_off, start_off)))
    prev = f0
    heard_series, f0_series = [], []
    n = 0
    for k in range(int(max(1, R))):
        n += 1
        y = speak_once(f0, dur=dur, seed=seed * 131 + k)
        h, ok = _hear(y, ear=ear, seed=seed * 977 + k)
        if not ok or h is None or not np.isfinite(h) or h <= 0:
            # 听不到 → 凭感觉维持（不修正）
            heard_series.append(None); f0_series.append(f0)
            continue
        # ★ 人为偏移反馈（REAL pitch-shift 实验）
        h *= (1.0 + shift)
        # ★ 说话时听觉被抑制 → 听到的噪声更大
        if self_suppress:
            h *= float(np.exp(rng.normal(0.0, 0.020)))
        # ★ DAF 延迟听觉反馈
        #   两版都错，第三版才对：
        #   ① 我先用"混入上一次的 f0_act" → 但收敛时 prev≈f0，滞后几乎无害，
        #      结果【延迟越大误差越小】，方向完全反了。
        #   ② 改成 clip(d/200,0,1) → ≥200ms 全饱和，非单调性被抹平。
        #   ★ 正确的物理：DAF 破坏的是【音节级的感知-运动对齐】——
        #      说话是连续流，延迟让说话者听到的是【上一个音节】的音高，
        #      而相邻音节音高是不同的（句内起伏），所以反馈与当前该发的音【错位】。
        #      且 REAL：效应在 ~200ms 最大，更长延迟被当成"别人的声音"→ 归属权重下降。
        if daf_ms > 0:
            d = float(daf_ms)
            w = d / 200.0 if d <= 200.0 else 1.0 - 0.55 * min((d - 200.0) / 200.0, 1.0)
            w = float(np.clip(w, 0.0, 1.0))
            misaligned = float(target) * float(np.exp(rng.uniform(-0.16, 0.16)))
            h = float(np.exp((1 - w) * np.log(h) + w * np.log(misaligned)))
        prev = f0
        heard_series.append(h); f0_series.append(f0)
        err = float(np.log(target / h))          # >0 = 说低了
        if not oracle:
            # ★ oracle 关闭：听到的音高【与她真实发了什么无关】
            #   第一版我写"随机翻转符号" → 仍是随机游走，λ 的峰没消失（判据假失败）
            #   正确关法：切断【产出→感知】这条通路本身
            h = float(target) * float(np.exp(rng.normal(0.0, 0.02)))
            err = float(np.log(target / h))
        if abs(err) < theta:
            break
        f0 *= float(np.exp(lam * err))
        f0 = float(np.clip(f0, 60.0, 420.0))
    # 真值：她最后实际发出来的是多少（相对目标，log 尺度）
    final_err = abs(float(np.log(f0_series[-1] / target)))
    return dict(final_err=final_err, attempts=n,
                f0_final=f0_series[-1],
                heard=[x for x in heard_series if x is not None])


def score_loop(target, lam, theta, R, seeds=16, **kw):
    """闭环好坏：说准了没 − 说了几次的代价"""
    es, ns = [], []
    for s in range(seeds):
        r = closed_loop(target, lam, theta, R, seed=s, **kw)
        es.append(r["final_err"]); ns.append(r["attempts"])
    q = float(np.exp(-np.mean(es) / 0.06))
    return float(q - 0.055 * np.mean(ns))


def drift_no_feedback(target, n_steps=40, step=0.010, seed=0):
    """语后聋：没有听觉反馈，产出随机漂移 → 越说越偏（REAL 言语退化）"""
    rng = np.random.default_rng(seed)
    f0 = float(target)
    traj = [f0]
    for _ in range(n_steps):
        f0 *= float(np.exp(rng.normal(0.0, step)))
        traj.append(f0)
    return np.array(traj)


def drift_mean(target, n_steps=40, step=0.010, seeds=60):
    """★ 随机游走必须取【多种子的平均偏离】，单个种子会碰巧回到原点"""
    es = []
    for s in range(seeds):
        t = drift_no_feedback(target, n_steps=n_steps, step=step, seed=s)
        es.append(abs(float(np.log(t[-1] / target))))
    return float(np.mean(es))
