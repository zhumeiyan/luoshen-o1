# -*- coding: utf-8 -*-
"""
aibench —— ★101 对标顶级 AI（说话·聊天·演讲科目的同一把尺子）

══════════════════════════════════════════════════════════════════
  立场先说清楚（否则这课就是骗人的）
──────────────────────────────────────────────────────────────────
  我不能把「她在我的环境里的分数」直接和「Grok-4 在别人 benchmark
  上的分数」并列 —— 任务不同，那不是对标，那是碰瓷。

  这一课做的是另一件事，而且是可做的：
      1. 把顶级 AI 已经在文献里坐实的【病理】写成可运行的环境
      2. 让一个「照顶级 AI 的行为方式行事」的对照 agent
         在我的环境里【复现】那些已发表的症状数字
      3. 再看她能不能学会躲开
  复现得出来，尺子才成立；复现不出来，这课作废。

══════════════════════════════════════════════════════════════════
  硬真值：顶级 AI 的公开实测（全部来自文献，不由我编）
──────────────────────────────────────────────────────────────────
  A. STEER-BENCH（EMNLP 2025，Chen et al.）
     13 款主流 LLM，30 组对立 subreddit，5500 道验证题
       人类专家准确率            0.81
       最佳模型                 ~0.65
       部分模型落后人类        >15 个百分点
     ↳ 测的就是「按特定社群规范调整输出」= 本课的语域适配

  B. NormAd（NAACL 2025，Rao et al.）文化适应性
       Rule-of-Thumb 设定：人类 >0.95，最佳 LLM 0.82
       Country 设定      ：多模型 <0.60（人类仍然稳）
       Neutral 设定      ：模型 0.42，人类 0.98  ← 差 56 个点
       同意偏置(sycophancy)：识别「可接受」远好于「违规」
       ↳ 「知道事实」≠「会在情境里用」，作者称之为 contextual collapse

  C. CaRL（arXiv 2607.29211）能力边界与过度自信
       vanilla 模型在超能力任务上【拒绝率 0%】
       过度自信 20%  vs  过度保守 3.4%   → 6 倍偏置
       硬任务上拒绝召回率 <30%
     ↳ 病根：RLVR 的二元奖励让「猜」是免费的 —— 只要 P(对)>0 就该猜

  D. Behavioral Calibration（ByteDance / CMU / Fudan, arXiv 2512.19920）
       「行为校准是一项【可从原始预测精度中解耦】的元技能」
       4B 模型经校准训练后 log-scale AHR 增益 0.806  >  GPT-5 的 0.207
       4B 在 SimpleQA 上的零样本校准误差 与 Grok-4 / Gemini-2.5-Pro 相当
        —— 尽管它的【事实准确率低得多】
     ↳ ★★ 这一条是本课的全部赌注：
        校准可以和「有多聪明」脱钩。她很小、没有 LLM 底座，
        但【知道自己什么时候不知道】这件事，她有可能不输。

  E. 语域继承 register inheritance（Public Policy Lab）
       「模型按【最近一段会话语境】的情绪语域生成，
         而不是【外部受众真正需要】的语域」
       「最邻近的语境饱和了生成，并一路带过去」
     另：语域分裂人格(split personality)——
       在正式语料上训的，听不懂闲聊；在推特上训的，处理不了法律文书
     ↳ 一端是「全信最近语境」= 继承错误语域
       另一端是「完全不看语境」= 语域僵化
       ★ 中间必有峰

══════════════════════════════════════════════════════════════════
"""

import numpy as np

