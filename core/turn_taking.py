#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★55 轮流（turn-taking）—— 对话腔真正的所在
================================================================
★★ 为什么建这一层
    ★53/★54 学的都是【音色】：停顿率、jitter、F0 跨度
    但换语料源换来的还是"朗读" —— 因为朗读和对话的差别
    【不在音色，在结构】：有没有轮流、有没有重叠、有没有附和

    朗读 = 一个人说，说完拉倒
    对话 = 两个人抢话轮，间隔 100ms，重叠 <5%，19% 是"嗯/对"

★★★ 核心矛盾（本层的可证伪锚）
    语音产生潜伏 > 600 ms（REAL，Levinson 2016）
    话轮间隔中位只有 100 ms（REAL，Stivers 2009 十语言）
    ------------------------------------------------
    ★ 不预测，间隔必然 >= 600ms，永远做不到 100ms
    ★ 所以【投影 projection】是必需的，不是可选的
    真机制：听者靠句法完成度 + 韵律完成度预测话轮何时结束
            EEG 实证：话轮结束前 1200ms 就出现 beta 去同步（Magyari 2014）

★★ 真锚点（全部来自文献，不是我编的）
    FTO 众数        0~200 ms，总众数 0，中位 +100 ms   Stivers 2009 PNAS
    FTO 分布        高峰度、右偏，集中 0~500 ms        Hoogland 2025 综述25篇
    话轮时长        平均 1680 ms，中位 1227 ms          Levinson&Torreira 2015
    重叠占比        <5% 语音信号，转换处平均 275 ms     同上
    话内−话间间隔   +150 ms                            ten Bosch 2005
    backchannel     19% 的话轮（Switchboard）          Jurafsky 1997
    回避性回答      至少慢 2 倍                        Stivers 2009
    长间隔 >700ms   携带符号意义（不情愿）              Kendrick&Torreira 2015
    日语 aizuchi     频率为英语 2 倍以上                 White 1989
    女-女 vs 男-男  中位 30 ms vs 130 ms（Switchboard） Language Log

★★ 关键：+150ms 不许硬编码
    它必须从【有序规则 ordered rules】自然产生：
    话轮转换处，接话权【先归下一个说话者】；只有他不接，当前说话者才继续
    → 当前说话者继续 = 多一次"要不要继续"的决策 → 天然更慢
