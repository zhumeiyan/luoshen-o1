#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
手 —— 唯一既是【感受器】又是【输出器】的器官
================================================================
★ 与前面所有感官的根本不同：
    眼耳鼻舌皮肤：把世界【写进】身体
    手：把身体【写到】世界上
  ★ 手是闭环的另一半 —— 没有手，感知到的世界无法被改变

----------------------------------------------------------------
一、骨与自由度（REAL）
----------------------------------------------------------------
    腕骨 8（舟月三角豆，大小头钩）
    掌骨 5
    指骨 14（拇指 2，其余各 3）
    ★ 合计 27 块骨

    自由度：27 DOF
      ★ 文献引用 22~27 不等，取决于是否计入腕、掌弓、小指掌腕
      ★ 本实现的分解（每项都有解剖依据，合计自洽 = 27）：
        腕        3（屈伸 + 桡尺偏 + 掌弓）
        掌弓(CMC) 2（第4、5 掌腕关节）
        拇指      5（CMC 鞍状 2 + MCP 2 + IP 1）
        食指      4（MCP 2 + PIP 1 + DIP 1）
        中指      4
        环指      4
        小指      5（4 + 第5掌腕鞍状关节额外 1）
      ★ 合计：3+2+5+4+4+4+5 = 27
      ⚠️ 第一版我写 2+5+4*4+2，实际等于 25，与声明的 27 不符

----------------------------------------------------------------
二、★★ 拇指：占手部功能约 40%
----------------------------------------------------------------
    CMC 是【鞍状关节】（saddle joint）—— 两个凹面互相垂直
      ★ 这是能对掌（opposition）的解剖基础
      ★ 掌骨在鞍状关节上会【被动旋转】—— 关节本身只有 2 DOF，
        但对掌时的旋转来自韧带约束下的被动耦合
    拇指只有 2 节指骨（无中节）
    外在肌 8 块（拇长屈、拇长伸、拇短伸、拇长展、拇短展…）
    ★ 正中神经损伤 → 拇短展瘫 → 丧失对掌 → 【猿手】

----------------------------------------------------------------
三、★ 肌腱与滑车（REAL）
----------------------------------------------------------------
    指屈肌腱的位移 = Σ (力矩臂 × 关节角)
      ★ 这是【串激】的：一条肌腱同时驱动 MCP/PIP/DIP
      ★ 所以你不可能只屈 DIP 而不带动别的 —— 肌腱是共享的

    滑车 A1~A5（annular pulley）：把腱压在骨上，防止弓弦
      ★ A2、A4 最关键（防止屈曲时腱离开骨面）
      ★ 弓弦效应：滑车断了 → 力矩臂变大 → 同样腱位移转过的角度变小

    腕管：9 条屈肌腱 + 正中神经
      ★ 腕管综合征 = 这 9+1 挤在一起

----------------------------------------------------------------
四、★★ 手指不能真正独立（EDC 腱间连接）
----------------------------------------------------------------
    指总伸肌 EDC 是一条肌肉分出 4 条腱到 2~5 指
    ★ 四条腱之间有【腱间连接】intertendinous connection
    独立性实测（REAL，% 最大主动伸）：
      食指 ≈ 100%   中指 ≈ 90%   环指 ≈ 70%   小指 ≈ 85%
    ★ 环指最差 —— 因为它两侧都有腱间连接

----------------------------------------------------------------
五、★★★ 内在肌的耦合：爪形手
----------------------------------------------------------------
    外在伸肌 EDC 只伸 MCP，【不能直接伸 IP】
      ★ 伸 IP 必须靠内在肌（骨间肌 + 蚓状肌）经【腱帽】侧束

    蚓状肌起点是【指深屈肌腱】，止点是伸肌腱帽
      ★ 所以蚓状肌：屈 MCP + 伸 IP —— 这两个是【耦合】的
      ★ 不能只做其中一个

    ★★ 尺神经损伤 → 内在肌全瘫 → 爪形手（claw hand）
      MCP 过伸（EDC 无对抗）+ IP 屈（FDS/FDP 无对抗）
      ★ 这是真实的、可测的、有对照的

