#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
手臂与肩膀 —— 把手【送到】空间里去的那一层
================================================================
★ 手（★34）是末端执行器，但它自己到不了任何地方
★ 手臂负责【定位】，肩膀负责【朝向】

----------------------------------------------------------------
一、★ 肩：全身活动度最大的关节，代价是稳定性
----------------------------------------------------------------
    ★ 盂肱关节 GH：肱骨头 vs 肩胛盂
      ★ 关节盂只覆盖肱骨头的约 1/3 —— 这是球窝关节里最浅的
      ★ 所以肩能转得最多，也最容易脱位（REAL：肩脱位占全部关节脱位 50%）

    肩复合体由【四个】关节协同（不是单一关节）：
      GH  盂肱关节
      AC  肩锁关节
      SC  胸锁关节
      ST  肩胛胸壁关节（不是真关节，是滑动界面）

    ★★ 肩肱节律 scapulohumeral rhythm（REAL，2:1）
      手臂外展 180° = GH 120° + 肩胛骨上旋 60°
      ★ 比例约 2:1
      ★ 肩胛骨不动，手臂只能抬到约 120°（REAL）
      ★ 肩胛固定（翼状肩/胸长神经损伤）→ 外展受限

----------------------------------------------------------------
二、★ 肘：稳定与旋转分离
----------------------------------------------------------------
    肱尺关节：只做屈伸（真正的铰链，活动度 0~145°）
    肱桡关节：参与屈伸
    ★★ 上尺桡关节：旋前/旋后（前臂旋转，REAL 各约 80~90°）
      ★ 旋前/旋后【不发生在肘】—— 是桡骨绕尺骨转
      ★ 这跟 GH 不同：GH 是球窝，这里是一个轴

    提携角 carrying angle：REAL 男 5~10°，女 10~15°
      ★ 完全伸直时前臂不是跟手臂一条直线，是向外偏的

----------------------------------------------------------------
三、★ 腕：两个自由度，但主要是【姿态】而非【位置】
----------------------------------------------------------------
    屈伸 REAL 70~85°（屈 ~80，伸 ~70）
    桡尺偏 REAL 桡偏 ~20°，尺偏 ~35°
      ★★ 不对称！尺偏比桡偏大约 15°
      ★ 原因：桡骨茎突比尺骨茎突低约 1~1.5 cm，桡侧先撞上

    ★ 腕中立位握力最大（REAL）
      屈/伸 30° 时握力下降约 20~30%

----------------------------------------------------------------
四、★★ 七自由度冗余（肩3 + 肘2 + 腕2）
----------------------------------------------------------------
    ★ 经典：手臂定位到空间一点只需 6 DOF（3 位置 + 3 朝向）
      但人类手臂是 7 DOF（肩3 + 肘1 + 前臂旋1 + 腕2 = 7）
    ★ 第 7 个自由度 = 【自运动】self-motion
      ★ 手位置姿态【固定不动】，肘还能在一条圆上摆动
      ★ 这个圆叫 redundancy circle / self-motion manifold

    ★ 这是 Bernstein 问题的核心：
      自由度太多 → 必须靠【协同】约束，否则无法控制

----------------------------------------------------------------
五、★★★ 速度-精度权衡（Fitts）与惯性各向异性
----------------------------------------------------------------
    ★ 端点质量矩阵不是各向同性的：
      沿手臂【径向】的有效质量 ≈ 小
      【切向】≈ 大 或相反，取决于姿势
    ★ REAL：伸直手臂时，径向移动比切向快

----------------------------------------------------------------
六、★ 肌：双关节肌（跨两个关节）
----------------------------------------------------------------
    肱二头肌：肩 + 肘（长头跨肩）
    肱三头肌长头：肩 + 肘
    ★ 双关节肌 → 一个肌肉影响两个关节
      ★ 所以"屈肘"时肩的位置会改变肘能发出的力

----------------------------------------------------------------
七、★ 与 ★29 本体觉 / ★28 前庭 的接口
----------------------------------------------------------------
    手臂位置 = 本体觉（肌梭 + 关节受体）
    头部朝向 = 前庭 + 颈本体觉
    ★ 手在【空间】里 = 手臂 + 头 + 眼 的坐标系串联
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL: 肩 ----------------
GH_COVERAGE = 1.0 / 3.0          # 关节盂只覆盖肱骨头约 1/3
SHOULDER_DISLOCATION_SHARE = 0.50  # 肩脱位占全部关节脱位 ~50%

# ★★ 肩肱节律 REAL 2:1
GH_ABDUCT_MAX = 120.0
SCAPULA_UPROT_MAX = 60.0
SHOULDER_COMPLEX = ("GH 盂肱", "AC 肩锁", "SC 胸锁", "ST 肩胛胸壁")

# ---------------- REAL: 肘 ----------------
ELBOW_FLEX_RANGE = (0.0, 145.0)
PRONATION_DEG = (0.0, 85.0)      # 旋前 REAL ~80~90
SUPINATION_DEG = (0.0, 85.0)     # 旋后
CARRYING_ANGLE = {"男": (5.0, 10.0), "女": (10.0, 15.0)}

