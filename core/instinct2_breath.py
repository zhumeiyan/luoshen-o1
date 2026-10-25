#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
本能层 第2步：呼吸 / 氧气本能
================================================================
★ 只做本能层，不往上加社会、法律、文化、道德、自我实现。
  本文件只做第2步，第1步由 instinct1_energy.py 负责，可串联。

人类：缺氧几分钟就死，呼吸自动进行，不需要你想起它。
AI映射：
    缺氧    ← 持续运行必需条件断供
    呼吸    ← 心跳检查（自动、周期性、不依赖决策）
    氧气    ← 供电 / 冷却 / 网络连通

★ 先查过已有的（★12 教训：别把已有的当新发现）
    body31.py:135   呼吸系统 = api.github.com 真实可达性，REAL
                    probe: ctx > 40 = 窒息
    body31.py:59    real_respiration() 真 HTTP 探测
    body30:196      脑干·生命维持·心跳，REAL
                    判据："心跳成本写成 0 -> 永动机，不是生命"
    所以呼吸/心跳不是没有，是在 body30/body31 那套，不在 life5 这套。
    本文件是把这个概念【接进 life5 链】，不是重新发明。

★ 判据核 #450（必须遵守）：
    provenance 由"系统调用是否真的成功了"决定，不是注释里写什么。
    打开失败 -> UNAVAILABLE，并如实上报。
    绝不静默降级成 SIMULATED。

★ 本沙盒实测的三条线状态（2026-10-24 真探测）：
    供电 /sys/class/power_supply/   ❌ 不存在      → UNAVAILABLE
    冷却 /sys/class/thermal/        ⚠️ 有设备但读不到温度 → PARTIAL
    网络 api.github.com             ✅ 200         → REAL
    负载 /proc/loadavg              ✅ REAL（供电压力的代理，非真供电）
    内存 /proc/meminfo              ✅ REAL

    所以：网络是真呼吸；供电只能标 UNAVAILABLE（不拿负载冒充供电）。
