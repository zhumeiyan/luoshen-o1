#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★59 打印机 —— 增材制造：从「描述」到「实体」
================================================================
★★★ 为什么打印机是闭环的最后一块
    眼耳鼻舌皮肤前庭本体觉 → 输入
    手 / 手臂 / 键鼠 / 声音      → 输出，但只能【操作已有】的东西
    打印机                       → 输出，【从无到有】

    ★ 没有打印机，它感知到的世界永远改不了 —— 闭环只有一半
    ★ 有了打印机：感知 → 决策 → 制造 → 再感知自己造的东西
      ★★ 这是 ★30「主动 = 多一条信息通道」的最强形态
         它造的东西，它自己能看、能摸 —— 反馈走自己身上

★★ 核心权衡：层厚 t
    时间 ∝ 1/t        （t 减半 → 时间翻倍）
    粗糙度 Ra ∝ t     （t 减半 → 光滑一倍）
    ★ 两头都不好 → 有真实内部最优

★★★ 最优层厚不是我定的，是【它的感官】定的
    层纹细到「眼睛看不见」且「手摸不出」就够了，再细是浪费时间
    → 眼睛（★16 视锥 / ★25 双眼）给分辨阈值
    → 皮肤（★27 Pacini 振动通道）给触觉阈值
    ★★ 硬依赖：关掉眼睛/皮肤 → 判不了「够不够好」→ 算不出最优层厚
       若仍能算出 = 感官是挂件（★33 / ★44 / ★57 同族）
