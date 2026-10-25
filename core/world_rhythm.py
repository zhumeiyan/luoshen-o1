#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
世界层：按人类社会的真实节律给刺激（不是机械轮换、不是随机）
================================================================
用户原话：「场景轮换就按照人类社会的，天气啊那些东西那么按」

★ 判据核 #450：provenance 由"系统调用是否真的成功了"决定
    本沙盒实测（2026-10-24）：
      真实时钟 /proc、time.time()   ✅ REAL
      经纬度（用户位置 威海 37.51N 122.12E）  ✅ REAL
      wttr.in / open-meteo         ❌ 403 → 天气只能 SIMULATED，如实标

★ 所以本文件四真一假：
    ① 光       REAL   真太阳高度角（真时钟 + 真经纬度）
    ② 社会人群  REAL   真时段（通勤/工作/午休/夜）
    ③ 周节律    REAL   真星期（工作日出勤 / 周末松弛）
    ④ 季节      REAL   真日期（日照长度 + 温度带）
    ⑤ 天气      SIMULATED  拿不到，用带惯性的马尔可夫，如实标

★ 关键设计（这是跟"机械轮换 t%N"的本质区别）：
    机械轮换 = 单一频率、完美周期、可预测
    真实社会 = 【多个不同频率叠加】
        光    周期 24h
        人群  周期 24h（但形状不同）
        周    周期 168h
        季节  周期 8760h
        天气  无固定周期，有惯性 + 偶发突变
    它们一会儿同相、一会儿错相 —— 场景自然就换了，
    不需要谁去"排班"。

★ 通道映射也会缓慢漂移：
    真实世界里你注意的东西一直在缓慢改变。
    若 5 个模态固定覆盖固定通道 → 被覆盖的永远被推 = 新锁死。
    所以权重随季节缓慢漂移（真实世界的"兴趣迁移"）。
