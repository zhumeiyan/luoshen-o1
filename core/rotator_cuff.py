#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
肩袖四肌协同稳定 —— ★35 未建模项，本模块补上
================================================================
★ 为什么必须有肩袖（这是 ★35 留下的核心问题）
    关节盂只覆盖肱骨头约 1/3（★35）
    光靠骨性结构，肱骨头会像球放在浅碟上 —— 一推就滑出去
  ★ 肩袖的作用不是【产生运动】，是【把球压进碟里】
    ★ 这叫 凹面压缩 concavity compression

----------------------------------------------------------------
一、四肌（SITS）REAL
----------------------------------------------------------------
    S  supraspinatus    冈上肌    外展启动 + 压缩
    I  infraspinatus    冈下肌    外旋 + 后向压缩
    T  teres minor      小圆肌    外旋 + 后向压缩
    S  subscapularis    肩胛下肌  内旋 + 前向压缩

    起止：都从肩胛骨 → 肱骨大小结节，肌腱融合成【肩袖腱帽】包住肱骨头
    ★ 四肌不是各干各的，是把肱骨头【裹住】

----------------------------------------------------------------
二、★★ 两个机制必须分开看（本模块的核心对照）
----------------------------------------------------------------
    机制A 凹面压缩 concavity compression
      肩袖把肱骨头【压进】关节盂
      ★ 压缩力越大，能抵抗的剪切力越大（类似摩擦锥）

    机制B 力偶 force couple
      纵向力偶：三角肌（向上） vs 冈下+小圆+肩胛下（向下）
        ★ 三角肌单独收缩会把肱骨头【向上拽】撞肩峰
        ★ 肩袖提供向下+向内分量抵消
      横向力偶：肩胛下肌（前） vs 冈下+小圆（后）
        ★ 前后平衡，支点才在盂中心

    ★★ 消融对照：只保留 A 或只保留 B，稳定性都不够
      → 证明两个机制都必需，缺一不可

----------------------------------------------------------------
三、★ 力臂交叉：为什么冈上肌撕裂后【启动】困难
----------------------------------------------------------------
    REAL：三角肌力臂随外展增大（0° 约 1.5cm → 90° 约 3.5cm）
          冈上肌力臂几乎恒定（约 2.2cm）
    ★ 交叉在约 30°：
      0~30°   冈上肌力臂 > 三角肌 → 冈上肌是【启动肌】
      >30°    三角肌接管
    ★ 这解释了：冈上肌撕裂 → 启动外展困难（0~30°）
      但一旦抬过 40~60°，三角肌能接管 → drop arm / 疼痛弧

----------------------------------------------------------------
四、REAL 数值
----------------------------------------------------------------
    肌横截面积 CSA（cm²）与最大肌力（N，按 ~60 N/cm²）
      冈上肌     5.0  → 约 300 N
      冈下肌     7.6  → 约 456 N
      小圆肌     3.0  → 约 180 N
      肩胛下肌   9.0  → 约 540 N
      三角肌    20.0  → 约 1200 N

    肩峰肱骨间距 AHD：正常约 10 mm，< 7 mm 提示肩袖撕裂
    疼痛弧 painful arc：60~120°
    关节盂凹面深度：约 2.5 mm（孟唇再加深约 50%）

----------------------------------------------------------------
五、病理（可证伪的对照）
----------------------------------------------------------------
    ① 冈上肌单独撕裂  → 稳定比变差，但其余三肌仍在
    ② 全层巨大撕裂    → 肱骨头上移，AHD < 7 mm
    ③ 假性麻痹        → 三角肌有力但抬不起来（无支点）
    ④ 盂唇切除        → 凹面深度减半 → 稳定性显著下降
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL: 四肌 ----------------
CUFF = {
    #            CSA(cm²)   力(N)       主功能      压缩方向
    "冈上肌":   dict(csa=5.0,  force=300.0,  role="外展启动", dir="内"),
    "冈下肌":   dict(csa=7.6,  force=456.0,  role="外旋",     dir="后下"),
    "小圆肌":   dict(csa=3.0,  force=180.0,  role="外旋",     dir="后下"),
    "肩胛下肌": dict(csa=9.0,  force=540.0,  role="内旋",     dir="前下"),
}
DELT = dict(csa=20.0, force=1200.0, role="外展主力", dir="上外")

# REAL 特定压应力 ~60 N/cm²
SPECIFIC_TENSION = 60.0

# REAL 肌腱常受累顺序
TEAR_ORDER = ["冈上肌", "冈下肌", "肩胛下肌", "小圆肌"]

# REAL: 肩峰肱骨间距 mm
AHD_NORMAL_MM = 10.0
AHD_PATHOLOGIC_MM = 7.0