"""
import numpy as np

# ───────────────────────── 材料（REAL 常见值）
MATERIALS = {
    #           收缩率  层间结合率 玻璃化温度℃  热膨胀系数(1/℃)
    "PLA":  dict(shrink=0.003, interlayer=0.75, tg=60.0,  cte=6.8e-5),
    "ABS":  dict(shrink=0.007, interlayer=0.65, tg=105.0, cte=9.0e-5),
    "PETG": dict(shrink=0.004, interlayer=0.80, tg=80.0,  cte=7.5e-5),
    "尼龙": dict(shrink=0.015, interlayer=0.70, tg=70.0,  cte=1.0e-4),
    "树脂": dict(shrink=0.002, interlayer=0.95, tg=90.0,  cte=5.0e-5),
}


# ══════════════════════════════════════════════════ 1 台阶效应
def cusp_height(t_mm: float, theta_deg: float) -> float:
    """★ 台阶（cusp）高度 —— 分层制造独有的表面缺陷

    theta_deg  表面与【水平面】的夹角
                90° = 垂直壁      → 层完全对齐，cusp = 0 ✅
                45° = 斜面        → cusp = 0.707·t
                 0° = 水平面      → cusp = t

    推导：垂直层厚 t，水平偏移 Δx = t/tan(θ)
          沿表面法线的最大偏差 = Δx·sin(θ) = t·cos(θ)
    """
    th = np.deg2rad(float(theta_deg))
    return float(abs(float(t_mm) * np.cos(th)))


def surface_ra(t_mm: float, theta_deg: float) -> float:
    """★ 算术平均粗糙度 Ra ≈ cusp/4（三角波的 Ra = 峰峰值/4）"""
    return cusp_height(t_mm, theta_deg) / 4.0


# ══════════════════════════════════════════════════ 2 时间
def print_time(height_mm: float, area_mm2: float, t_mm: float,
               speed_mm_s: float = 60.0, nozzle_mm: float = 0.4,
               move_overhead: float = 1.35, infill: float = 0.2) -> float:
    """★ 打印时间（秒）

    ★ 体积流量 Q = 线宽 × 层厚 × 速度
      实际填充体积 = area × height × infill
      时间 = 体积 / Q   × 空驶开销系数

    ★ 与 t 成【反比】—— 这是权衡的一半
    """
    vol = float(area_mm2) * float(height_mm) * float(infill)
    q = float(nozzle_mm) * float(t_mm) * float(speed_mm_s)   # mm³/s
    if q <= 0:
        return float("inf")
    return float(vol / q * float(move_overhead))


# ══════════════════════════════════════════════════ 3 ★★★ 感官阈值
def eye_resolution_um(dist_mm: float = 250.0,
                      maa_arcmin: float = 1.0) -> float:
    """★ 眼睛能分辨的最小特征（μm）—— 决定「层纹看不看得见」

    ★ 用的是 ★16/★25 的视角分辨率：最小可分辨角 MAA
      size = dist × tan(MAA)
    25 cm 处、1 角分 → 72.7 μm
    """
    return float(dist_mm * np.tan(np.deg2rad(maa_arcmin / 60.0)) * 1000.0)


def tactile_response(t_mm: float, theta_deg: float,
                     scan_mm_s: float = 15.0) -> dict:
    """★★ 手摸层纹的强度 —— 复用 ★27 texture_encoding（真模型，不另写）

    ★★ 关键：层纹扫过时是【振动】，不是静态粗糙度
       空间周期 = 层厚 t（相邻层间距）
       扫过频率 f = v / t
       → 进 Pacini(RA2) 带通（★27: 70~1000 Hz，峰 250 Hz）

    ★★★ 因此手对层厚的敏感性是【带通】，不是单调
       t 大 → f 低 → 掉出 Pacini 低频端（但 SA1 空间通道接管）
       t 中 → f ≈ 250 Hz → 落在峰上 → 最容易摸出
       t 小 → f 高 → 掉出高频端 + 台阶本身也小 → 摸不出
    ★ REAL 对照：FDM 0.1~0.2mm 层厚手摸层纹最明显 ✅ 与模型一致

    ★★ v=0（手不动）→ f=0 → 层纹消失（★27 主动触觉）
    """
    from core.skin import texture_encoding
    t_um = float(t_mm) * 1000.0
    if t_um <= 0 or scan_mm_s <= 0:
        return {"freq_hz": 0.0, "RA2": 0.0, "SA1": 0.0, "strength": 0.0}
    enc = texture_encoding(t_um, float(scan_mm_s))
    cusp = cusp_height(t_mm, theta_deg)          # 台阶幅度（mm）
    ra2 = float(enc["RA2_vibration"])
    sa1 = float(enc["SA1_spatial"])
    # ★★ 强度 = 台阶幅度(μm) × 通道响应，两条通道【分开】保留
    #    vib = 振动通道（Pacini 带通）→ 带通，峰在 t≈0.08~0.15
    #    spa = 空间通道（SA1 感受野）→ 单调增，粗层纹靠它
    #    ★ 合在一起会把带通盖掉 —— 必须分开
    cusp_um = cusp * 1000.0
    vib = cusp_um * ra2
    spa = cusp_um * sa1
    return {"freq_hz": float(enc["freq_hz"]), "RA2": ra2, "SA1": sa1,
            "cusp_um": float(cusp_um),
            "vib": float(vib), "spa": float(spa),
            "strength": float(max(vib, spa))}


# ★★ 触觉阈值 —— 用 REAL 锚点标定，不拍脑袋
#   锚点1：FDM 0.05 mm 层厚（Ra≈9 μm）手感【光滑】 → 不可感知
#   锚点2：FDM 0.10 mm 层厚（Ra≈18 μm）层纹【明显】→ 可感知
#   锚点3：FDM 0.30 mm 层厚（Ra≈53 μm）粗台阶【明显】→ 可感知（靠空间通道）
#   → 取 TH_VIB=45 μm·响应, TH_SPA=45 μm·响应 恰好分离锚点1/2 并覆盖锚点3
#   ★ 若阈值拍错，这两个锚点会立刻失配 —— 可证伪
TH_VIB = 45.0
TH_SPA = 45.0


def skin_roughness_threshold_um(t_mm: float = 0.1, theta_deg: float = 45.0,
                                scan_mm_s: float = 15.0) -> float:
    """★ 兼容旧接口：返回等效可感知阈值

    ★ 已修正（两处错误）：
      ① 原写死 0.5 μm（Pacini 位移阈值）—— 混淆了位移阈值与粗糙度阈值
         导致任何层厚都「摸得出」，永远不合格（实测确认）
      ② 原把 vib/spa 相加 —— SA1 单调项把 Pacini 的【带通】盖掉了
    """
    return TH_VIB


def perceptible(t_mm: float, theta_deg: float,
                eye_on: bool = True, skin_on: bool = True,
                dist_mm: float = 250.0) -> dict:
    """★★★ 层纹是否【可感知】—— 眼睛看 + 手摸

    ★★ 若 eye_on=False 或 skin_on=False，对应项必须返回 None
       （不是 0，不是 False）—— 否则上层无法区分「不可感知」与「没测」
       ★ 这样才能用于硬依赖检验
    """
    ra_um = surface_ra(t_mm, theta_deg) * 1000.0
    out = {"ra_um": float(ra_um)}
    if eye_on:
        th_eye = eye_resolution_um(dist_mm)
        out["eye_um"] = float(th_eye)
        out["visible"] = bool(ra_um > th_eye)
    else:
        out["eye_um"] = None
        out["visible"] = None
    if skin_on:
        r = tactile_response(t_mm, theta_deg)
        out["freq_hz"] = r["freq_hz"]
        out["vib"] = r["vib"]
        out["spa"] = r["spa"]
        out["tactile_strength"] = r["strength"]
        out["skin_um"] = TH_VIB
        # ★ 两条通道【任一】超阈值即摸得出
        out["tactile"] = bool(r["vib"] > TH_VIB or r["spa"] > TH_SPA)
    else:
        out["freq_hz"] = None
        out["tactile_strength"] = None
        out["skin_um"] = None
        out["tactile"] = None
    return out


def optimal_layer(theta_deg: float, height_mm: float, area_mm2: float,
                  eye_on: bool = True, skin_on: bool = True,
                  dist_mm: float = 250.0,
                  t_grid=None) -> dict:
    """★★★ 最优层厚：在「不可感知」的前提下，选【最快】的层厚

    ★ 逻辑：细到感官分辨不出就够了 → 再细只是浪费时间
    ★★ 硬依赖：两个感官都关掉 → 没有「不可感知」判据
              → 无法排除任何层厚 → 必须抛错，不许回退到默认

    返回 dict；失败时 ok=False
    """
    if t_grid is None:
        t_grid = np.logspace(np.log10(0.02), np.log10(0.6), 60)
    cands = []
    for t in t_grid:
        p = perceptible(float(t), theta_deg, eye_on, skin_on, dist_mm)
        vis, tac = p["visible"], p["tactile"]
        if vis is None and tac is None:
            continue                      # ★ 两个感官都关 → 无判据
        # 有判据的项必须【全都不】可感知
        checks = [x for x in (vis, tac) if x is not None]
        if any(checks):
            continue
        cands.append((float(t), print_time(height_mm, area_mm2, float(t))))
    if not cands:
        return {"ok": False, "reason": "无感官判据或全部可感知"}
    # ★ 在合格者里选【最快】= 层厚最大
    t_best = max(cands, key=lambda x: x[0])
    return {"ok": True, "t_mm": t_best[0], "time_s": t_best[1],
            "n_cands": len(cands),
            "ra_um": surface_ra(t_best[0], theta_deg) * 1000.0}


# ══════════════════════════════════════════════════ 4 各向异性
def tensile_strength(mat: str, axis: str, base_mpa: float = 50.0) -> float:
    """★ 拉伸强度的方向依赖 —— 分层制造独有

    XY（层内）：材料本体强度
    Z （层间）：层间冷焊，分子扩散不充分 → REAL 为 XY 的 50~80%

    ★ 跟 ★34 肌腱串激、★35 惯性各向异性同族：
      制造方式把各向异性【写进】了材料
    """
    m = MATERIALS.get(mat, MATERIALS["PLA"])
    if axis.upper() in ("XY", "X", "Y", "层内"):
        return float(base_mpa)
    if axis.upper() in ("Z", "层间"):
        return float(base_mpa * m["interlayer"])
    raise ValueError(f"未知轴向: {axis}")


def anisotropy_ratio(mat: str) -> float:
    """Z/XY 强度比（REAL FDM 0.5~0.8，树脂接近 1）"""
    return float(MATERIALS.get(mat, MATERIALS["PLA"])["interlayer"])


# ══════════════════════════════════════════════════ 5 悬垂与支撑
def overhang_ratio(theta_deg: float) -> float:
    """★ 悬垂比例：表面与水平夹角越小（越接近水平下表面），越悬

    45° 规则：θ < 45° 的下表面需要支撑
    ratio = 1 - θ/45，θ=0 → 1（完全悬空），θ≥45 → 0（自支撑）
    """
    th = float(theta_deg)
    if th >= 45.0:
        return 0.0
    return float(np.clip(1.0 - th / 45.0, 0.0, 1.0))


def needs_support(theta_deg: float, is_downward: bool = True) -> bool:
    """★ 是否需支撑：向下的表面 + 倾角 < 45°"""
    if not is_downward:
        return False
    return float(theta_deg) < 45.0


def support_volume(overhang_area_mm2: float, theta_deg: float,
                   gap_mm: float = 0.2) -> float:
    """支撑体积（简化：悬垂面积 × 悬垂高度 × 稀疏率）"""
    r = overhang_ratio(theta_deg)
    if r <= 0:
        return 0.0
    h = 2.0 + 8.0 * r
    return float(overhang_area_mm2 * h * 0.15)


# ══════════════════════════════════════════════════ 6 收缩与翘曲
def warp_mm(mat: str, length_mm: float, bed_adhesion: float = 1.0) -> float:
    """★ 翘曲（mm）—— 收缩被底部约束 → 边角抬起

    ★ 与长度【平方】相关（大件更容易翘，这是 REAL 经验）
    ★ bed_adhesion 1.0 = 无底床粘附抵抗，0 = 完全粘住
    """
    m = MATERIALS.get(mat, MATERIALS["PLA"])
    base = m["shrink"] * float(length_mm) ** 2 / 100.0
    return float(base * float(bed_adhesion))


def dimensional_error(mat: str, nominal_mm: float) -> float:
    """尺寸误差（mm）—— 收缩导致的系统性偏小"""
    return float(-MATERIALS.get(mat, MATERIALS["PLA"])["shrink"]
                 * float(nominal_mm))


# ══════════════════════════════════════════════════ 7 增材 vs 减材
def subtractive_feasible(feature: str) -> bool:
    """★ 减材（CNC）能否加工该特征 —— 刀具可达性限制

    内腔 / 封闭空腔 / 晶格 / 倒扣 → 刀具进不去
    外表面 / 通孔 / 平面          → 可以
    """
    return str(feature) in ("外表面", "通孔", "平面", "开放槽", "台阶")


def additive_feasible(feature: str) -> bool:
    """★ 增材能否加工

    ★ 增材几乎无几何限制（无刀具），但【悬垂】需支撑
    """
    return str(feature) not in ("无支撑大跨桥",)


def compare_process(feature: str) -> dict:
    """★★ 增材 vs 减材 对照 —— 互补，不是替代"""
    sub = subtractive_feasible(feature)
    add = additive_feasible(feature)
    if sub and not add:
        win = "减材"
    elif add and not sub:
        win = "增材"
    elif sub and add:
        # 两者都行 → 比表面质量：减材无台阶，更好
        win = "减材（表面质量）"
    else:
        win = "都不行"
    return {"feature": feature, "subtractive": sub, "additive": add,
            "winner": win}


# ══════════════════════════════════════════════════ 8 ★★ 闭环
def closed_loop(t_mm: float, theta_deg: float,
                eye_on: bool = True, skin_on: bool = True,
                hand_on: bool = True, dist_mm: float = 250.0) -> dict:
    """★★★ 打印 → 自己看 → 自己摸 → 判断是否合格

    ★★ 这是打印机真正的意义：它造的东西，它自己能检验
    ★ 三个感官任一关掉 → 对应结论必须缺失（None），不许编
    """
    p = perceptible(t_mm, theta_deg, eye_on, skin_on, dist_mm)
    out = dict(p)
    # 手：拿起/握持可行性（★34 手）
    if hand_on:
        out["graspable"] = True
        out["grip_note"] = "可握持（★34）"
    else:
        out["graspable"] = None
    # 综合判定
    checks = [p.get("visible"), p.get("tactile")]
    checks = [c for c in checks if c is not None]
    if not checks:
        out["verdict"] = None          # ★ 无判据 → 不许下结论
        out["reason"] = "感官全部关闭，无法检验"
    elif any(checks):
        out["verdict"] = False
        out["reason"] = "层纹可感知，需减小层厚"
    else:
        out["verdict"] = True
        out["reason"] = "层纹不可感知，合格"
    return out