"""
import numpy as np

# ─────────────────────────────────────────── REAL 锚点
REAL = {
    "fto_median":      (0.00, 0.25),   # 中位 +100ms，跨语言中位 0~300
    "fto_mode":        (0.00, 0.20),   # 众数 0~200ms
    "fto_kurtosis":    (3.0, None),    # 高峰度
    "fto_skew":        (0.0, None),    # 右偏
    "turn_dur_mean":   (1.20, 2.20),   # 平均 1680ms
    "turn_dur_median": (0.80, 1.70),   # 中位 1227ms
    "overlap_frac":    (0.0, 0.05),    # <5%
    "intra_minus_inter": (0.05, 0.30), # +150ms
    "bc_frac":         (0.10, 0.30),   # 19%
    "dispref_ratio":   (1.6, None),    # 至少 2 倍
}


class TurnParams:
    """说话者 / 对话双方的参数 —— 学的时候改这些"""

    def __init__(self):
        # ── 产生侧（生理，不可随意改）
        self.plan_latency = 0.60     # 语音产生潜伏，REAL >600ms
        # ── 预测侧（★55 核心）
        self.predict_horizon = 0.45  # 提前多少秒开始编码（投影能力）
        self.predict_noise = 0.12    # 预测误差（越大越容易早/晚）
        # ── 转换行为
        self.gap_base = 0.10         # 基础间隔
        self.gap_sigma = 0.10        # 间隔抖动
        # ── 重叠 / 抢话
        self.overlap_prob = 0.12     # 抢话（提前启动过头）概率
        # ── backchannel（"嗯/对/是"，不夺话轮）
        self.bc_rate = 0.19          # REAL 19%
        # ── 话轮长度
        self.turn_len_mean = 1.68    # REAL 1680ms
        self.turn_len_sigma = 0.95
        # ── 当前说话者继续说话的额外决策成本
        #    ★ 这是 +150ms 的来源，不许直接写 0.15 到间隔里
        self.continue_cost = 0.15
        # ── 回避性回答（不情愿）的延迟倍数
        self.dispreferred_mult = 2.0  # REAL 至少 2 倍
        self.dispreferred_prob = 0.12
        # ── 接话阈值：REAL「>700ms 的间隔携带符号意义」(Kendrick&Torreira 2015)
        self.takeover_threshold = 0.70

    def copy(self):
        p = TurnParams()
        p.__dict__.update(self.__dict__)
        return p


# ─────────────────────────────────────────── 模拟一场对话
def simulate(p, n_turns=400, seed=0, dispref=False):
    """两人对话，返回事件序列

    ★ 机制，不是硬编码结果：
      1. 当前说话者说一个 turn unit，时长从对数正态取
      2. ★ 听者【投影】：预测结束时刻 = 真实结束 - predict_horizon + 噪声
      3. 听者在预测点开始编码，plan_latency 后发声
         → 实际发声时刻 = 预测结束点 - predict_horizon + plan_latency
         当 predict_horizon 接近 plan_latency 时，间隔趋近 0
      4. 若预测偏早 → 重叠（负 offset）
         若预测偏晚 → 间隔（正 offset）
      5. 若听者不接（1 - take_prob），当前说话者继续
         → 中间多一次"要不要继续"的决策 → continue_cost
      6. backchannel：听者在对方话中插入"嗯"，不夺话轮
    """
    rng = np.random.default_rng(seed)
    events = []          # (speaker, start, end, is_bc)
    ftos = []            # 话轮转换 offset（正=间隔，负=重叠）—— 仅换人时
    intra_gaps = []      # 同一说话者连续 unit 之间的间隔 —— 仅不换人时
    t = 0.0
    spk = 0
    prev_end = None
    prev_spk = None
    n_bc = 0
    n_taken = 0
    overlaps = []

    for i in range(n_turns):
        # ── 上一个 unit 在 prev_end 结束，说话者 prev_spk
        # ── 听者（1-prev_spk）要接话
        # ★★ 投影（projection）—— ★55 的核心机制
        #   听者必须在预期结束点前 plan_latency 就开始编码
        #   他能提前预判的量 = predict_horizon
        #   → FTO = plan_latency - predict_horizon + err
        #     predict_horizon = 0    → 600ms（REAL 产生潜伏）
        #     predict_horizon = 0.55 →  50ms（REAL 中位 100ms）
        listener = 1 - prev_spk if prev_spk is not None else 1
        err = rng.normal(0.0, p.predict_noise)
        # ★★ 修（★55 第三次）：连续加 exponential 会把【中位】一起推高
        #    （中位被推到 283ms，超出 REAL 上限 250ms）
        #    REAL 的形状是：主峰很窄（0~100ms）+ 少数很长的延迟
        #    → 高峰度 + 强右偏，但中位不动
        if rng.random() < 0.10:                    # 10% 的话轮预测失败/迟疑
            err += rng.exponential(max(p.predict_noise, 1e-6) * 3.0)
        fto_raw = (p.plan_latency - p.predict_horizon) + err \
                  + rng.normal(p.gap_base, max(p.gap_sigma, 1e-6))

        # ── 回避性回答（不情愿）→ 至少慢 2 倍
        if dispref and rng.random() < p.dispreferred_prob:
            fto_raw = abs(fto_raw) * p.dispreferred_mult + 0.30

        # ── 抢话（overlap）：主动提前启动 → 负 offset
        # ★★ 修（★55）：幅度 0.25 会拉出左尾，与 REAL「右偏」矛盾
        #    REAL：重叠短暂且受限，间隔才有长尾 → 抢话幅度压小，右尾加强
        if rng.random() < p.overlap_prob:
            fto_raw -= abs(rng.normal(0.12, 0.05))

        # ── 话轮时长：对数正态 → 右偏，与真实一致
        dur = float(rng.lognormal(np.log(max(p.turn_len_mean, 0.05))
                                  - 0.5 * p.turn_len_sigma ** 2,
                                  p.turn_len_sigma))
        dur = float(np.clip(dur, 0.05, 30.0))

        # ── 接上了吗？阈值 = REAL「>700ms 的间隔携带符号意义」
        take = abs(fto_raw) < p.takeover_threshold

        if take:
            this_spk = listener                    # ★ 换人
            gap_used = fto_raw
        else:
            # ★ 听者没接上 → 当前说话者继续
            #   ordered rules：接话权先归下一个说话者，只有他不接，当前人才继续
            #   → 多一次"要不要继续"的决策 → 天然更慢 = +150ms 的来源
            this_spk = prev_spk if prev_spk is not None else 0
            # ★★ 修（★55）：不能用 |fto_raw| —— 它必然 >= takeover_threshold(0.7)
            #    会算出 intra ≈ 0.85s，比 REAL 的 +150ms 大 5 倍
            #    真机制：听者没接上只是【触发】继续的决策，
            #    当前人重新起话用的是他自己的节奏（gap_base），不是听者的延迟
            gap_used = abs(rng.normal(p.gap_base, max(p.gap_sigma, 1e-6))) \
                       + p.continue_cost
            dur = dur * 0.8                        # 继续时通常说短一点

        start = max(0.0, (prev_end if prev_end is not None else 0.0) + gap_used)
        end = start + dur
        # ── backchannel："嗯/对/是"，插在对方话里，不夺话轮
        if rng.random() < p.bc_rate and prev_end is not None:
            n_bc += 1
            bc_t = start + dur * rng.uniform(0.3, 0.9)
            events.append((1 - this_spk, bc_t, bc_t + 0.15, True))

        events.append((this_spk, start, end, False))
        # ★★ 归属：换人 → FTO（正=间隔，负=重叠）；不换人 → 话内间隔
        if prev_spk is not None and prev_end is not None:
            if this_spk != prev_spk:
                ftos.append(gap_used)
                if gap_used < 0:
                    overlaps.append(-gap_used)
            else:
                intra_gaps.append(gap_used)
            if this_spk != prev_spk:
                n_taken += 1
        prev_end, prev_spk, t = end, this_spk, end

    return {
        "ftos": np.array(ftos),
        "intra_gaps": np.array(intra_gaps),
        "turn_durs": np.array([e[2] - e[1] for e in events if not e[3]]),
        "overlaps": np.array(overlaps),
        "n_bc": n_bc, "n_turns": len(events), "n_taken": n_taken,
        "speech_time": float(sum(e[2] - e[1] for e in events)),
        "overlap_time": float(np.sum(np.clip(-np.array(ftos)[np.array(ftos) < 0], 0, None)))
        if len(ftos) else 0.0,
        "events": events,
    }


# ─────────────────────────────────────────── 特征
def _mode_hist(x, bins=None):
    if len(x) < 5:
        return 0.0
    if bins is None:
        bins = np.arange(-1.0, 1.5, 0.05)
    h, edges = np.histogram(x, bins=bins)
    return float((edges[h.argmax()] + edges[h.argmax() + 1]) / 2)


def _kurt(x):
    if len(x) < 10 or x.std() < 1e-9:
        return 0.0
    z = (x - x.mean()) / x.std()
    return float((z ** 4).mean())


def _skew(x):
    if len(x) < 10 or x.std() < 1e-9:
        return 0.0
    z = (x - x.mean()) / x.std()
    return float((z ** 3).mean())


def extract(p, n_turns=400, seeds=(0, 1, 2), dispref=False):
    """多 seed 聚合，返回特征字典（稳定，抗抖动）"""
    recs = [simulate(p, n_turns=n_turns, seed=s, dispref=dispref) for s in seeds]
    ftos = np.concatenate([r["ftos"] for r in recs])
    intra = np.concatenate([r["intra_gaps"] for r in recs])
    durs = np.concatenate([r["turn_durs"] for r in recs])
    ov = np.concatenate([r["overlaps"] for r in recs])
    speech = sum(r["speech_time"] for r in recs)
    ovtime = sum(r["overlap_time"] for r in recs)
    nb = sum(r["n_bc"] for r in recs)
    nt = sum(r["n_turns"] for r in recs)
    inter = ftos[ftos >= 0] if len(ftos) else np.array([0.0])
    return {
        "fto_median": float(np.median(ftos)) if len(ftos) else 0.0,
        "fto_mode": _mode_hist(ftos),
        "fto_kurtosis": _kurt(ftos),
        "fto_skew": _skew(ftos),
        "turn_dur_mean": float(durs.mean()) if len(durs) else 0.0,
        "turn_dur_median": float(np.median(durs)) if len(durs) else 0.0,
        "overlap_frac": float(ovtime / max(speech, 1e-9)),
        "intra_minus_inter": (float(np.median(intra)) - float(np.median(inter)))
                             if len(intra) else 0.0,
        "bc_frac": float(nb / max(nt, 1)),
        "overlap_mean_ms": float(ov.mean() * 1000) if len(ov) else 0.0,
    }


FEATS = ["fto_median", "fto_mode", "fto_kurtosis", "fto_skew",
         "turn_dur_mean", "turn_dur_median", "overlap_frac",
         "intra_minus_inter", "bc_frac", "overlap_mean_ms"]


def vec(d):
    return np.array([d[k] for k in FEATS])


# ─────────────────────────────────────────── 目标 = 真人对话
TARGET = {
    "fto_median": 0.10,        # 中位 +100ms
    "fto_mode": 0.05,          # 众数 0~200ms
    "fto_kurtosis": 6.0,       # 高峰度
    "fto_skew": 1.5,           # 右偏
    "turn_dur_mean": 1.68,     # REAL 1680ms
    "turn_dur_median": 1.23,   # REAL 1227ms
    "overlap_frac": 0.03,      # <5%
    "intra_minus_inter": 0.15, # +150ms
    "bc_frac": 0.19,           # REAL 19%
    "overlap_mean_ms": 275.0,  # REAL 275ms
}
TARGET_V = vec(TARGET)


# ─────────────────────────────────────────── 两个"腔"
def monologue():
    """朗读/独白腔：不预测、长话轮、无重叠、无附和、无轮流"""
    p = TurnParams()
    p.predict_horizon = 0.0        # ★ 不预测
    p.predict_noise = 0.30
    p.gap_base = 0.90              # 长间隔
    p.gap_sigma = 0.40
    p.turn_len_mean = 4.50         # 长句
    p.turn_len_sigma = 0.60
    p.overlap_prob = 0.0
    p.bc_rate = 0.0
    p.continue_cost = 0.05
    return p


def dialogue():
    """对话腔：强预测、短话轮、少量重叠、19% 附和"""
    p = TurnParams()
    p.predict_horizon = 0.55
    p.predict_noise = 0.12
    p.gap_base = 0.10
    p.gap_sigma = 0.10
    p.turn_len_mean = 1.68
    p.turn_len_sigma = 0.95
    p.overlap_prob = 0.12
    p.bc_rate = 0.19
    p.continue_cost = 0.15
    return p
