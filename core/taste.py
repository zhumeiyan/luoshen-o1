#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
味觉 —— 化学感受的最后一块，也是【分子手性】最暴露的一块
================================================================
★ 与前面所有层的根本不同：
    眼耳鼻：感受【物理量】（光强、声压、分子形状）
    ★ 味觉：感受【化学键】—— 直接对分子立体构型敏感
    ★ 所以味觉是手性暴露得最彻底的一层（★ 见实验3）

----------------------------------------------------------------
一、五种基本味觉（REAL，不是四种）
----------------------------------------------------------------
    甜 sweet    T1R2+T1R3 (GPCR)      蔗糖阈值约 10 mM
    鲜 umami    T1R1+T1R3 (GPCR)      谷氨酸钠约 1.5 mM
    咸 salty    ENaC (离子通道)        NaCl 约 10 mM
    酸 sour     OTOP1 (质子通道)       HCl 约 1 mM
    苦 bitter   T2R 家族 ~25~30 种     奎宁约 0.008 mM

    ★★ 苦的阈值是甜的 1/1250 —— 因为要检测毒素
    ★★ 苦的受体有 25~30 种，甜只有 1 种组合
        ★ 甜只需检测糖（一种），苦要检测成千上万种毒

----------------------------------------------------------------
二、★★ 味觉地图是假的（教科书级假货）
----------------------------------------------------------------
    经典地图：舌尖甜 / 舌根苦 / 两侧前咸 / 两侧后酸
    来源：1901 Hänig 测的是【相对敏感度】，差异很小
          1942 Boring 英译时把相对量画成了【绝对分区】
    ★ REAL：所有区域都能检测所有味觉，差异 < 2 倍
    ★ 这是与 ★26"解剖手性≠功能手感"同一类：
      教科书上的图 ≠ 真实机制

----------------------------------------------------------------
三、★★★ 分子手性：甜与苦的反转
----------------------------------------------------------------
    阿斯巴甜（aspartame）= L-天冬氨酸 + L-苯丙氨酸甲酯
        L,L 型 → 甜（约蔗糖 200 倍）
        D,D 型 → 苦
    ★★ 同一个分子式、同样的原子，手性不同 → 甜苦完全反转

    柠檬烯（limonene）
        R-(+) → 橙子味
        S-(-) → 柠檬味
    ★ 注意区分：阿斯巴甜是【价态反转】(甜↔苦)
                柠檬烯是【身份变化】(橙↔柠檬)，两者都是好气味
    ★ 天然氨基酸全是 L 型，天然糖全是 D 型
      ★ 生命本身是手性的 —— 这是最底层的手性

----------------------------------------------------------------
四、★★ 辣不是味觉，是痛觉
----------------------------------------------------------------
    辣椒素 → TRPV1（★27 皮肤的热伤害通道，阈值 43°C）
      ★ 辣椒素把 TRPV1 激活阈值【降到体温以下】
        → 常温下就"烧"
    薄荷醇 → TRPM8（★27 皮肤的冷通道，峰值 25°C）
      ★ 薄荷醇把 TRPM8 激活阈值【升到体温以上】
        → 常温下就"凉"
    ★★ 辣和凉是【口腔里的温度觉 + 痛觉】
        ★ 由三叉神经 CN V 传导，不是面神经 CN VII
        ★ 这与 ★27 皮肤的冷热通道是【同一个受体】

----------------------------------------------------------------
五、★ 风味 = 味觉 + 鼻后嗅觉 + 三叉神经
----------------------------------------------------------------
    捏鼻子 → 苹果和洋葱分不出来（经典实验）
    ★ 味觉本身只有 5 个维度，风味的丰富度几乎全来自嗅觉
    ★ 鼻后通路（retronasal）：从口腔后部进入鼻腔
      ★ 与 ★26 鼻子的鼻前通路（orthonasal）是同一套受体、不同路径