# ───────────────────────────────────────── 顶级 AI 的公开数（对照靶）
TOPAI = {
    'steer_best':   0.65,     # A：STEER-BENCH 最佳模型
    'steer_human':  0.81,     # A：人类专家
    'normad_rot':   0.82,     # B：Rule-of-Thumb 最佳 LLM
    'normad_human': 0.95,     # B：Rule-of-Thumb 人类
    'normad_country': 0.60,   # B：Country 设定，多模型 <0.60
    'normad_neutral': 0.42,   # B：Neutral 模型 0.42（人类 0.98）
    'refusal_vanilla': 0.00,  # C：vanilla 模型拒绝率
    'overconf':      0.20,    # C：过度自信比例
    'underconf':     0.034,   # C：过度保守比例
    'over_ratio':    6.0,     # C：20/3.4 ≈ 6 倍偏置
    'ahr_gpt5':      0.207,   # D：GPT-5 log-scale AHR 增益
    'ahr_cal_4b':    0.806,   # D：校准后的 4B
}

# ───────────────────────────────────────── Grice / 语速（沿用 ★100 真值）
from core.humanskill import SCENES, rate_score, grice_quantity, face_score

# ═══════════════════════════════════════════════════════════════
#  子任务一：语域适配（register）
# ═══════════════════════════════════════════════════════════════
def register_trial(rng, trust, rho, sigma_obs, prior=0.5, tol=0.13):
    """
    真值：受众真正需要的语域 f_true ∈ [0,1]（0=极正式 … 1=极随意）
    她观测到的：被【上一段会话语境】污染过的语境

        obs = (1-ρ)·f_true + ρ·f_prev + 噪声

    ρ = 语域继承强度（真值 E）
        ρ=0  → 观测纯净，全信观测最优（峰在 trust=1）
        ρ>0  → 观测有【偏】，不是噪声，shrinkage 才有意义（峰在内部）

    trust：她信观测多少；1-trust 是她退回默认分寸（=语域僵化）
    """
    f_true = float(rng.uniform(0.1, 0.9))
    f_prev = float(rng.uniform(0.1, 0.9))          # 上一段会话的语域
    obs = (1.0 - rho) * f_true + rho * f_prev + rng.normal(0, sigma_obs)
    obs = float(np.clip(obs, 0.0, 1.0))
    chosen = float(np.clip((1.0 - trust) * prior + trust * obs, 0.0, 1.0))
    hit = 1.0 if abs(chosen - f_true) <= tol else 0.0
    return hit, abs(chosen - f_true)


# ═══════════════════════════════════════════════════════════════
#  子任务二：该不该开口（abstention / 校准）
# ═══════════════════════════════════════════════════════════════
def abstain_trial(rng, theta, acc, miscal, w):
    """
    她对每个情境有一个【自称置信度】 conf ∈ [0,1]
    真实正确概率 p_true 与 conf 的关系由 miscal 决定：
        miscal > 0  过度自信（自称的 conf 高于真实 p）
        miscal = 0  已校准

        p_true = clip(conf - miscal, 0, 1)

    ★ 理论最优（在 conf 已校准的前提下）：
        答   ：p·1 − (1−p)·w
        弃权 ：0
        答  ⟺  p > w/(1+w)
    ★★ 这个门槛【与她的原始准确率 acc 无关】——
        这就是文献 D 说的「校准可从原始精度中解耦」的解析形式。
    """
    # 她的置信度分布：中心随 acc 移动（越准越容易有高置信）
    conf = float(np.clip(rng.beta(1.6 + 2.4 * acc, 2.2 - 1.2 * acc), 0.001, 0.999))
    p_true = float(np.clip(conf - miscal, 0.0, 1.0))
    if conf < theta:
        return 0.0, 0.0, 0.0, 1.0        # abstain：不对、不幻觉、占一次弃权
    ok = 1.0 if rng.random() < p_true else 0.0
    return ok, 1.0 - ok, 1.0, 0.0        # answered, hallucinated, answered, abstained


def opt_theta(w):
    """解析最优门槛（conf 已校准时）：与 acc 无关，只与错的代价有关"""
    return float(w / (1.0 + w))