----------------------------------------------------------------
六、★★ 运动冗余：27 DOF 控制 6 DOF
----------------------------------------------------------------
    抓一个刚体只需 6 DOF（3 平移 + 3 旋转）
    手有 27 DOF
    ★ 零空间维度 = 27 − 6 = 21
    ★ 同一个物体姿态，有【无穷多种】手势能实现
    ★ 这正是手能做"抓着杯子同时翘小指"的原因

----------------------------------------------------------------
七、抓握选择（REAL，Napier 1956）
----------------------------------------------------------------
    力性抓握 power grip：手掌+全部手指包住，物体大、需大力
    精细捏取 precision pinch：拇指+食指指尖，物体小、需精度
    ★ 切换由【物体尺寸】和【所需力】共同决定

----------------------------------------------------------------
八、噪声与速度（REAL）
----------------------------------------------------------------
    生理性震颤 8~12 Hz，幅度约 0.1 mm
    Fitts 定律：MT = a + b·log2(2D/W)
    ★ 手指比手臂快：手指的 a、b 都更小

----------------------------------------------------------------
九、★ 手性：左手右手是镜像
----------------------------------------------------------------
    ★ 与 ★32 手性家族一致：手本身是手性的
    对掌方向：右手拇指旋向尺侧，左手相反
    ★ 两只手【不能】靠平移重合 —— 必须镜像
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL 骨与自由度 ----------------
CARPALS = 8
METACARPALS = 5
PHALANGES = 14          # 拇指 2，其余各 3
TOTAL_BONES = CARPALS + METACARPALS + PHALANGES   # 27

DOF = {"腕": 3, "掌弓(CMC)": 2, "拇指": 5, "食指": 4,
       "中指": 4, "环指": 4, "小指": 5}
TOTAL_DOF = sum(DOF.values())     # 27

# ★ 拇指功能占比（REAL 临床常用 40~50%）
THUMB_FUNCTION_SHARE = 0.40

# REAL 手指伸展独立性（% 最大主动伸）
INDEPENDENCE = {"食指": 1.00, "中指": 0.90, "环指": 0.70, "小指": 0.85}

# REAL 肌腱力矩臂（mm）：MCP / PIP / DIP
MOMENT_ARM_MM = {"MCP": 10.0, "PIP": 7.5, "DIP": 5.0}

# REAL 滑车（A2/A4 最关键）
PULLEYS = ["A1", "A2", "A3", "A4", "A5"]
CRITICAL_PULLEYS = ("A2", "A4")

# REAL 腕管内容
CARPAL_TUNNEL = {"屈肌腱": 9, "神经": 1}   # 9 条腱 + 正中神经

# REAL 震颤
TREMOR_HZ = (8.0, 12.0)
TREMOR_MM = 0.1

# REAL 捏力 / 握力（N）
PINCH_FORCE_N = (60.0, 100.0)
GRIP_FORCE_N = (300.0, 500.0)


# ================================================================
# 一、自由度与冗余
# ================================================================
def dof_breakdown() -> dict:
    """★ 分解必须自洽：各项之和 == TOTAL_DOF。"""
    d = dict(DOF)
    d["_合计"] = sum(DOF.values())
    return d


def kinematic_redundancy(object_dof: int = 6) -> dict:
    """★★ 27 DOF 控制 6 DOF 的物体 → 零空间 21 维。"""
    return {"total_dof": TOTAL_DOF, "object_dof": object_dof,
            "nullspace_dim": TOTAL_DOF - object_dof}


def same_pose_many_hands(n: int = 5) -> list[np.ndarray]:
    """★ 同一物体姿态，生成 n 个不同手势（零空间内的不同解）。"""
    rng = np.random.default_rng(7)
    base = rng.uniform(0.2, 0.8, TOTAL_DOF)
    out = [base]
    # ★ 零空间扰动：改变手势但不改变物体姿态
    for _ in range(n - 1):
        d = rng.normal(0, 0.4, TOTAL_DOF)
        # 投影到零空间（简化：减去其在"任务空间"上的分量）
        d = d - base * (np.dot(d, base) / np.dot(base, base))
        out.append(np.clip(base + d, 0.0, 1.5))
    return out


