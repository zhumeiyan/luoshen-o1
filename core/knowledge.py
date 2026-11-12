# -*- coding: utf-8 -*-
"""
★94 知识的可靠性 —— 信谁、信多久、追多深

真值来源：从 10 篇真实 PDF（arXiv 论文 + 项目自述文档）抽取的 206 条数值声明。
不是我编的数，是她自己仓库里真有的文献。

两个真实病害：
  ① 引用失真 / 放大(citation distortion)：一条数值每转述一手，向"更极端"漂移。
     文献里这是真实现象——转述会放大原始结论。
  ② 知识过时：真值随时间漂移，旧报告反映的是当时的世界。

她要学三件事（三个旋钮）：
  rho     预算里多少花在"溯源"(消系统偏向) vs "重复"(降随机噪声)
  tau_h   旧报告的时间权重半衰期
  theta   异常报告剔除门槛

单位用她自己的度量衡(★88)：预算单位是"一次读数"，不是秒也不是钱。
"""
import json, os, math, random

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAIMS_PATH = os.path.join(HERE, "data", "knowledge", "claims_raw.json")

# ----  hyperparameters of the WORLD (not hers) ----
H_MAX   = 3.0     # 转述链最大长度(hop)，连续
KAPPA   = 0.075   # 每手放大率(相对真值) —— 引用失真
SIGMA   = 8.0     # 单份报告的随机噪声(百分点)
GAMMA   = 6.0     # 溯源溢价：越接近原始越贵
DRIFT   = 0.025   # 真值每年的相对漂移 —— 知识过时
A_MAX   = 6.0     # 报告最大年龄(年)
T_NOW   = 2032.0  # "现在"。必须晚于 claim 年份，否则过时病害会被 max(0,·) 吃掉
# 真实病害：偶尔一条转述被彻底弄错(数字/单位/量纲)。重尾，不是高斯。
P_CORRUPT  = 0.15
CORRUPT_MUL = 2.0

# 来源类型偏差：自述文档(selfdoc)有自我夸大偏向，preprint 较中性
# 这是真实存在的现象：项目自己的介绍文档会挑好看的数。
SRC_BIAS = {"preprint": 0.0, "selfdoc": 0.06}


def load_claims(path=CLAIMS_PATH, seed=0, n_claim=120):
    """加载真知识。真值 = PDF 里抽出来的那个数。"""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    rng = random.Random(seed)
    rng.shuffle(raw)
    out = []
    for c in raw[:n_claim]:
        v = float(c["truth"])
        if not (1.0 <= v <= 100.0):
            continue
        yr = c.get("year")
        out.append(dict(
            v0=v,                    # 基准真值(真PDF抽的)
            stype=c.get("stype", "preprint"),
            year=yr if yr else 2024,
            doc=c.get("doc", ""),
        ))
    return out


def true_now(c, t_now, drift=DRIFT):
    """真值随时间[下降] —— 错误率/延迟/成本这类指标逐年改善。
    所以旧报告会[高估]当前真值 —— 与引用放大同向，两者不会互相抵消。
    (这是我上一版搞错的地方：做成上升会和放大抵消，把权衡抹掉。)"""
    age = max(0.0, t_now - float(c["year"]))
    return c["v0"] * max(0.05, 1.0 - drift * age)


def make_report(c, t_now, hop, age, rng, kappa=KAPPA, sigma=SIGMA, drift=DRIFT,
                p_corrupt=P_CORRUPT, corrupt_mul=CORRUPT_MUL):
    """生成一份报告。hop=转述手数(连续)，age=多久以前(年)。"""
    v_then = true_now(c, t_now - age, drift)          # 报告时刻的真值
    amp = kappa * hop                                  # 引用放大：越二手越极端
    bias = SRC_BIAS.get(c["stype"], 0.0)               # 自述文档的自我夸大
    val = v_then * (1.0 + amp + bias) + rng.gauss(0.0, sigma)
    if rng.random() < p_corrupt:
        # 严重失真：数值被彻底转错(量纲/单位/抄错)，方向随机
        val *= (corrupt_mul if rng.random() < 0.5 else 1.0 / corrupt_mul)
    return dict(hop=hop, age=age, val=val)


def cost_of(hop, gamma=None):
    gamma = GAMMA if gamma is None else gamma
    """回溯越深(越接近原始)越贵。"""
    return 1.0 + gamma * (H_MAX - hop)


def estimate(claims, t_now, rho, tau_h, theta, b_per_claim, rng,
             kappa=KAPPA, sigma=SIGMA, drift=DRIFT, gamma=None,
             n_rep=1, return_detail=False,
             p_corrupt=P_CORRUPT, corrupt_mul=CORRUPT_MUL):
    """
    她的估计器：给定预算，对每个 claim 读数并估计当前真值。
      rho    -> 溯源强度。hop=(1-rho)*H_MAX。rho=1 追到原始(贵、份数少、无放大偏向)
                rho=0 只吃二手(便宜、份数多、有引用放大偏向)
      tau_h  -> 旧报告时间权重 0.5^(age/tau_h)
      theta  -> 与中位数差异超过 theta*尺度 的报告剔除
    """
    hop = (1.0 - rho) * H_MAX
    cost = cost_of(hop, gamma)
    n_float = b_per_claim / cost
    n_int = int(math.floor(n_float))
    p_extra = n_float - n_int

    errs = []
    for c in claims:
        vt = true_now(c, t_now, drift)
        n = n_int + (1 if rng.random() < p_extra else 0)
        if n < 1:
            n = 1
        reps = []
        for _ in range(n):
            # 报告的年龄：她能选新的，但新报告少；这里均匀采样(她无法只挑最新的)
            age = A_MAX * (rng.random() ** 0.80)   # 老的多、新的少（真实文献的时间分布）
            reps.append(make_report(c, t_now, hop, age, rng, kappa, sigma, drift, p_corrupt, corrupt_mul))
        vals = [r["val"] for r in reps]
        ws = [0.5 ** (r["age"] / max(tau_h, 1e-6)) for r in reps]

        # 异常剔除：以(加权)中位数为中心，偏离过大的报告视为失真
        if theta > 0 and len(vals) >= 2:
            sv = sorted(zip(vals, ws))
            cum, half = 0.0, sum(ws) / 2.0
            med = sv[-1][0]
            for v, w in sv:
                cum += w
                if cum >= half:
                    med = v
                    break
            scale = max(1.0, 0.15 * c["v0"])
            keep_v, keep_w = [], []
            for v, w in zip(vals, ws):
                if abs(v - med) <= theta * scale:
                    keep_v.append(v)
                    keep_w.append(w)
            if keep_v:
                vals, ws = keep_v, keep_w

        sw = sum(ws)
        est = sum(v * w for v, w in zip(vals, ws)) / sw if sw > 0 else (sum(vals) / len(vals))
        errs.append(abs(est - vt))
    mae = sum(errs) / len(errs)
    if return_detail:
        return mae, errs
    return mae