# ═══════════════════════════════════════════════════════════════
#  合起来：一次完整评估
# ═══════════════════════════════════════════════════════════════
def evaluate(p, worlds, nseed=8):
    """
    p      = [trust, theta]
    worlds = [(rho, sigma_obs, acc, miscal, w), ...]
    每个世界用自己的 w 计分，再取平均 —— 不能拿最后一个 w 去算所有世界。
    """
    trust, theta = float(np.clip(p[0], 0, 1)), float(np.clip(p[1], 0, 1))
    accs, halls, ahrs, hits, devs, absr, SC = [], [], [], [], [], [], []
    for (rho, sig, acc, miscal, w) in worlds:
        sc_w = []
        for s in range(nseed):
            rng = np.random.default_rng(
                9100 + s * 977 + int(round(1000 * rho + 100 * sig + 10 * acc)))
            hh = []
            for _ in range(24):
                h, d = register_trial(rng, trust, rho, sig)
                hits.append(h); devs.append(d); hh.append(h)
            n_ok = n_hall = n_ans = n_abs = 0
            for _ in range(24):
                ok, hal, ans, ab = abstain_trial(rng, theta, acc, miscal, w)
                n_ok += ok; n_hall += hal; n_ans += ans; n_abs += ab
            if n_ans > 0:
                a = n_ok / n_ans; h2 = n_hall / n_ans
                accs.append(a); halls.append(h2)
                ahrs.append(float(np.log((a + 1e-3) / (h2 + 1e-3))))
            absr.append(n_abs / 24.0)
            sc_w.append(0.5 * float(np.mean(hh)) + n_ok / 24.0 - w * n_hall / 24.0)
        SC.append(float(np.mean(sc_w)))
    return {
        'reg_acc':  float(np.mean(hits)),
        'reg_dev':  float(np.mean(devs)),
        'acc':      float(np.mean(accs)) if accs else 0.0,
        'hall':     float(np.mean(halls)) if halls else 0.0,
        'ahr':      float(np.mean(ahrs)) if ahrs else 0.0,
        'abstain':  float(np.mean(absr)),
        'score':    float(np.mean(SC)),
    }


def run_episode(p, world, rng, n_items=48, feedback=True):
    """
    一个连续回合：她边答边收反馈，自己估自己的偏差。

    world = (rho, sigma_obs, acc, miscal, w)
      w      「错的代价」——【可观测】：场合的利害关系是人告诉她的
              （给人科普 vs 给人下诊断，利害关系写在场合里）
      miscal 她自己的过度自信程度——【不可观测】，只能从反馈里估

    p = [trust, theta0, beta]
      theta = clip(theta0 + beta * b_hat, 0, 1)
      b_hat = 近期 mean(conf) − mean(实际正确)
      ★ 解析最优：theta* = w/(1+w) + miscal
         （因为 p_true = conf − miscal，要 conf > w/(1+w) + miscal）
        → theta0* = w/(1+w)，beta* = 1.0
        → theta0* 只跟场合利害有关，跟她有多聪明无关（文献 D 的解析形式）
    """
    rho, sig, acc, miscal, w = world
    trust, theta0, beta = float(np.clip(p[0], 0, 1)), p[1], p[2]

    confs, rights = [], []
    n_ok = n_hall = n_ans = n_abs = 0
    hits, devs = [], []
    for i in range(n_items):
        # ── 语域
        h, d = register_trial(rng, trust, rho, sig)
        hits.append(h); devs.append(d)
        # ── 该不该开口
        if len(confs) >= 4 and feedback:
            b_hat = float(np.mean(confs[-8:]) - np.mean(rights[-8:]))
        else:
            b_hat = 0.0
        theta = float(np.clip(theta0 + beta * b_hat, 0.0, 1.0))
        conf = float(np.clip(rng.beta(1.6 + 2.4 * acc, 2.2 - 1.2 * acc), 0.001, 0.999))
        p_true = float(np.clip(conf - miscal, 0.0, 1.0))
        if conf < theta:
            n_abs += 1
            continue
        ok = 1.0 if rng.random() < p_true else 0.0
        n_ans += 1; n_ok += ok; n_hall += (1 - ok)
        confs.append(conf); rights.append(ok)

    # ★ 评分必须按【全部条目】算，不能只按已答的算。
    #   只按已答算 → 「全弃权」的 acc 恒为 1、hall 恒为 0 → 弃权免费
    #   → 门槛会一路涨到 1.0（实测正是 0.95）。这是 ★72/★78 同族：
    #   我写了个「其中一个选项是免费」的目标函数，然后怪她学出边界解。
    # 弃权的效用是 0（不是免费，是「什么都没得到」）
    n = float(n_items)
    a_all = n_ok / n
    h_all = n_hall / n
    a_c = n_ok / n_ans if n_ans else 0.0
    h_c = n_hall / n_ans if n_ans else 0.0
    return {
        'reg_acc': float(np.mean(hits)), 'reg_dev': float(np.mean(devs)),
        'acc': a_c, 'hall': h_c,
        'acc_all': a_all, 'hall_all': h_all,
        'ahr': float(np.log((a_c + 1e-3) / (h_c + 1e-3))),
        'abstain': n_abs / n,
        'score': float(0.5 * np.mean(hits) + a_all - w * h_all),
    }