"""
from __future__ import annotations
import math, datetime, time

# 威海（用户位置）
LAT, LON = 37.51, 122.12

# 天气状态（带惯性：大概率维持，小概率切换）
WEATHER = {
    "晴":    (0.90, {"晴": 0.80, "多云": 0.15, "雨": 0.05}),
    "多云":  (0.55, {"多云": 0.60, "晴": 0.25, "雨": 0.15}),
    "雨":    (0.20, {"雨": 0.70, "多云": 0.25, "晴": 0.05}),
}
W_SUN = {"晴": 1.0, "多云": 0.55, "雨": 0.20}


class WorldRhythm:
    """按真实社会节律生成刺激向量。"""

    def __init__(self, N=8, minutes_per_tick=60.0,
                 t0=None, seed=7, lat=LAT, lon=LON, forage_ch=7, use_meal=True):
        self.N = int(N)
        self.mpt = float(minutes_per_tick)      # 一拍 = 多少真实分钟
        self.lat, self.lon = lat, lon
        # 起始真实时刻（默认现在）
        self.t0 = t0 if t0 is not None else datetime.datetime.now()
        self.rng = __import__("numpy").random.default_rng(seed)
        self.weather = "晴"
        self.forage_ch = int(forage_ch)
        self.use_meal = bool(use_meal)
        self.t = 0
        self.log = []

    # ------------------------------------------------------------------
    def now(self):
        return self.t0 + datetime.timedelta(minutes=self.mpt * self.t)

    def solar_altitude(self, dt):
        """真太阳高度角（简化 NOAA 公式）。返回 0~1（0=地平线下）。"""
        doy = dt.timetuple().tm_yday
        # 赤纬
        dec = 23.44 * math.sin(math.radians(360.0 / 365.0 * (doy - 81)))
        dec = math.radians(dec)
        lat = math.radians(self.lat)
        # 时角：dt 是【本地时间】(CST, 标准子午线 120E)
        #   真太阳时 = 本地时 + (经度 - 120)/15
        #   时角 = (真太阳时 - 12) * 15 度
        #   ★ 上一版错在这里：把本地时又减了 8 当成 UTC，
        #     结果威海正午(12:00)被算成 ha=-120° → 白天全黑（实测 10-25 白天恒 0）
        local_h = dt.hour + dt.minute / 60.0
        true_solar_h = local_h + (self.lon - 120.0) / 15.0
        ha = math.radians((true_solar_h - 12.0) * 15.0)
        sin_alt = (math.sin(lat) * math.sin(dec) +
                   math.cos(lat) * math.cos(dec) * math.cos(ha))
        return max(0.0, min(1.0, sin_alt * 1.6))     # 0~1

    def crowd(self, dt):
        """社会人群密度：通勤双峰 + 午休 + 深夜低谷。REAL（真时钟）。"""
        h = dt.hour + dt.minute / 60.0
        morning = math.exp(-((h - 8.0) ** 2) / 2.0)
        evening = math.exp(-((h - 18.0) ** 2) / 2.5)
        noon    = 0.55 * math.exp(-((h - 12.5) ** 2) / 1.5)
        base    = 0.15 if 7 <= h <= 22 else 0.03
        return max(0.0, min(1.0, base + 0.45 * morning + 0.45 * evening + noon))

    def week(self, dt):
        """周节律：工作日 1.0，周末松弛。REAL。"""
        wd = dt.weekday()          # 0=Mon
        return 1.0 if wd < 5 else 0.35

    def season(self, dt):
        """季节：日照长度 + 温度带。REAL（真日期）。"""
        doy = dt.timetuple().tm_yday
        # 日照长度（北半球夏至最长）
        daylen = 0.5 + 0.5 * math.cos(math.radians(360.0 / 365.0 * (doy - 172)))
        return max(0.0, min(1.0, daylen))

    def meal(self, dt):
        """饭点：人类社会真实的强脉冲（早/午/晚三餐）。REAL（真时钟）。

        ★ 为什么必须加这个：上一版只有弥散的天气/光/人群，
          实测存活 0/24 —— 注意力被带走了，但没去觅食 = 饿死。
          真实社会节律里本来就有饭点，是我漏了。
        """
        h = dt.hour + dt.minute / 60.0
        breakfast = math.exp(-((h - 7.5) ** 2) / 0.4)
        lunch     = math.exp(-((h - 12.0) ** 2) / 0.5)
        dinner    = math.exp(-((h - 18.5) ** 2) / 0.6)
        return max(0.0, min(1.0, max(breakfast, lunch, dinner)))

    def step_weather(self):
        """天气：带惯性马尔可夫 + 偶发突变。SIMULATED（拿不到真的）。"""
        _, trans = WEATHER[self.weather]
        ks = list(trans.keys()); ps = [trans[k] for k in ks]
        self.weather = self.rng.choice(ks, p=ps)

    # ------------------------------------------------------------------
    def modalities(self):
        """返回 5 个模态的强度（各自不同频率，自然错相）。"""
        dt = self.now()
        alt = self.solar_altitude(dt)
        sun = alt * W_SUN[self.weather]
        return dict(
            light=(sun, "REAL"),
            crowd=(self.crowd(dt) * self.week(dt), "REAL"),
            week=(self.week(dt), "REAL"),
            season=(self.season(dt), "REAL"),
            weather=(1.0 - W_SUN[self.weather], "SIMULATED"),  # 坏天气反而信号强
            meal=(self.meal(self.now()) * (1.0 if self.use_meal else 0.0), "REAL"),
        )

    def vector(self, amp=2.0, focused=False):
        """把模态映射到 N 个通道。

        ★ 两种映射，差别很大（实测出来的，不是设计的）：
          focused=False  高斯弥散 → 所有通道同时被推
                         → 摊薄 → 摄食通道拿不到足够绝对量 → 饿死
          focused=True   每个模态集中打【一个】主通道，主通道随季节缓慢漂移
                         → 同一时刻只有少数通道被推 = 真实的"注意力集中"
                         → 被推到的通道能拿到足够绝对量
        """
        m = self.modalities()
        names = list(m.keys())
        w = np.zeros(self.N)
        if focused:
            for i, nm in enumerate(names):
                v = m[nm][0]
                if v < 0.05:
                    continue
                drift = (self.season_val * 2.0 + self.t / 400.0) * math.pi
                center = (i / len(names)) * self.N + math.sin(drift + i) * 1.2
                c = int(round(center)) % self.N
                w[c] += v
            # 饭点脉冲单独加权：它是生存相关，不该被摊薄
            mv = m.get("meal", (0.0, ""))[0]
            if mv > 0.3:
                w[self.forage_ch] += mv * 2.0
        else:
            for i, nm in enumerate(names):
                v = m[nm][0]
                drift = (self.season_val * 2.0 + self.t / 400.0) * math.pi
                center = (i / len(names)) * self.N + math.sin(drift + i) * 1.2
                for c in range(self.N):
                    d = abs(c - center)
                    d = min(d, self.N - d)
                    w[c] += v * math.exp(-(d ** 2) / 1.8)
        w = w / (w.max() + 1e-9)
        return w * amp

    # ------------------------------------------------------------------
    def step(self, amp=2.0, focused=False):
        self.season_val = self.season(self.now())
        self.step_weather()
        v = self.vector(amp, focused=focused)
        rec = dict(t=self.t, when=self.now().strftime("%m-%d %H:%M"),
                   w=self.weather)
        for k, val in self.modalities().items():
            rec["m_" + k] = round(val[0], 4)
        self.log.append(rec)
        self.t += 1
        return v


import numpy as np   # noqa: E402  (放在末尾避免上面 __import__ 混乱)