# ---------------- REAL: 腕 ----------------
WRIST_FLEX_DEG = (70.0, 85.0)     # 屈
WRIST_EXT_DEG = (70.0, 85.0)
WRIST_RADIAL_DEG = 20.0           # 桡偏（小）
WRIST_ULNAR_DEG = 35.0            # 尺偏（大）
RADIAL_STYLOID_LOWER_MM = 1.2     # 桡骨茎突比尺骨茎突低 ~1~1.5cm

# ---------------- 自由度 ----------------
DOF_ARM = {"肩": 3, "肘(屈伸)": 1, "前臂(旋)": 1, "腕": 2}
TOTAL_ARM_DOF = sum(DOF_ARM.values())   # 7


# ================================================================
# 一、★ 肩：活动度最大，稳定性最差
# ================================================================
def gh_stability() -> dict:
    """★ 关节盂只覆盖 1/3 → 能转最多，也最容易脱位。"""
    return {"coverage": GH_COVERAGE,
            "dislocation_share": SHOULDER_DISLOCATION_SHARE,
            "tradeoff": "活动度 ↔ 稳定性"}


def shoulder_complex() -> tuple:
    """★ 肩不是单一关节，是四个关节协同。"""
    return SHOULDER_COMPLEX


def scapulohumeral(total_abduct: float = 180.0,
                   ratio: float = 2.0) -> dict:
    """★★ 肩肱节律：外展 = GH + 肩胛上旋，比例约 2:1。"""
    gh = total_abduct * ratio / (ratio + 1.0)
    sc = total_abduct * 1.0 / (ratio + 1.0)
    return {"total_deg": total_abduct, "gh_deg": gh,
            "scapula_deg": sc, "ratio": ratio}


def scapula_frozen() -> dict:
    """★★ 肩胛骨不动 → 外展只能到约 120°（REAL）。"""
    return {"max_with_scapula": 180.0, "max_frozen": GH_ABDUCT_MAX,
            "loss_deg": 180.0 - GH_ABDUCT_MAX}


# ================================================================
# 二、★ 肘：屈伸与旋转分离
# ================================================================
def elbow_flexion(angle: float) -> bool:
    lo, hi = ELBOW_FLEX_RANGE
    return lo <= angle <= hi


def forearm_rotation(kind: str) -> tuple:
    """★ 旋前/旋后【不在肘】，是桡骨绕尺骨转。"""
    return PRONATION_DEG if kind == "旋前" else SUPINATION_DEG


def rotation_axis_check() -> dict:
    """★ 对照：肘是铰链（1轴），前臂旋转是另一根轴，两者分离。"""
    return {"elbow_dof": 1, "forearm_dof": 1,
            "same_axis": False,
            "note": "屈伸与旋前旋后是两根不同的轴"}


def carrying_angle(sex: str = "男") -> tuple:
    lo, hi = CARRYING_ANGLE.get(sex, CARRYING_ANGLE["男"])
    return (lo, hi)


def carrying_check() -> dict:
    """★ 女性提携角大于男性（REAL）。"""
    m = CARRYING_ANGLE["男"][1]
    f = CARRYING_ANGLE["女"][1]
    return {"male_max": m, "female_max": f, "female_larger": f > m}


# ================================================================
# 三、★ 腕：尺偏 > 桡偏（不对称）
# ================================================================
def wrist_deviation() -> dict:
    """★★ 尺偏 35° vs 桡偏 20° —— 差 15°。"""
    return {"radial_deg": WRIST_RADIAL_DEG,
            "ulnar_deg": WRIST_ULNAR_DEG,
            "asymmetry_deg": WRIST_ULNAR_DEG - WRIST_RADIAL_DEG,
            "cause_mm": RADIAL_STYLOID_LOWER_MM}


def grip_vs_wrist(flex_deg: float, max_n: float = 400.0) -> float:
    """★ 腕中立位握力最大，屈伸 30° 掉 20~30%（REAL）。"""
    d = abs(flex_deg)
    loss = min(0.35, d / 30.0 * 0.25)
    return float(max_n * (1.0 - loss))


def wrist_neutral_best() -> dict:
    return {"neutral_N": grip_vs_wrist(0),
            "flex30_N": grip_vs_wrist(30),
            "ext30_N": grip_vs_wrist(-30),
            "neutral_best": grip_vs_wrist(0) > grip_vs_wrist(30)}


# ================================================================
# 四、★★ 七自由度冗余：自运动（self-motion）
# ================================================================
def arm_dof() -> dict:
    d = dict(DOF_ARM); d["_合计"] = TOTAL_ARM_DOF
    return d


def self_motion(n: int = 8, elbow_swing: float = 1.2):
    """★★ 手的位置和姿态不动，肘还能在一条圆上摆。

    返回 n 个不同的肘角，对应【同一个】手位姿。
    """
    return [float(elbow_swing * np.cos(2 * np.pi * i / n))
            for i in range(n)]