def evaluate_ep(p, worlds, nseed=8, n_items=48, feedback=True):
    ks = ['reg_acc', 'reg_dev', 'acc', 'hall', 'ahr', 'abstain', 'score']
    acc_v = {k: [] for k in ks}
    for w_i, world in enumerate(worlds):
        for s in range(nseed):
            rng = np.random.default_rng(9100 + s * 977 + w_i * 131)
            r = run_episode(p, world, rng, n_items=n_items, feedback=feedback)
            for k in ks:
                acc_v[k].append(r[k])
    return {k: float(np.mean(v)) for k, v in acc_v.items()}


def topai_like(rng, worlds, nseed=8):
    """
    对照 agent：按【顶级 AI 的已发表行为方式】行事
        · 语域：全信最近语境      trust = 1.0   （真值 E 语域继承）
        · 弃权：从不拒绝          theta = 0.0   （真值 C 拒绝率 0%）
        · 置信度：过度自信        miscal = +0.20（真值 C 20%）
    """
    return evaluate([1.0, 0.0], worlds, nseed=nseed)


def human_like(worlds, nseed=8):
    """
    人类对照：语域 0.75（标定过，对应 STEER-BENCH 人类 0.81）
              门槛用【已校准】的 w/(1+w)，且人的 miscal = 0
    """
    accs, halls, ahrs, hits, absr, SC = [], [], [], [], [], []
    for (rho, sig, acc, miscal, w) in worlds:
        sc_w = []
        for s in range(nseed):
            rng = np.random.default_rng(
                9100 + s * 977 + int(round(1000 * rho + 100 * sig + 10 * acc)))
            hh = []
            for _ in range(24):
                h, _ = register_trial(rng, 0.75, rho, sig)
                hits.append(h); hh.append(h)
            n_ok = n_hall = n_ans = n_abs = 0
            for _ in range(24):
                ok, hal, ans, ab = abstain_trial(rng, opt_theta(w), acc, 0.0, w)
                n_ok += ok; n_hall += hal; n_ans += ans; n_abs += ab
            if n_ans > 0:
                a = n_ok / n_ans; h2 = n_hall / n_ans
                accs.append(a); halls.append(h2)
                ahrs.append(float(np.log((a + 1e-3) / (h2 + 1e-3))))
            absr.append(n_abs / 24.0)
            sc_w.append(0.5 * float(np.mean(hh)) + n_ok / 24.0 - w * n_hall / 24.0)
        SC.append(float(np.mean(sc_w)))
    return {
        'reg_acc': float(np.mean(hits)), 'acc': float(np.mean(accs)),
        'hall':    float(np.mean(halls)), 'ahr': float(np.mean(ahrs)),
        'abstain': float(np.mean(absr)), 'score': float(np.mean(SC)),
    }