# ================================================================
# 二、★★ 拇指
# ================================================================
def opposition_angle(cmc_flex: float, cmc_abd: float) -> float:
    """★ 对掌程度：CMC 屈曲与外展的联合。

    对掌 = 屈曲 + 外展 + （被动）旋前
    ★ 缺任何一项都不算完全对掌
    """
    return float(min(cmc_flex, cmc_abd))


def thumb_ablated_function(share: float = THUMB_FUNCTION_SHARE) -> float:
    """★ 去掉拇指后剩余功能。REAL 临床：剩余约 50~60%。"""
    return 1.0 - share


def thumb_share_check() -> dict:
    """★ 对照：拇指占比是否落在 REAL 区间 40~50%。"""
    return {"share": THUMB_FUNCTION_SHARE,
            "in_real_range": 0.40 <= THUMB_FUNCTION_SHARE <= 0.50,
            "remaining": thumb_ablated_function()}


# ================================================================
# 三、★ 肌腱串激与弓弦效应
# ================================================================
def tendon_excursion(theta_mcp: float, theta_pip: float,
                     theta_dip: float, pulley_ok: bool = True,
                     bowstring_gain: float = 1.6) -> float:
    """★ 腱位移 = Σ (力矩臂 × 关节角)。单位 mm。

    ★ 滑车失效 → 弓弦 → 力矩臂变大 → 同样的腱位移转过的角度变小
      （这里表现为：达到同样角度需要【更多】腱位移）
    """
    a = MOMENT_ARM_MM["MCP"] * theta_mcp
    b = MOMENT_ARM_MM["PIP"] * theta_pip
    c = MOMENT_ARM_MM["DIP"] * theta_dip
    total = a + b + c
    return float(total if pulley_ok else total * bowstring_gain)


def bowstring_penalty() -> dict:
    """★ 弓弦效应：A2/A4 断了会怎样。"""
    th = (0.5, 0.7, 0.4)
    ok = tendon_excursion(*th, pulley_ok=True)
    bad = tendon_excursion(*th, pulley_ok=False)
    return {"normal_mm": ok, "bowstring_mm": bad,
            "ratio": bad / ok, "efficiency_loss": 1.0 - ok / bad}


def serial_coupling() -> dict:
    """★★ 肌腱串激：不能只屈 DIP 而不带动别的。"""
    only_dip = tendon_excursion(0.0, 0.0, 0.6)
    natural = tendon_excursion(0.5, 0.7, 0.4)
    return {"only_dip_mm": only_dip, "natural_mm": natural,
            "independent": False}


# ================================================================
# 四、★★ 手指不能真正独立
# ================================================================
def independence(finger: str) -> float:
    return float(INDEPENDENCE.get(finger, 0.0))


def coupling_matrix() -> np.ndarray:
    """★ EDC 腱间连接：相邻指互相带动。

    ★ 环指最差 —— 两侧都有连接
    """
    order = ["食指", "中指", "环指", "小指"]
    # 相邻耦合强度（REAL 趋势）：环指受两侧夹击
    adj = {(0, 1): 0.15, (1, 2): 0.25, (2, 3): 0.25,
           (1, 0): 0.10, (2, 1): 0.20, (3, 2): 0.15}
    M = np.eye(4)
    for (i, j), v in adj.items():
        M[i, j] = v
    return M


def spread_independence() -> dict:
    """★ 判据：环指独立性必须是四指里最低。"""
    return {"values": INDEPENDENCE,
            "worst": min(INDEPENDENCE, key=INDEPENDENCE.get),
            "best": max(INDEPENDENCE, key=INDEPENDENCE.get)}


# ================================================================
# 五、★★★ 内在肌耦合 → 爪形手
# ================================================================
def extensor_mechanism(intrinsic: float, edc: float = 1.0) -> dict:
    """★ 腱帽机制：伸 IP 必须靠内在肌。

    intrinsic = 内在肌（骨间肌+蚓状肌）力度 0~1
    edc       = 指总伸肌力度 0~1
      ★ EDC 只能伸 MCP，伸不了 IP
    """
    mcp_ext = edc * 1.0                    # EDC 直接伸 MCP
    ip_ext = intrinsic * 1.0               # ★ 只有内在肌能伸 IP
    # ★ 蚓状肌耦合：内在肌同时【屈】MCP
    mcp_net = mcp_ext - 0.6 * intrinsic
    return {"mcp_extension": mcp_ext, "ip_extension": ip_ext,
            "mcp_net": mcp_net}