# REAL: 疼痛弧
PAINFUL_ARC = (60.0, 120.0)

# REAL: 关节盂凹面深度 mm（盂唇再加深约 50%）
GLENOID_DEPTH_MM = 2.5
LABRUM_GAIN = 1.5          # 盂唇使有效深度 ×1.5

# ★ 残余压缩（N）：肩袖全断后仍有骨性+关节囊+肱二头肌长头+被动张力
#   ⚠️ 没有这一项，全断时稳定比会发散到 5e8（无意义的数）
MIN_COMPRESSION_N = 80.0

# REAL: 力臂（cm）
MA_SUPRA_CM = 2.2                        # 冈上肌，近乎恒定
MA_DELTOID_CM = (1.5, 3.5)               # 三角肌 0° → 90°


# ================================================================
# 一、四肌与力
# ================================================================
def cuff_list() -> list:
    return list(CUFF.keys())


def cuff_force(m: str, scale: float = 1.0) -> float:
    return CUFF[m]["force"] * scale


def total_compression(intact: list | None = None) -> float:
    """★ 四肌合力中【压向关节盂】的分量之和。"""
    intact = intact if intact is not None else cuff_list()
    # 每块肌的力只有一部分用于压缩（其余用于旋转）
    # REAL 简化：压缩分量系数
    share = {"冈上肌": 0.60, "冈下肌": 0.45,
             "小圆肌": 0.45, "肩胛下肌": 0.50}
    return float(sum(CUFF[m]["force"] * share[m] for m in intact))


def deltoid_shear(abduct_deg: float) -> float:
    """★ 三角肌的【向上剪切】分量 —— 这是要被抵消的坏东西。

    ★ 外展角越大，三角肌越接近垂直向上拉 → 剪切越大
    """
    th = np.deg2rad(abduct_deg)
    # 三角肌力方向相对肱骨：外展时向上分量增大
    up = np.sin(th) * 0.5 + 0.5 * (th / (np.pi / 2))
    return float(DELT["force"] * np.clip(up, 0.0, 1.0))


# ================================================================
# 二、★★ 稳定比 = 剪切 / 压缩（越小越稳）
# ================================================================
def stability_ratio(intact: list | None = None, abduct_deg: float = 60.0,
                    labrum: bool = True,
                    concavity: bool = True,
                    force_couple: bool = True) -> dict:
    """★★ 核心指标：稳定比 = 剪切 / 压缩（REAL 称 stability ratio）。

    ★ 消融开关（这是本模块的重点）：
      concavity    False → 关掉【凹面压缩】机制A
      force_couple False → 关掉【力偶】机制B
    ★ 关掉任一个，稳定比都应变差 —— 证明两个机制都必需

    ⚠️ 本函数第二版修了两个 bug：
      ① 肩袖全断时 comp → 0，稳定比发散到 5e8（无意义的数）
         → 加 MIN_COMPRESSION_N：关节囊/肱二头肌长头/被動张力的残余
      ② force_couple=True 时即使 intact 为空也执行 shear*=0.55
         → 没有肌肉就不可能形成力偶，这是永真折扣
    """
    intact = intact if intact is not None else cuff_list()

    shear = deltoid_shear(abduct_deg)

    # ---- 机制A：凹面压缩 ----
    comp = 0.0
    if concavity:
        comp += total_compression(intact)
    else:
        # 没有凹面压缩，等效凹面只剩骨性浅碟
        comp += total_compression(intact) * 0.35

    # ---- 机制B：力偶（★ 必须依赖真实存在的肌肉）----
    post_N = sum(CUFF[m]["force"] for m in intact
                 if m in ("冈下肌", "小圆肌")) * 0.30
    ant_N = CUFF["肩胛下肌"]["force"] * 0.30 if "肩胛下肌" in intact else 0.0
    couple_N = post_N + ant_N
    if force_couple and couple_N > 0:
        comp += couple_N
        # ★ 抵消比例正比于力偶强度（有肌肉才打折，没有就不打折）
        relief = 1.0 - 0.45 * min(1.0, couple_N / 300.0)
        shear *= relief

    # 盂唇加深凹面 → 同样压缩能抵抗更多剪切
    if labrum:
        comp *= LABRUM_GAIN

    # ★ 残余压缩：骨性 + 关节囊 + 肱二头肌长头 + 被动张力
    comp += MIN_COMPRESSION_N

    return {"shear_N": float(shear), "compression_N": float(comp),
            "ratio": float(shear / comp),
            "stable": float(shear / comp) < 0.60}