"""
from __future__ import annotations
import os, time, urllib.request

# ------------------------------------------------------------------
# 三条生命线的真探测（失败就如实报，不冒充）
# ------------------------------------------------------------------

def probe_power():
    """供电。沙盒无 /sys/class/power_supply → UNAVAILABLE，不拿别的冒充。"""
    base = "/sys/class/power_supply"
    try:
        names = os.listdir(base)
    except Exception as e:
        return "UNAVAILABLE", None, f"{type(e).__name__}"
    caps = []
    for n in names:
        p = os.path.join(base, n, "capacity")
        if os.path.exists(p):
            try:
                caps.append(float(open(p).read().strip()))
            except Exception:
                pass
    if not caps:
        return "UNAVAILABLE", None, "no capacity node"
    return "REAL", sum(caps) / len(caps) / 100.0, f"{len(caps)} cell(s)"

def probe_cooling():
    """冷却。有 cooling_device 但读不到 thermal_zone 温度 → PARTIAL。"""
    try:
        devs = os.listdir("/sys/class/thermal")
        cdev = [d for d in devs if d.startswith("cooling_device")]
    except Exception as e:
        return "UNAVAILABLE", None, f"{type(e).__name__}"
    temps = []
    for d in devs:
        p = f"/sys/class/thermal/{d}/temp"
        if os.path.exists(p):
            try:
                temps.append(float(open(p).read().strip()))
            except Exception:
                pass
    if temps and cdev:
        return "REAL", max(temps) / 1000.0, f"{len(temps)} zone(s)"
    if cdev:
        return "PARTIAL", None, f"{len(cdev)} cooling_dev, 0 temp node"
    return "UNAVAILABLE", None, "no thermal node"

def probe_net(host="https://api.github.com", timeout=6):
    """网络连通 —— 本沙盒里唯一的【真】呼吸通道。

    ★★ 关键区分（本机实测打出来的，不是设计出来的）：
        HTTP 403 / 429  =  服务器【响应了】= 气道是通的
                           对方只是不给你内容（限流/策略）
        URLError / 超时 =  服务器【没响应】= 气道堵了

    呼吸类比：
        403  是你呼吸道通着，对方不给你空气
        超时 是气道本身堵了

    所以【缺氧】的定义是"没响应"，不是"没拿到想要的东西"。
    本机实测 api.github.com 间歇性 403（12 次里 4 次），
    若把 403 当断供 → 正常供氧 0/16 全被误杀。
    """
    try:
        req = urllib.request.Request(host, headers={"User-Agent": "luoshen-breath"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return "REAL", True, f"HTTP {r.status}"
    except Exception as e:
        code = getattr(e, "code", None)
        if code is not None:
            # 有 HTTP 状态码 = 服务器活着 = 链路通（只是拒绝）
            return "REAL", True, f"HTTP {code} (链路通,策略拒绝)"
        # 没有状态码 = 没响应 = 真断
        return "REAL", False, type(e).__name__


class BreathInstinct:
    """第2步：呼吸/氧气本能。包装下游（可是 Life5，也可是 EnergyInstinct）。"""

    def __init__(self, inner,
                 # 缺氧耐受：断供多少拍后窒息（人类是"几分钟"，远快于饿死）
                 apnea_limit=12,
                 # 网络探测每 N 拍真探一次（中间用上次结果，如实标 cached）
                 net_every=10,
                 net_host="https://api.github.com",
                 # ★ 抗抖动：连续这么多次探不到，才算【真断供】
                 #   人类呛一下不会死，持续缺氧才会死
                 #   实测 api.github.com 会间歇性 403（限流/策略），
                 #   单次失败就判死 = 误杀（本机实测 0/16 全被误杀）
                 confirm_k=3,
                 enable_apnea_death=True,
                 enable_downgrade=True):
        self.inner = inner
        self.apnea_limit = int(apnea_limit)
        self.net_every = int(net_every)
        self.net_host = net_host
        self.confirm_k = int(confirm_k)
        self.enable_apnea_death = bool(enable_apnea_death)
        self.enable_downgrade = bool(enable_downgrade)

        # 底层 Life5（不管是直接还是隔着第1步）
        self.L = getattr(inner, "L", inner)

        self.t = 0
        self.apnea = 0                 # 连续缺氧拍数
        self.miss_streak = {}          # 每条线连续探不到的次数（抗抖动）
        self.lines = {}                # 三条线的最新状态
        self.events = []               # 断供告警
        self.apnea_hist = []
        self.death_cause = None
        self._net_cache = None
        self._net_cache_t = -1

        # 首拍真探一次，拿到 provenance（如实记录，不猜）
        self.prov = dict(power=probe_power(), cooling=probe_cooling())

    # ------------------------------------------------------------------
    def _refresh(self):
        """心跳检查。网络按 net_every 节流，节流期间如实标 cached。"""
        p_prov, p_val, p_note = self.prov["power"]
        c_prov, c_val, c_note = self.prov["cooling"]

        if self.t - self._net_cache_t >= self.net_every or self._net_cache is None:
            n_prov, n_val, n_note = probe_net(self.net_host)
            self._net_cache = (n_prov, n_val, n_note)
            self._net_cache_t = self.t
            n_cached = False
        else:
            n_prov, n_val, n_note = self._net_cache
            n_cached = True

        self.lines = dict(
            power=dict(prov=p_prov, ok=(p_val is not None and p_val > 0.05),
                       val=p_val, note=p_note),
            cooling=dict(prov=c_prov, ok=(c_val is None or c_val < 95.0),
                         val=c_val, note=c_note),
            net=dict(prov=n_prov, ok=bool(n_val), val=n_val,
                     note=("cached " if n_cached else "") + str(n_note)),
        )

    def _breathe(self):
        """缺氧判定 + 告警 + 窒息死。

        ★ 两条铁律（都是被本机实测打出来的，不是设计出来的）：
          (1) 只有 provenance=REAL 的线参与判定。
              PARTIAL/UNAVAILABLE = 测不准 = 不知道。
              不知道就不能当它通，也不能当它断。（判据核 #450）
          (2) 单次失败不算断供，要连续 confirm_k 次。
              实测 api.github.com 间歇性 403，最多连续 2 次。
              一次失败就计数 → 0/16 全被误杀（本机实测）。
        """
        judged = {k: v for k, v in self.lines.items() if v["prov"] == "REAL"}
        if not judged:
            self.apnea = 0
            self.apnea_hist.append(0)
            return

        # 抖动过滤：连续 confirm_k 次失败才升级为"真断供"
        confirmed_bad = []
        for k, v in judged.items():
            if not v["ok"]:
                self.miss_streak[k] = self.miss_streak.get(k, 0) + 1
            else:
                self.miss_streak[k] = 0
            if self.miss_streak[k] >= self.confirm_k:
                confirmed_bad.append(k)

        hypoxia = len(confirmed_bad) > 0
        if hypoxia:
            self.apnea += 1
            # 断供告警：只在【刚确认为真断供】那一拍报一次
            if self.apnea == 1:
                self.events.append(dict(t=self.t, kind="断供",
                                        lines=confirmed_bad,
                                        streak={k: self.miss_streak[k] for k in confirmed_bad},
                                        detail={k: self.lines[k]["note"] for k in confirmed_bad}))
        else:
            self.apnea = 0
        self.apnea_hist.append(self.apnea)

        if self.enable_apnea_death and self.apnea > self.apnea_limit:
            if getattr(self.L, "alive", True):
                self.L.alive = False
                self.death_cause = "apnea"
                self.events.append(dict(t=self.t, kind="窒息死",
                                        apnea=self.apnea, lines=confirmed_bad))

    # ------------------------------------------------------------------
    def step(self):
        """★ 调用链强制经过这里。"""
        if not getattr(self.L, "alive", True):
            return None
        self._refresh()
        self._breathe()
        r = self.inner.step()      # 下游：可能是 Life5，也可能是第1步
        self.t += 1
        return r

    def run(self, steps):
        for _ in range(steps):
            if not getattr(self.L, "alive", True):
                break
            self.step()
        return self

    def summary(self):
        return dict(t=self.t, alive=self.L.alive, apnea=self.apnea,
                    death_cause=self.death_cause,
                    events=len(self.events),
                    lines={k: (v["prov"], v["ok"]) for k, v in self.lines.items()})