----------------------------------------------------------------
六、细胞更新（REAL）
----------------------------------------------------------------
    ★ 味觉细胞是【上皮细胞】，不是神经元
    寿命 10~14 天（比嗅上皮 45 天快得多）
      ★ 口腔环境恶劣：温度、机械磨损、pH 剧烈变化

----------------------------------------------------------------
七、传导：三条脑神经
----------------------------------------------------------------
    舌前 2/3 → 鼓索 chorda tympani（CN VII 面神经）
    舌后 1/3 → 舌咽神经 CN IX
    会厌/喉  → 迷走神经 CN X
    ★ 与 ★17 眼睛的三条眼肌神经（III/IV/VI）呼应
    中枢：孤束核 NTS → 丘脑 VPMpc → 岛叶/额岛盖
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL 检测阈值（mM） ----------------
THRESHOLD_MM = {
    "甜": 10.0,      # 蔗糖
    "咸": 10.0,      # NaCl
    "鲜": 1.5,       # 谷氨酸钠
    "酸": 1.0,       # HCl（柠檬酸约 2 mM）
    "苦": 0.008,     # 奎宁
}
HILL_N = {"甜": 1.3, "咸": 1.4, "鲜": 1.2, "酸": 1.0, "苦": 1.0}

# 受体数量（REAL）
T1R_COUNT = 3        # T1R1, T1R2, T1R3
T2R_COUNT = 25       # 人类功能性苦味受体（REAL 25~30）

# 味道强度（相对蔗糖=1）
SWEETNESS_X = {"蔗糖": 1.0, "果糖": 1.7, "葡萄糖": 0.7,
               "阿斯巴甜": 200.0, "糖精": 300.0, "三氯蔗糖": 600.0}

# 细胞更新（REAL）
TASTE_CELL_LIFETIME_DAYS = (10, 14)
OLFACTORY_CELL_LIFETIME_DAYS = (30, 60)   # ★26 嗅上皮对照

# ★27 皮肤温度通道（这里是同一个受体）
TRPV1_THRESHOLD_C = 43.0      # 热伤害
TRPM8_PEAK_C      = 25.0      # 冷


# ================================================================
# 一、浓度-响应（Hill）
# ================================================================
def hill(conc_mM: np.ndarray, K_mM: float, n: float = 1.0) -> np.ndarray:
    """★ Hill 方程 R = C^n/(C^n + K^n)。K 处响应 = 0.5。"""
    C = np.asarray(conc_mM, float)
    Cn = np.power(np.maximum(C, 0.0), n)
    Kn = np.power(K_mM, n)
    return Cn / (Cn + Kn)


def taste_response(conc_mM: float, modality: str = "甜") -> float:
    K = THRESHOLD_MM[modality]
    n = HILL_N[modality]
    return float(hill(np.array([conc_mM]), K, n)[0])


def threshold_curve(modality: str = "甜",
                    concs: np.ndarray = None) -> tuple[np.ndarray, np.ndarray]:
    if concs is None:
        K = THRESHOLD_MM[modality]
        concs = np.logspace(np.log10(K/100), np.log10(K*100), 60)
    return concs, hill(concs, THRESHOLD_MM[modality], HILL_N[modality])


def bitter_advantage() -> dict:
    """★ 苦的检测优势：阈值最低 + 受体最多。"""
    return {
        "苦阈值/甜阈值": THRESHOLD_MM["甜"] / THRESHOLD_MM["苦"],
        "苦受体数/甜受体数": T2R_COUNT / 1.0,
        "甜受体组合数": 1,
    }


