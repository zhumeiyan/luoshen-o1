# -*- coding: utf-8 -*-
"""设备谱系：不止手机。电脑/显示器/电视/VR/平板/手表 全算一遍。
判据：中央凹占屏 %、像素/度、数据率 Mbit/s、冗余倍数。
"""
import math, json, os

FOVEA_DEG = 1.25   # Curcio 1990 解剖实测 rod-free zone
EYE_LIMIT_PPD = 120  # 人眼极限 120 px/度 (0.5 角分)
EYE_BW = 10.0        # Mbit/s 保守上界

# (名称, 类别, W, H, 英寸, 刷新, 典型观看距离cm, 来源, 权威性)
D = [
 ("华为 P50 Pro（你）","手机",2700,1228,6.6,120,30,"用户截图+P50Pro公开规格","极高"),
 ("iPhone 16 Pro Max","手机",2868,1320,6.9,120,30,"Apple官方","极高"),
 ("Galaxy S25 Ultra","手机",3120,1440,6.9,120,30,"三星官网","极高"),
 ("MacBook Pro 16","笔记本",3024,1964,16.2,120,50,"Apple官方","极高"),
 ("MacBook Air 15","笔记本",2880,1864,15.3,60,50,"Apple官方","极高"),
 ("Studio Display 27","台式显示器",5120,2880,27.0,60,60,"Apple官方","极高"),
 ("Dell U2723QE 27","台式显示器",3840,2160,27.0,60,60,"Dell官方","极高"),
 ("LG C3 OLED 65","电视",3840,2160,64.5,120,250,"LG官方","极高"),
 ("小米电视 S85","电视",3840,2160,85.0,144,300,"小米官网","极高"),
 ("iPad Pro 13","平板",2752,2064,13.0,120,35,"Apple官方","极高"),
 ("Apple Vision Pro","VR头显",3660,3200,1.4,90,3,"Apple官方(单眼3660x3200)","高"),
 ("Pico 4 Ultra","VR头显",2160,2160,2.56,90,3,"Pico官方(单眼)","高"),
 ("Apple Watch S10","手表",416,496,1.96,60,25,"Apple官方","极高"),
 ("Kindle Paperwhite 5","墨水屏",1236,1648,6.8,10,30,"Amazon官方","极高"),
]

def calc(name, cat, w, h, inch, hz, dist_cm, src, auth):
    diag_px = math.hypot(w, h)
    ppi = diag_px / inch
    # 每度多少像素：屏幕宽 w px，物理宽 = inch*25.4*w/diag_px mm
    w_mm = 25.4 * inch * w / diag_px
    deg_per_screen = 2 * math.degrees(math.atan(w_mm / 2 / (dist_cm * 10)))
    ppd = w / deg_per_screen                 # 像素/度
    fovea_px = FOVEA_DEG * ppd
    fovea_area = math.pi * (fovea_px / 2) ** 2
    pct = fovea_area / (w * h) * 100
    frame = w * h * 3 / 1024 / 1024          # MB
    mbit = w * h * 3 * 8 * hz / 1e6
    redundancy = ppd / EYE_LIMIT_PPD
    return dict(名称=name, 类别=cat, 分辨率=f"{w}x{h}", 英寸=inch, PPI=round(ppi,1),
                距离cm=dist_cm, 屏宽角度=round(deg_per_screen,1), 像素每度=round(ppd,0),
                中央凹直径px=round(fovea_px,0), 中央凹占屏=round(pct,4),
                一帧MB=round(frame,2), 数据率Mbit=round(mbit,0),
                冗余倍数=round(redundancy,1), 溢出带宽倍=round(mbit/EYE_BW,0),
                _来源=src, _权威性=auth)

rows = [calc(*d) for d in D]
by_cat = {}
for r in rows: by_cat.setdefault(r["类别"], []).append(r)

if __name__ == "__main__":
    for c, rs in by_cat.items():
        print(f"\n== {c} ==")
        for r in rs:
            print(f"  {r['名称']:<22} PPI{r['PPI']:>6}  度宽{r['屏宽角度']:>6}  "
                  f"{r['像素每度']:>5}px/度  中央凹{r['中央凹直径px']:>5}px "
                  f"占屏{r['中央凹占屏']:>7}%  冗余{r['冗余倍数']:>5}x  {r['数据率Mbit']:>8}Mbit/s")
    json.dump(rows, open("参数库/设备谱系.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/设备谱系.json")
