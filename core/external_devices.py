#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★60 外挂感官 —— 微表情动态捕捉 / 无人机摄像 / 其他采集设备
================================================================
★★★ 跟前面所有层的根本区别
    眼耳鼻舌皮肤  → 长在身上，参数被解剖和物理锁死
    外挂设备      → 参数【可选】，能突破原生极限

★★ 但这不是"更好"，是【换一组权衡】
    原生：零延迟、零功耗、永不断连，但量程被锁死
    外挂：量程突破，但引入原生没有的失效模式
          ★ 延迟 / 时间混叠 / 运动模糊 / 供电 / 标定

★★★ 三类扩展（按突破方式分，不是按设备名分）
    A 扩量程/分辨率：高速相机(时间)、深度相机(基线)、麦克风阵列(基线)、激光雷达
    B 扩波段/模态  ：红外热成像、事件相机(DVS)、紫外
    C 改变视点     ：无人机、云台、内窥镜
    ★ A 改变"能测到多少"，B 改变"能测什么"，C 改变"从哪测"

★★★★ 贯穿本轮的一条（跟 ★33/★50 同族）
    外挂比原生【更容易】变成挂件 —— 因为没有它系统照样能跑
    ★ 所以每个设备都必须做消融：关掉 → 能力必须真的消失