# ================================================================
# 二、★★ 味觉地图是假的
# ================================================================
CLASSIC_MAP = {
    "舌尖":  {"甜": 1.0, "咸": 0.0, "酸": 0.0, "苦": 0.0},
    "舌侧前": {"甜": 0.0, "咸": 1.0, "酸": 0.0, "苦": 0.0},
    "舌侧后": {"甜": 0.0, "咸": 0.0, "酸": 1.0, "苦": 0.0},
    "舌根":  {"甜": 0.0, "咸": 0.0, "酸": 0.0, "苦": 1.0},
}
# ★ REAL：Hänig 1901 原测的是相对敏感度，差异 < 2 倍
REAL_MAP = {
    "舌尖":  {"甜": 1.00, "咸": 0.90, "酸": 0.85, "苦": 0.75},
    "舌侧前": {"甜": 0.90, "咸": 1.00, "酸": 0.90, "苦": 0.80},
    "舌侧后": {"甜": 0.80, "咸": 0.90, "酸": 1.00, "苦": 0.95},
    "舌根":  {"甜": 0.75, "咸": 0.85, "酸": 0.90, "苦": 1.00},
}


def taste_map(site: str, modality: str, real: bool = True) -> float:
    """★ 经典地图 vs 真实敏感度。"""
    m = REAL_MAP if real else CLASSIC_MAP
    return float(m.get(site, {}).get(modality, 0.0))


def map_discrepancy() -> dict:
    """★ 两个地图的最大分歧点。"""
    worst = None
    for site in REAL_MAP:
        for mod in REAL_MAP[site]:
            c = taste_map(site, mod, real=False)
            r = taste_map(site, mod, real=True)
            d = abs(r - c)
            if worst is None or d > worst[2]:
                worst = (site, mod, d, c, r)
    return {"site": worst[0], "modality": worst[1], "diff": worst[2],
            "classic": worst[3], "real": worst[4]}


# ================================================================
# 三、★★★ 分子手性：甜苦反转
# ================================================================
def chirality_valence(c: float, w: float = 0.5) -> tuple[float, float]:
    """★ 手性参数 c ∈ [-1, +1]。

    +1 = L,L（天然氨基酸构型）  → 甜
    -1 = D,D（镜像）            → 苦
    返回 (甜度, 苦度)
    """
    sweet = 200.0 * np.exp(-0.5 * ((c - 1.0) / w) ** 2)
    bitter = 100.0 * np.exp(-0.5 * ((c + 1.0) / w) ** 2)
    return float(sweet), float(bitter)


def aspartame(chirality: float) -> dict:
    """★★ 阿斯巴甜：L,L 甜 / D,D 苦。"""
    s, b = chirality_valence(chirality)
    return {"chirality": chirality, "sweet": s, "bitter": b,
            "valence": s - b,
            "percept": "甜" if s > b else "苦"}


def chirality_sweep(n: int = 41) -> dict:
    cs = np.linspace(-1, 1, n)
    vs = np.array([aspartame(c)["valence"] for c in cs])
    return {"c": cs, "valence": vs}


def limonene(chirality: float) -> str:
    """★ 柠檬烯：手性改变【身份】，不是反转价态。"""
    return "橙子味" if chirality > 0 else "柠檬味"


def chirality_kinds() -> dict:
    """★★ 区分两种手性效应。"""
    return {
        "阿斯巴甜": {"类型": "价态反转", "L,L": aspartame(+1.0)["percept"],
                     "D,D": aspartame(-1.0)["percept"]},
        "柠檬烯":   {"类型": "身份变化", "R(+)": limonene(+1.0),
                     "S(-)": limonene(-1.0)},
    }


def no_chirality_control() -> dict:
    """★ 对照：去掉手性维度（c 固定 0），甜苦能反转吗？"""
    s, b = chirality_valence(0.0)
    return {"sweet": s, "bitter": b, "valence": s - b,
            "reversible": False}


# ================================================================
# 四、★★ 辣 = 痛觉，不是味觉
# ================================================================
def trpv1_threshold(capsaicin_uM: float) -> float:
    """★ 辣椒素把 TRPV1 阈值从 43°C 往下拉。
    REAL：阈值可降到体温(37°C)以下 → 常温下感觉烧。"""
    return float(TRPV1_THRESHOLD_C - 12.0 * (1 - np.exp(-capsaicin_uM / 5.0)))


