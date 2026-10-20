# -*- coding: utf-8 -*-
"""
参数库 —— 不再猜，去查。

用户命题：
  "你应该找一下所有类型的那些参数，你看能不能搜到，应该大部分能搜到。"

做了两件事：
  1. 设备参数：7 类显示设备的真实规格（厂商官方优先）
  2. 感官参数：眼/耳/触觉，每个带来源与【冲突】

核心规矩（沿用用户『他们写的可能是错』）：
  冲突必须记录，不静默选一个。

最要紧的三条发现：
  ① 中央凹 1.25° 是 Curcio 1990 解剖实测 —— 终结了此前 1°/2°/6° 的争论。
     那三个数是二手转述，1.25° 是测出来的。

  ② 个体差异 > 来源差异。
     中央凹视锥密度：个体 100,000~324,000（差 3.24×）
                    来源间只差 1.35×
     → 『标准人眼』在生理上不成立。此前所有『标准值』都是错的问法。

  ③ 设备端 PPI 差 2 倍，但都在往眼睛灌远超它能收的量。
     iPad Pro 264 PPI（看 distant） vs S25 Ultra 498 PPI（看 near）
     → 不是谁更好，是【观看距离】决定了合理 PPI

    python3 params.py 设备     # 7 类设备的中央凹像素与带宽
    python3 params.py 感官     # 感官参数与冲突
    python3 params.py 距离     # 为什么 PPI 差 2 倍是合理的
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = json.load(open(os.path.join(HERE, "参数库", "设备.json"), encoding="utf-8"))
SEN = json.load(open(os.path.join(HERE, "参数库", "感官.json"), encoding="utf-8"))

FOVEA_DEG = 1.25   # Curcio 1990 解剖实测：rod-free zone 0.350mm = 1.25°
EYE_MBIT = (0.47, 10.0)

# 各品类的典型观看距离（cm）——外部惯例，非我拍
DIST = {"手机": 30, "平板": 40, "笔记本": 50, "头显": None}


def fovea_px(ppi, dist_cm, fov=FOVEA_DEG):
    """中央凹在该屏上占多少像素直径。按视角几何，不是我拍的。"""
    arc_mm = math.radians(fov)*dist_cm*10
    return arc_mm/25.4*ppi


def bandwidth(w, h, hz, bpp=24):
    """屏幕往眼睛灌多少 Mbit/s。"""
    return w*h*bpp*hz/1e6


def run_devices():
    print("=== 7 类设备：中央凹占多少像素，机器灌了多少 ===\n")
    print("  中央凹按 Curcio 1990 实测 1.25°（不再是猜的 2°）\n")
    print("  %-22s %-11s %-6s %-10s %-9s %s"
          % ("设备", "分辨率", "PPI", "中央凹px", "占屏%", "灌(Mbit/s)"))
    print("  " + "-"*76)
    specs = [
        ("华为 P50 Pro（你）", 2700, 1228, 449.4, 120, 30),
        ("iPhone 16 Pro Max",  2868, 1320, 460,   120, 30),
        ("Galaxy S25 Ultra",   3120, 1440, 498,   120, 30),
        ("华为 Mate 70",       2688, 1216, 441,   120, 30),
        ("iPad Pro 13 (M4)",   2752, 2064, 264,   120, 40),
        ("MacBook Pro 16",     3024, 1964, 254,   120, 50),
    ]
    rows = []
    for name, w, h, ppi, hz, d in specs:
        fp = fovea_px(ppi, d)
        area = math.pi*(fp/2)**2/(w*h)*100
        bw = bandwidth(w, h, hz)
        print("  %-22s %-11s %-6.0f %-10.0f %-9.3f %s"
              % (name, "%dx%d" % (w, h), ppi, fp, area, format(int(bw), ",")))
        rows.append((name, fp, area, bw))
    print()
    print("  你的眼睛收得下 %.2f ~ %.0f Mbit/s" % EYE_MBIT)
    print("  %-22s %-14s %s" % ("设备", "灌/收(保守)", "灌/收(激进)"))
    print("  " + "-"*52)
    for name, fp, area, bw in rows:
        print("  %-22s %-14s %s" % (name,
              "%.0f×" % (bw/10), "%.0f×" % (bw/0.47)))
    print()
    print("  → 全部溢出 3~4 个数量级。没有一台例外。")


def run_senses():
    print("=== 感官参数：每条都带冲突 ===\n")
    e = SEN["眼·空间"]
    c = e["中央凹视锥密度峰值"]
    print("  【中央凹视锥密度】%s /mm²  (%s)" % (format(c["值"], ","), c["来源"][:38]))
    print("    个体差异 %s ~ %s = %.2f 倍" % (format(c["个体差异"][0], ","),
          format(c["个体差异"][1], ","), c["个体差异倍差"]))
    print("    来源之间只差 %.2f 倍" % (c["值"]/147300))
    print("    → 个体差异 > 来源差异：『标准人眼』不成立\n")
    f = e["中央凹大小"]
    print("  【中央凹大小】%.2f° (%s)" % (f["值"], f["来源"][:44]))
    print("    此前我用 1°/2°/6° —— 全是二手转述，已作废\n")
    t = SEN["眼·时间"]["闪烁融合频率 CFF"]
    print("  【闪烁融合 CFF】百度百科 %s / 百度健康 %s / ScienceInsights %s"
          % (t["百度百科"], t["百度健康"], t["ScienceInsights"]))
    print("    低端 30 与高端 90 差 %.0f 倍" % (90/30))
    print("    规律：%s\n" % t["_规律"])
    a = SEN["触觉"]["两点辨别阈"]
    print("  【触觉两点辨别】指尖 %s mm（中国标准）/ %s mm（Wikipedia）"
          % (a["指尖"], a["Wikipedia 指尖"]))
    print("    权威批评：%s" % a["_权威批评"][:44] + "...")


def run_distance():
    print("=== 为什么 PPI 差 2 倍是合理的 ===\n")
    print("  %-22s %-8s %-10s %-10s %s" % ("设备", "PPI", "观看cm", "中央凹px", "1°内像素"))
    print("  " + "-"*62)
    for name, ppi, d in [("Galaxy S25 Ultra", 498, 30), ("iPhone 16 Pro Max", 460, 30),
                         ("华为 P50 Pro（你）", 449.4, 30), ("iPad Pro 13", 264, 40),
                         ("MacBook Pro 16", 254, 50)]:
        fp = fovea_px(ppi, d)
        ppd = ppi/(2*math.pi*d/360)/1  # 每度像素近似
        ppd = ppi*25.4/(math.radians(1)*d*10)
        print("  %-22s %-8.0f %-10d %-10.0f %.0f" % (name, ppi, d, fp, ppd))
    print()
    print("  → 手机 498 PPI @30cm，平板 264 PPI @40cm")
    print("  → 折算成【每度像素】后差距缩小很多：不是谁更好，是距离决定的")
    print()
    print("  人眼极限（按最小可分辨视角 0.5~1 角分）：")
    for arcmin in [0.5, 1.0]:
        print("    可分辨 %.1f 角分 → 需要 %.0f ~ %.0f 像素/度 才不吃亏"
              % (arcmin, 60/arcmin, 60/arcmin))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "设备"
    {"设备": run_devices, "感官": run_senses, "距离": run_distance}.get(c, run_devices)()