"""
import numpy as np

# ══════════════════════════════ 一、微表情动态捕捉
# REAL: 宏表情 0.5~4 s，微表情 1/25~1/5 s（40~200 ms）
MICRO_T_MIN_S, MICRO_T_MAX_S = 0.04, 0.20
# REAL: FACS 动作单元位移幅度，微表情幅度小（0.5~2 mm）
MICRO_AMP_MIN_MM, MICRO_AMP_MAX_MM = 0.5, 2.0
# REAL: 未训练者识别准确率 ~50%，算法+高速相机 70~85%
REAL_HUMAN_ACC = 0.50
REAL_ALGO_ACC = 0.78


def maa_size_mm(dist_mm: float, maa_arcmin: float = 1.0) -> float:
    """★ 眼睛在 dist 处的最小可分辨尺寸（mm）—— 复用 ★59"""
    return float(dist_mm * np.tan(np.deg2rad(maa_arcmin / 60.0)))


# ★★ REAL 参数
SACCADE_LATENCY_MS = 200.0     # 扫视潜伏期（★43 用过，REAL 150~250）
FOVEA_DEG          = 2.0       # 中央凹直径（REAL 1.5~2°）
FACE_WIDTH_MM      = 200.0     # 人脸宽度
PERIPHERAL_W       = 0.05      # 周边视觉权重（★43: 中央凹/周边 ≈ 20×）
ALGO_ACC           = 0.85      # 算法精度上限（REAL 微表情识别 70~85%）


def face_angle_deg(dist_mm: float, face_w_mm: float = FACE_WIDTH_MM) -> float:
    """★ 人脸在 dist 处的视角张角"""
    return float(np.degrees(2 * np.arctan(face_w_mm / 2.0 / float(dist_mm))))


AU_SEP_MM = 80.0          # 眼周(AU6) 与 嘴角(AU12) 的间距


def au_separation_deg(dist_mm: float, sep_mm: float = AU_SEP_MM) -> float:
    """★ 两个关键 AU 区域的视角间距"""
    return float(np.degrees(2 * np.arctan(sep_mm / 2.0 / float(dist_mm))))


def regions_needed(dist_mm: float, fovea_deg: float = FOVEA_DEG) -> int:
    """★ 需要几次注视

    ★★ 只要两个区域【同时】落进中央凹 → 1 次就够
       否则必须扫视 → 2 次
    ★ 注意：不是整张脸扫一遍（只需两个 AU 区域）
    """
    return 1 if au_separation_deg(dist_mm) <= float(fovea_deg) else 2


def amp_arcmin(amp_mm: float, dist_mm: float) -> float:
    """★ AU 位移幅度的视角度（角分）"""
    return float(np.degrees(2 * np.arctan(amp_mm / 2.0 / float(dist_mm))) * 60)


# ★★ 低对比度 + 动态 → 等效视敏度显著变差
#    REAL: 静态高对比 MAA ≈ 1 角分；低对比度皮肤形变 + 运动中判断
#          等效 MAA 差 2~4 倍（dynamic / low-contrast visual acuity）
MAA_EFFECTIVE_ARCMIN = 3.0
# ★ 调节近点（REAL：青年 ~100mm，中年 ~250mm，老视更大）
NEAR_POINT_MM = 250.0


def accommodation_penalty(dist_mm: float,
                          near_point_mm: float = NEAR_POINT_MM) -> float:
    """★ 近于调节近点 → 模糊（REAL：眼睛有最近清晰距离）"""
    d = float(dist_mm)
    if d >= float(near_point_mm):
        return 1.0
    return float(np.clip((d / float(near_point_mm)) ** 2, 0.0, 1.0))


def space_factor(amp_mm: float, dist_mm: float,
                 maa_arcmin: float = MAA_EFFECTIVE_ARCMIN) -> float:
    """★★ 空间分辨充分度：需 ≥2 个可分辨单元（MAA）"""
    return float(np.clip(amp_arcmin(amp_mm, dist_mm)
                         / (2.0 * float(maa_arcmin)), 0.0, 1.0))


def time_factor(t_s: float, fps: float) -> float:
    """★★ 时间采样充分度 —— Nyquist（n = T·fps，至少 2 帧）"""
    n = float(t_s) * float(fps)
    return float(np.clip(n - 1.0, 0.0, 1.0))


def micro_detect_native(t_s: float, dist_mm: float, amp_mm: float,
                        latency_ms: float = SACCADE_LATENCY_MS) -> float:
    """★★★ 裸眼检出率 —— 视觉是【串行】的

    ★★ 核心机制：一次注视只有 ~2° 的中央凹是高分辨的，
       而人脸在 1m 处张角 ~11° → 必须靠扫视逐块看
       但微表情只持续 40~200ms，扫视潜伏期就要 ~200ms
       ★ 扫到第二个区域时，第一个已经过去了

    ★★★ 距离有【内部最优】—— 两个相反的方向
       近：两点张角大 → 一次看不全 → 要扫视 → 时间不够（串行瓶颈）
       远：两点挤进中央凹 → 1 次够，但 AU 位移的视角太小 → 看不清幅度
       ★ 近端受【时间】限，远端受【空间】限 → 中间最优

    ★★ 与 ★55 的交叉：投影机制对【可预测】事件有效（提前 1200ms 准备）
       但微表情恰恰是【不可预测】的（被压抑情绪的泄露）
       → 投影失效 → 裸眼漏检
    """
    need = regions_needed(dist_mm)
    n_avail = 1 + int(np.floor(float(t_s) * 1000.0 / float(latency_ms)))
    cov = float(min(n_avail, need)) / float(need)
    cov = cov + (1.0 - cov) * PERIPHERAL_W          # 未覆盖部分靠周边
    return float(cov * space_factor(amp_mm, dist_mm)
                 * accommodation_penalty(dist_mm))


def micro_detect_device(t_s: float, fps: float,
                        algo_acc: float = ALGO_ACC) -> float:
    """★★ 设备检出率 —— 【并行】全画幅

    ★ 没有中央凹限制：所有像素同时记录 → 不受扫视潜伏期约束
    只受时间采样（Nyquist）和算法精度限制
    """
    return float(time_factor(t_s, fps)) * float(algo_acc)


def micro_detect_rate(fps: float, dist_mm: float,
                      optical_gain: float = 1.0,
                      native: bool = False,
                      n: int = 4000, seed: int = 7) -> float:
    """★ 微表情检出率（蒙特卡洛，对时长与幅度同时采样）

    native=True  → 【串行扫视】模型（眼 CFF ~60Hz 对 40ms 已足够，不是瓶颈）
    native=False → 【并行全画幅】模型（只受 fps 的 Nyquist 与算法精度约束）
    """
    rng = np.random.default_rng(seed)
    ts = rng.uniform(MICRO_T_MIN_S, MICRO_T_MAX_S, n)
    am = rng.uniform(MICRO_AMP_MIN_MM, MICRO_AMP_MAX_MM, n)
    if native:
        return float(np.mean([micro_detect_native(x, dist_mm, y)
                              for x, y in zip(ts, am)]))
    # ★★ 光学增益 = 等效拉近距离（视角放大 g 倍），【不是】同时缩小物体
    #    bug 记录：曾写成 space_factor(y/g, dist/g) → 两者相除抵消，gain 恒无效
    g = max(float(optical_gain), 1e-9)
    sf = np.mean([space_factor(y, dist_mm / g) for y in am])
    return float(np.mean([micro_detect_device(x, fps) for x in ts]) * sf)


def optimal_distance(grid=None) -> dict:
    """★★ 裸眼最优观察距离（近端时间限、远端空间限）"""
    if grid is None:
        grid = np.linspace(300, 4000, 120)
    vals = [micro_detect_rate(60.0, d, native=True) for d in grid]
    i = int(np.argmax(vals))
    return {"dist_mm": float(grid[i]), "rate": float(vals[i]),
            "interior": bool(0 < i < len(grid) - 1)}


# ─────────── Duchenne：真笑 vs 假笑（★ 可证伪，不可伪装）
def duchenne_score(au6: float, au12: float) -> float:
    """★★★ 真笑判据：AU6（眼轮匝肌）+ AU12（颧大肌）

    REAL（Duchenne / Ekman）：
      真笑 = AU6 + AU12      AU6 绕眼，【难以随意控制】
      假笑 = 仅 AU12         颧大肌可随意控制
    ★★ 可证伪：给"只动 AU12"必须判假；AU6 上升必须单调抬高真笑分
    ★ 这是"真 vs 假"的硬判据 —— 靠的是【能不能随意控制】，不是幅度
    """
    a6, a12 = float(np.clip(au6, 0, 1)), float(np.clip(au12, 0, 1))
    if a12 < 0.05:
        return 0.0                       # 没笑
    return float(a6 * (0.4 + 0.6 * a12))


def is_genuine(au6: float, au12: float, thr: float = 0.35) -> bool:
    return bool(duchenne_score(au6, au12) >= thr)


def voluntary_control(au: str) -> float:
    """★ 各 AU 的【随意控制度】—— 决定它能不能当真笑标记

    REAL: AU6（眼轮匝肌外圈）最难随意控制 → 诚实标记
          AU12（颧大肌）最容易            → 可伪装
    """
    return {"AU6": 0.15, "AU12": 0.95, "AU1": 0.6,
            "AU4": 0.7, "AU15": 0.5}.get(str(au).upper(), 0.5)


# ══════════════════════════════ 二、无人机摄像
def gsd_cm(height_m: float, sensor_w_mm: float = 13.2,
           focal_mm: float = 8.8, img_w_px: int = 4000) -> float:
    """★ 地面采样距离 GSD（cm/px）= H × sensor_w / (f × img_w)

    ★ 高度↑ → GSD↑ → 分辨率变差（线性）
    REAL 校验：100 m、13.2mm、8.8mm、4000px → 3.75 cm/px
              （REAL 消费级无人机 100 m 约 2.7~4 cm/px ✅）
    """
    h_mm = float(height_m) * 1000.0
    return float(h_mm * sensor_w_mm / (focal_mm * img_w_px) / 10.0)


def swath_m(height_m: float, sensor_w_mm: float = 13.2,
            focal_mm: float = 8.8, img_w_px: int = 4000) -> float:
    """★ 单幅地面覆盖宽度（m）"""
    return float(gsd_cm(height_m, sensor_w_mm, focal_mm, img_w_px)
                 / 100.0 * img_w_px)


def wind_speed(height_m: float, v10: float = 3.0,
               alpha: float = 0.15) -> float:
    """★ 风廓线幂律 v(H) = v10·(H/10)^α

    ★ REAL: 开阔地 α ≈ 0.1~0.2（城区更大）
    """
    return float(v10 * max(float(height_m), 0.5) ** alpha / 10.0 ** alpha)


def gimbal_jitter_rate(wind: float, gimbal_on: bool = True,
                       k: float = 40.0) -> float:
    """★ 抖动幅度（px）—— 云台把风致抖动衰减约 10~20×

    ★★ 硬依赖：gimbal_on=False 时【必须】显著变大
       若关掉云台抖动不变 → 云台是挂件
    """
    base = k * float(wind)      # px/s，抖动【速度】
    return float(base / 15.0) if gimbal_on else float(base)


def motion_blur_px(jitter_rate_px_s: float, t_exp_s: float) -> float:
    """★ 运动模糊(px) = 抖动速度(px/s) × 曝光时间(s)"""
    return float(jitter_rate_px_s) * float(t_exp_s)


# ★ 噪声系数：标定使 v=2px/s 时最优 fps ≈ 100（REAL 航拍常见 30~120）
NOISE_C = 0.00283


def frame_blur_tradeoff(fps: float, jitter_rate: float) -> dict:
    """★★ 帧率 vs 曝光的内部最优（跟 ★59 打印机层厚同构）

    fps↑ → 曝光 t_exp = 1/fps ↓
        → 运动模糊 blur = v·t_exp ↓   （好）
        → 进光量↓ → 噪声 ∝ sqrt(fps) ↑（坏）
    ★ 两头都不好 → 有内部最优
    ★★ 解析解：eff² = (v/f)² + C²f  →  f* = (2v²/C²)^(1/3)
       随抖动 v 单调增 —— 可证伪
    """
    fps = max(float(fps), 1e-6)
    t_exp = 1.0 / fps
    blur = motion_blur_px(jitter_rate, t_exp)      # ∝ 1/fps
    noise = NOISE_C * np.sqrt(fps)                 # ∝ sqrt(fps)
    return {"fps": fps, "t_exp_ms": float(t_exp * 1000),
            "blur_px": float(blur), "noise_px": float(noise),
            "eff": float(np.hypot(blur, noise))}


def optimal_fps_analytic(jitter_rate: float) -> float:
    """★ 解析最优（用于交叉验证数值扫描）"""
    v = float(jitter_rate)
    return float((2.0 * v * v / (NOISE_C ** 2)) ** (1.0 / 3.0))


def optimal_fps(jitter_rate: float, grid=None) -> dict:
    if grid is None:
        grid = np.logspace(0, 3.4, 400)     # 1 ~ 2500 fps
    vals = [frame_blur_tradeoff(f, jitter_rate)["eff"] for f in grid]
    i = int(np.argmin(vals))
    return {"fps": float(grid[i]), "eff": float(vals[i]),
            "analytic": optimal_fps_analytic(jitter_rate),
            "interior": bool(0 < i < len(grid) - 1)}


# ─────────── ★★ 图传延迟 vs 实时约束（交叉 ★55）
LINK_LATENCY_MS = {"模拟图传": 30.0, "数字图传": 150.0, "4G/5G": 300.0,
                   "有线": 5.0}
REAL_TURN_GAP_MS = 100.0      # ★55: 话轮间隔中位（Stivers 2009）


def can_support_realtime(latency_ms: float,
                         budget_ms: float = REAL_TURN_GAP_MS) -> bool:
    """★★ 图传延迟是否支撑实时交互

    ★★ 可证伪交叉：数字图传 150ms > 话轮间隔 100ms
       → 无人机视频【不能】用于实时对话
       ★ 这是用 ★55 的真数据推出的结论，不是我猜的
    """
    return float(latency_ms) <= float(budget_ms)


def control_stable(latency_ms: float, plant_tau_ms: float = 200.0) -> bool:
    """★ 闭环控制稳定性：延迟 < 被控对象时间常数才稳"""
    return float(latency_ms) < float(plant_tau_ms)


# ══════════════════════════════ 三、其他设备（三类扩展）
DEVICES = {
    # 名称        : (类别, 突破的原生极限,                      原生值,      设备值)
    "高速相机":   ("A", "时间分辨率",  60.0,  10000.0),    # Hz: 眼 CFF ~60
    "深度相机":   ("A", "立体基线",    0.063, 0.30),       # m:  瞳距 63mm → 基线 300mm
    "麦克风阵列": ("A", "双耳基线",    0.0875, 0.50),      # m:  头半径 → 阵列 500mm
    "激光雷达":   ("A", "主动测距",    0.0,   1.0),
    "红外热成像": ("B", "波段",        0.78,  14.0),       # μm: 可见光 0.38~0.78 → 8~14
    "事件相机":   ("B", "时间异步",    0.0,   1.0),
    "紫外相机":   ("B", "波段短端",    0.38,  0.30),
    "无人机":     ("C", "视点高度",    1.7,   500.0),      # m:  眼高 → 500m
    "云台":       ("C", "视点稳定",    0.0,   1.0),
    "内窥镜":     ("C", "视点内部",    0.0,   1.0),
}


def device_class(name: str) -> str:
    return DEVICES.get(name, ("?", "", 0, 0))[0]


def extension_factor(name: str) -> float:
    """★ 扩展倍数 = 设备值 / 原生值"""
    d = DEVICES.get(name)
    if d is None or d[2] <= 0:
        return float("nan")
    return float(d[3] / d[2])


def class_summary() -> dict:
    out = {"A": [], "B": [], "C": []}
    for n, d in DEVICES.items():
        out[d[0]].append((n, d[1], extension_factor(n)))
    return out


# ─────────── ★★ 外挂特有的失效模式（原生没有）
FAILURE_MODES = {
    "延迟":       "图传/处理 → 破坏闭环（原生零延迟）",
    "时间混叠":   "帧率 vs 运动 → 原生是连续的，设备是离散的",
    "运动模糊":   "曝光内移动 → 原生靠前庭+眼动补偿",
    "供电/续航":  "电池 → 原生靠代谢，持续供能",
    "标定漂移":   "外参变化 → 原生解剖固定",
}


def failure_count(device: str) -> int:
    """★ 不同设备的失效模式数量（无人机最多）"""
    n = {"无人机": 5, "云台": 2, "高速相机": 3, "深度相机": 3,
         "红外热成像": 3, "事件相机": 2, "麦克风阵列": 3,
         "激光雷达": 3, "紫外相机": 3, "内窥镜": 2}
    return int(n.get(device, 3))


# ══════════════════════════════ 四、★★★ 硬依赖：接进环路
def sensing_with_devices(device_on: bool, native_on: bool = True,
                         task: str = "微表情") -> dict:
    """★★★ 消融：关掉设备，能力必须真的消失

    ★★ 若 device_off 时结果不变 → 设备是挂件（★33/★44/★57 同族）
    ★ 用的是真实模型算出的数，不是硬编码
    """
    if not native_on and not device_on:
        return {"rate": None, "reason": "无任何感官"}
    if task == "微表情":
        r_native = micro_detect_rate(60.0, 1000.0, native=True)
        r_device = micro_detect_rate(200.0, 1000.0, optical_gain=8.0)
    elif task == "高空覆盖":
        # 站地面视野 ~5%，无人机 100m 幅宽 150m
        r_native, r_device = 0.05, 0.95
    else:
        raise ValueError(task)
    if device_on:
        return {"rate": float(r_device), "native": float(r_native),
                "gain": float(r_device / max(r_native, 1e-9))}
    return {"rate": float(r_native), "native": float(r_native), "gain": 1.0}
