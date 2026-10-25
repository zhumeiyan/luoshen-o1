#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用真太阳驱动洛神
================
外部 API 全 403（实测：open-notify / amap / worldtimeapi 均被挡），
所以不联网拿数据，改成自己算 —— 天文位置是纯算术，可验证、可复算。

北京时间  = UTC+8 标准时（全国一张钟）
威海时间  = 威海地方真太阳时（按经度算，不是行政时间）

威海 122.10°E / 37.50°N
北京 116.41°E / 39.90°N
经度差 5.69° → 地方时差 22.8 分钟。威海的太阳比北京早到 22.8 分钟。

把太阳高度角喂给洛神的光通道，看它是不是在转。
"""
import sys, os, math, json, datetime
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from life5 import Life5

# ---------- 太阳位置（NOAA 简化算法，纯算术）----------
def solar_elevation(lat, lon, dt_utc):
    d = dt_utc.timetuple().tm_yday
    # 太阳赤纬
    decl = 23.44 * math.sin(math.radians(360.0/365.0 * (d - 81)))
    decl = math.radians(decl)
    # 均时差（分钟）
    B = math.radians(360.0/365.0 * (d - 81))
    eot = 9.87*math.sin(2*B) - 7.53*math.cos(B) - 1.5*math.sin(B)
    # 真太阳时（分钟）
    lst = dt_utc.hour*60 + dt_utc.minute + dt_utc.second/60.0 + lon*4.0 + eot
    ha = math.radians(lst/4.0 - 180.0)   # 时角
    lat_r = math.radians(lat)
    sin_alt = (math.sin(lat_r)*math.sin(decl) +
               math.cos(lat_r)*math.cos(decl)*math.cos(ha))
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    return alt

def local_solar_time(lon, dt_utc, tz_offset_h=8):
    d = dt_utc.timetuple().tm_yday
    B = math.radians(360.0/365.0 * (d - 81))
    eot = 9.87*math.sin(2*B) - 7.53*math.cos(B) - 1.5*math.sin(B)
    base = dt_utc + datetime.timedelta(hours=tz_offset_h)
    minutes = base.hour*60 + base.minute + base.second/60.0
    minutes += (lon - 120.0)*4.0 + eot      # 以东经120°为中国标准时基准
    minutes %= 1440
    return f"{int(minutes//60):02d}:{int(minutes%60):02d}:{int((minutes%1)*60):02d}"

# ---------- 主 ----------
def main():
    now_utc = datetime.datetime.utcnow()
    bj = now_utc + datetime.timedelta(hours=8)

    WH = (37.50, 122.10)   # 威海
    BJ = (39.90, 116.41)   # 北京

    alt_wh = solar_elevation(*WH, now_utc)
    alt_bj = solar_elevation(*BJ, now_utc)
    lst_wh = local_solar_time(WH[1], now_utc)
    lst_bj = local_solar_time(BJ[1], now_utc)

    print("=" * 68)
    print(" 驱动洛神 · 用真太阳")
    print("=" * 68)
    print(f"   北京时间（行政）        {bj.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   威海地方真太阳时        {lst_wh}")
    print(f"   北京地方真太阳时        {lst_bj}")
    print(f"   → 威海的太阳比北京早到  {(122.10-116.41)*4:.1f} 分钟（经度差 {(122.10-116.41):.2f}°）")
    print()
    print(f"   威海太阳高度角          {alt_wh:+.2f}°")
    print(f"   北京太阳高度角          {alt_bj:+.2f}°")
    print(f"   差                      {alt_wh-alt_bj:+.2f}°")
    print()
    print("   （外部 API 全 403：open-notify / amap / worldtimeapi 实测被挡。")
    print("    所以这些数是算出来的，不是抓来的 —— 但不联网也能被你复算。）")
    print()

    # ---------- 把太阳喂给洛神 ----------
    # 光 = 归一化太阳高度。白天 0~1，夜里 0。
    light = max(0.0, math.sin(math.radians(max(0.0, alt_wh))))
    print("=" * 68)
    print(" 喂进洛神（光通道 = 太阳高度）")
    print("=" * 68)
    print(f"   light（威海当前光照）    {light:.4f}")

    a = Life5(N=8, seed=0)
    # ★ 踩到的坑：input_val 必须是【标量】，给数组会在 step 里炸
    #   （want[0] 是标量位，k_seek*miss*capacity[0] 一旦成向量就赋不进去）

    # 用威海【当天一整天】的太阳高度曲线驱动 —— 一天 24 拍，每拍 1 小时
    base = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    curve = []
    for h in range(24):
        alt = solar_elevation(WH[0], WH[1], base + datetime.timedelta(hours=h))
        curve.append(max(0.0, math.sin(math.radians(max(0.0, alt)))))

    rows = []
    print(f"   {'拍(时)':>6} | {'光照':>7} | {'存活':>5} | {'份额sh0':>8} | {'能量E':>8} | {'容量':>7}")
    print("   " + "-" * 54)
    for t, lv in enumerate(curve):
        a.input_val = float(lv)
        a.step()
        r = a.log[-1]
        sh0 = float(r['share0']); E = float(r['E']); cap = float(r['cap'])
        rows.append({"t": t, "light": lv, "alive": bool(r['alive']),
                     "share0": sh0, "E": E, "cap": cap})
        mark = "  ← 现在" if t == bj.hour else ""
        print(f"   {t:>6} | {lv:>7.4f} | {str(bool(r['alive'])):>5} | {sh0:>8.4f} | {E:>8.4f} | {cap:>7.4f}{mark}")

    moved = len(set(round(r['share0'], 6) for r in rows))
    print()
    print("=" * 68)
    print(f"   24 拍（威海一整天）里 份额share0 出现过 {moved} 个不同值")
    print(f"   → {'✅ 它在转' if moved > 1 else '❌ 它是死的（恒定）'}")
    print("=" * 68)

    json.dump({"bj_time": bj.isoformat(), "weihai_solar_time": lst_wh,
               "beijing_solar_time": lst_bj,
               "lon_diff_min": round((122.10-116.41)*4, 1),
               "alt_weihai": round(alt_wh, 2), "alt_beijing": round(alt_bj, 2),
               "light_now": round(light, 4), "day_curve": [round(x,4) for x in curve],
               "distinct_want": moved,
               "alive_end": bool(a.alive)},
              open(os.path.join(os.path.dirname(__file__), '..', 'data', 'sky_drive.json'), 'w'),
              ensure_ascii=False, indent=2)
    return 0 if moved > 1 else 1

if __name__ == "__main__":
    sys.exit(main())