def redundancy_check() -> dict:
    """★ 7 DOF 控制 6 DOF → 冗余 1 维 → 自运动流形是一条圆。"""
    return {"arm_dof": TOTAL_ARM_DOF, "task_dof": 6,
            "redundancy": TOTAL_ARM_DOF - 6}


def bernstein_problem() -> dict:
    """★ 自由度太多 → 必须靠协同约束。"""
    return {"statement": "DOF 超过任务需求 → 解不唯一 → 需协同",
            "arm_dof": TOTAL_ARM_DOF, "hand_dof": 27,
            "total_dof": TOTAL_ARM_DOF + 27}


# ================================================================
# 五、★★ 惯性各向异性（端点质量矩阵）
# ================================================================
def endpoint_mass_matrix(shoulder_deg: float = 0.0,
                         elbow_deg: float = 90.0):
    """★ 端点有效质量不是各向同性的。

    伸直手臂（肘角小）时：径向（沿手臂）比切向【重】还是【轻】？
    ★ REAL：伸直时沿臂方向的有效质量更小（更容易沿臂推拉）
      —— 因为力沿骨传递，不产生关节力矩
    """
    s = np.deg2rad(shoulder_deg); e = np.deg2rad(elbow_deg)
    # 简化平面两连杆：雅可比 J
    L1, L2 = 0.30, 0.28
    j11 = -L1 * np.sin(s) - L2 * np.sin(s + e)
    j12 = -L2 * np.sin(s + e)
    j21 = L1 * np.cos(s) + L2 * np.cos(s + e)
    j22 = L2 * np.cos(s + e)
    J = np.array([[j11, j12], [j21, j22]])
    # 端点质量矩阵 M = (J J^T)^{-1}（关节惯量取单位阵）
    try:
        M = np.linalg.inv(J @ J.T)
    except np.linalg.LinAlgError:
        M = np.eye(2) * 1e6
    return M


def anisotropy(shoulder_deg: float = 0.0, elbow_deg: float = 90.0) -> dict:
    """★ 各向异性 = 有效质量最大/最小之比。"""
    M = endpoint_mass_matrix(shoulder_deg, elbow_deg)
    w = np.linalg.eigvalsh(M)
    return {"min_mass": float(w[0]), "max_mass": float(w[-1]),
            "ratio": float(w[-1] / max(w[0], 1e-9)),
            "anisotropic": float(w[-1] / max(w[0], 1e-9)) > 1.5}


def anisotropy_scan():
    """★ 扫不同肘角：伸直 vs 弯曲，各向异性不同。"""
    rows = []
    for sh in [0.0, 30.0, 60.0]:
        for el in [20.0, 45.0, 90.0, 135.0]:
            a = anisotropy(sh, el)
            rows.append((sh, el, a["ratio"]))
    return rows


# ================================================================
# 六、★ 双关节肌
# ================================================================
BIARTICULAR = {
    "肱二头肌": ("肩", "肘"),
    "肱三头肌长头": ("肩", "肘"),
    "股直肌": ("髋", "膝"),
    "腓肠肌": ("膝", "踝"),
}


def biarticulate_coupling(muscle: str, shoulder_deg: float,
                          elbow_deg: float) -> dict:
    """★ 一个肌肉影响两个关节 → 肘能发出的力受肩姿势影响。"""
    if muscle not in BIARTICULAR:
        return {"error": f"未知肌肉 {muscle}"}
    # 简化：肘屈力矩随肩屈角增大而减小（双关节肌被预先拉长）
    eff = float(np.cos(np.deg2rad(shoulder_deg)) * 0.5 + 0.5)
    return {"muscle": muscle, "joints": BIARTICULAR[muscle],
            "shoulder_deg": shoulder_deg,
            "elbow_torque_factor": round(eff, 3)}


def biarticulate_check() -> dict:
    a = biarticulate_coupling("肱二头肌", 0.0, 90.0)
    b = biarticulate_coupling("肱二头肌", 90.0, 90.0)
    return {"shoulder0": a["elbow_torque_factor"],
            "shoulder90": b["elbow_torque_factor"],
            "differs": a["elbow_torque_factor"] != b["elbow_torque_factor"]}


# ================================================================
# 七、★ 与本体觉/前庭的接口
# ================================================================
def chain_to_space() -> dict:
    """★ 手在空间里 = 一串坐标系串联。"""
    return {"chain": ["躯干", "肩胛(ST)", "肩(GH)", "上臂",
                      "肘", "前臂(旋)", "腕", "手(★34)"],
            "position_sense": "★29 本体觉（肌梭+关节受体）",
            "head_orientation": "★28 前庭 + 颈本体觉",
            "eye": "★17/★25 双眼",
            "note": "任何一环错，手在空间的坐标就错"}


def coordinate_error(chain_deg_error: float = 1.0,
                     n_links: int = 7, lever_m: float = 0.6) -> float:
    """★ 每节 1° 误差，到手端会放大多少（REAL：误差沿链累积）。"""
    total_rad = np.deg2rad(chain_deg_error * np.sqrt(n_links))
    return float(total_rad * lever_m * 1000.0)  # mm