def ablation() -> dict:
    """★★ 消融对照：分离机制A（凹面压缩）与机制B（力偶）。"""
    full = stability_ratio()
    noA = stability_ratio(concavity=False)
    noB = stability_ratio(force_couple=False)
    neither = stability_ratio(concavity=False, force_couple=False)
    return {"全开": full["ratio"], "关A(凹面压缩)": noA["ratio"],
            "关B(力偶)": noB["ratio"], "两个都关": neither["ratio"],
            "A必需": noA["ratio"] > full["ratio"],
            "B必需": noB["ratio"] > full["ratio"]}


def tear_scan():
    """★ 按 REAL 撕裂顺序逐个切掉，看稳定比怎么恶化。"""
    rows = []
    intact = cuff_list()
    rows.append(("完整", stability_ratio(intact)["ratio"],
                 stability_ratio(intact)["stable"]))
    gone = []
    for m in TEAR_ORDER:
        gone.append(m)
        left = [x for x in cuff_list() if x not in gone]
        r = stability_ratio(left)
        rows.append((f"切到{m}", r["ratio"], r["stable"]))
    return rows


# ================================================================
# 三、★ 力臂交叉：冈上肌是启动肌
# ================================================================
def moment_arm_supra(_abduct_deg: float = 0.0) -> float:
    """★ 冈上肌力臂近乎恒定（REAL 约 2.2 cm）。"""
    return MA_SUPRA_CM


def moment_arm_deltoid(abduct_deg: float) -> float:
    """★ 三角肌力臂随外展【增大】（REAL 0°约1.5 → 90°约3.5 cm）。"""
    lo, hi = MA_DELTOID_CM
    return float(lo + (hi - lo) * np.clip(abduct_deg, 0, 90) / 90.0)


def crossing_angle() -> float | None:
    """★ 交叉角：三角肌力臂超过冈上肌的那个角度。"""
    for d in np.arange(0, 90.1, 0.5):
        if moment_arm_deltoid(d) >= moment_arm_supra(d):
            return float(d)
    return None


def startup_scan():
    """★ 0~90° 扫描，看谁主导。"""
    rows = []
    for d in [0, 15, 30, 45, 60, 90]:
        ms = moment_arm_supra(d)
        md = moment_arm_deltoid(d)
        rows.append((d, ms, md, "冈上肌" if ms > md else "三角肌"))
    return rows


# ================================================================
# 四、★ 病理：肱骨头上移、AHD、假性麻痹
# ================================================================
def humeral_head_migration(intact: list | None = None,
                           max_mm: float = 6.0) -> dict:
    """★ 肩袖失效 → 三角肌把肱骨头【向上拽】→ AHD 变小。"""
    intact = intact if intact is not None else cuff_list()
    lost = [m for m in cuff_list() if m not in intact]
    frac = len(lost) / len(cuff_list())
    up = frac * max_mm
    ahd = AHD_NORMAL_MM - up
    return {"torn": lost, "up_mm": float(up),
            "AHD_mm": float(ahd),
            "pathologic": ahd < AHD_PATHOLOGIC_MM}


def pseudoparalysis(intact: list | None = None) -> dict:
    """★★ 假性麻痹：三角肌有力，但抬不起来 —— 因为没有支点。

    ★ 对照：三角肌【肌力】不变，变的是【能不能形成支点】
    """
    intact = intact if intact is not None else cuff_list()
    r = stability_ratio(intact, abduct_deg=60.0)
    # 三角肌力仍在
    delt_ok = DELT["force"] > 0
    # 但没有压缩 → 无法把力转成外展力矩
    can_abduct = r["stable"]
    return {"deltoid_force_N": DELT["force"], "deltoid_intact": delt_ok,
            "stable": can_abduct,
            "pseudoparalysis": delt_ok and not can_abduct}


def painful_arc(abduct_deg: float) -> bool:
    """★ 疼痛弧 60~120°：肩峰下撞击。"""
    lo, hi = PAINFUL_ARC
    return lo <= abduct_deg <= hi


def painful_arc_scan():
    return [(d, painful_arc(d)) for d in [0, 30, 60, 90, 120, 150]]


# ================================================================
# 五、★ 关节反作用力
# ================================================================
def joint_reaction(abduct_deg: float, bodyweight_N: float = 700.0,
                   intact: list | None = None) -> dict:
    """★ 盂肱关节反作用力。REAL：外展 90° 时约 0.9 倍体重。"""
    intact = intact if intact is not None else cuff_list()
    r = stability_ratio(intact, abduct_deg)
    # 力越大、越不稳 → 反作用力越大
    scale = 0.45 + 0.35 * np.clip(abduct_deg / 90.0, 0, 1)
    jrf = bodyweight_N * scale * (1.0 + 0.5 * r["ratio"])
    return {"abduct_deg": abduct_deg, "ratio": r["ratio"],
            "JRF_N": float(jrf), "x_bodyweight": float(jrf / bodyweight_N)}