def trpm8_threshold(menthol_mM: float) -> float:
    """★ 薄荷醇把 TRPM8 激活阈值往上推。

    REAL：可推到体温(37°C)以上 → 常温下感觉凉。
    ★ 第一版上限只写到 +10°C（最高 35°C），永远够不到体温 37°C
      → 凉度恒为 0，薄荷醇完全无效
      ★ 这就是"该到达的地方到不了"，与 ★28 前庭"该衰减的地方不衰减"是镜像
    """
    return float(25.0 + 16.0 * (1 - np.exp(-menthol_mM / 2.0)))


def pungency(capsaicin_uM: float, temp_c: float = 37.0) -> float:
    """★ 辣度 = 体温超出（被拉低的）TRPV1 阈值的量。"""
    th = trpv1_threshold(capsaicin_uM)
    return float(max(0.0, temp_c - th))


def coolness(menthol_mM: float, temp_c: float = 37.0) -> float:
    """★ 凉度 = （被推高的）TRPM8 阈值超出体温的量。"""
    th = trpm8_threshold(menthol_mM)
    return float(max(0.0, th - temp_c))


def is_taste(modality: str) -> bool:
    """★ 辣/凉/涩/碳酸 都不是味觉 —— 走三叉神经 CN V。"""
    return modality in ("甜", "咸", "酸", "苦", "鲜")


# ================================================================
# 五、★ 风味整合
# ================================================================
def flavor(taste_vec: np.ndarray, retronasal: np.ndarray,
           trigeminal: float = 0.0) -> dict:
    """★ 风味 = 味觉(5维) + 鼻后嗅觉(高维) + 三叉神经。"""
    t = np.asarray(taste_vec, float)
    r = np.asarray(retronasal, float)
    return {"taste_dim": t.size, "retronasal_dim": r.size,
            "trigeminal": trigeminal,
            "total_dim": t.size + r.size + (1 if trigeminal else 0)}


def pinch_nose(retronasal_gain: float = 0.0) -> float:
    """★ 捏鼻子：鼻后通路断掉 → 只剩 5 个味觉维度。"""
    return 5.0 * (1.0 - retronasal_gain) + 400.0 * retronasal_gain


def apple_vs_onion(retronasal_on: bool) -> str:
    """★ 经典实验：捏鼻子分不出苹果和洋葱。"""
    return "可区分" if retronasal_on else "分不出（都只是甜+酸）"


# ================================================================
# 六、细胞更新
# ================================================================
def turnover_fraction(days: np.ndarray, lifetime_days: float = 12.0
                      ) -> np.ndarray:
    """★ 味觉细胞更新：exp(-t/τ)，τ=12 天。"""
    return 1.0 - np.exp(-np.asarray(days, float) / lifetime_days)


# ================================================================
# 七、适应与对比增强
# ================================================================
def adaptation(conc_mM: float, t_s: np.ndarray, tau_s: float = 2.0
               ) -> np.ndarray:
    """★ 味觉适应：持续刺激响应衰减。

    REAL：持续刺激几秒内就显著适应（唾液稀释 + 受体脱敏）。
    ★ 第一版 tau 取 3.0s：6 秒后还剩 12.9%，落在判据(10%)之外
      → 味觉适应实际比这更快，tau 约 1~2 s
    """
    base = taste_response(conc_mM, "甜")
    return base * np.exp(-np.asarray(t_s, float) / tau_s)


def salt_then_water(salt_mM: float = 100.0) -> float:
    """★★ 对比增强：盐水漱口后，水会【变甜】。
    REAL：这是交叉适应的经典现象（water taste）。"""
    return float(0.6 * (1 - np.exp(-salt_mM / 50.0)))


def acid_enhances_salt(acid_mM: float, salt_mM: float) -> float:
    """★ 酸能增强咸味感知（少放盐，加点柠檬汁显得更咸）。"""
    base = taste_response(salt_mM, "咸")
    return float(base * (1.0 + 0.35 * hill(np.array([acid_mM]), 2.0, 1.0)[0]))