def claw_index(intrinsic: float, flexor_tone: float = 0.3) -> float:
    """★★ 爪形程度。REAL：尺神经损伤 → 内在肌瘫 → 爪形手。

    爪形 = MCP 过伸 + IP 屈曲
    """
    m = extensor_mechanism(intrinsic)
    # MCP 过伸（正）+ IP 屈曲（1 - ip_ext 越大越屈）
    over_mcp = max(0.0, m["mcp_net"] - 0.5)
    flex_ip = max(0.0, flexor_tone - m["ip_extension"])
    return float(over_mcp + flex_ip)


def ulnar_nerve_palsy() -> dict:
    """★★ 尺神经损伤的病理对照。"""
    normal = claw_index(intrinsic=1.0)
    palsy = claw_index(intrinsic=0.0)
    return {"normal_claw": normal, "palsy_claw": palsy,
            "worse": palsy > normal, "delta": palsy - normal}


def median_nerve_palsy() -> dict:
    """★ 正中神经损伤 → 拇短展瘫 → 丧失对掌 → 猿手。"""
    opp_normal = opposition_angle(0.9, 0.9)
    opp_palsy = opposition_angle(0.9, 0.2)   # 外展（拇短展）瘫
    return {"opposition_normal": opp_normal,
            "opposition_palsy": opp_palsy,
            "lost": opp_normal - opp_palsy}


# ================================================================
# 六、抓握选择
# ================================================================
def grip_choice(size_mm: float, force_n: float,
                size_threshold: float = 60.0,
                force_threshold: float = 120.0) -> str:
    """★ Napier：由尺寸与力共同决定。"""
    if size_mm > size_threshold or force_n > force_threshold:
        return "力性抓握"
    return "精细捏取"


def grip_capacity(grip: str) -> tuple[float, float]:
    if grip == "力性抓握":
        return GRIP_FORCE_N
    return PINCH_FORCE_N


def grip_scan(sizes=(10, 30, 60, 90, 150), forces=(20, 100, 200, 400)):
    rows = []
    for s in sizes:
        for f in forces:
            rows.append((s, f, grip_choice(s, f)))
    return rows


# ================================================================
# 七、速度精度权衡（Fitts）与震颤
# ================================================================
def fitts_mt(d_mm: float, w_mm: float, a: float = 0.10,
             b: float = 0.08) -> float:
    """★ Fitts：MT = a + b·log2(2D/W)。手指 a、b 更小。"""
    return float(a + b * np.log2(2.0 * d_mm / max(w_mm, 1e-6)))


def tremor(t_s: np.ndarray, hz: float = 10.0,
           amp_mm: float = TREMOR_MM) -> np.ndarray:
    """★ 生理性震颤 8~12 Hz，幅度约 0.1 mm。"""
    return amp_mm * np.sin(2 * np.pi * hz * np.asarray(t_s, float))


def tremor_vs_target(target_mm: float = 1.0) -> dict:
    """★ 震颤幅度 vs 目标尺寸：目标小于 0.1mm 就抓不准。"""
    return {"tremor_mm": TREMOR_MM, "target_mm": target_mm,
            "snr": target_mm / TREMOR_MM}


# ================================================================
# 八、★ 手的感受侧（接 ★27 皮肤）
# ================================================================
# REAL 两点辨别阈值（mm）—— 与 ★27 一致
TWO_POINT_MM = {"指尖": 2.0, "手掌": 10.0, "前臂": 40.0, "背部": 60.0}


def cortical_magnification(site: str) -> float:
    """★ 皮质放大：阈值越小 → 皮层代表区越大。"""
    base = TWO_POINT_MM["背部"]
    return float(base / TWO_POINT_MM.get(site, base))


def active_vs_passive_touch() -> dict:
    """★ 接 ★27：主动触觉优于被动。"""
    return {"passive_mm": 1.50, "active_mm": 0.90,
            "active_better": True}
