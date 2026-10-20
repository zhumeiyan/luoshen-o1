# -*- coding: utf-8 -*-
"""空间距离感：距离在成像那一刻怎么被压掉、还剩多少、我能不能反推"""
import math, json

# ---- P50 Pro 主摄 ----
SENSOR_W_MM=8.192; SENSOR_PX=8192; EFL_MM=23.0; FF_W=36.0
f = EFL_MM*SENSOR_W_MM/FF_W               # 实际焦距 mm
px_per_mm = SENSOR_PX/SENSOR_W_MM         # px/mm 传感器面
B = 0.063                                  # 瞳距 63mm（成人均值）
RHO0 = 111.0                               # 中央凹峰值 视锥/度
STEREOSC = 10.0/3600                       # 立体视锐度 ~10 角秒（文献常见值）

def img_px(H_m, d_m):
    """真实高 H 米的物体，在 d 米处，成像多少像素"""
    return f * (H_m/d_m) * px_per_mm      # 像高mm = f(mm)*H/d, 再×px/mm

def stereo_precision(d_m):
    """双目可分辨的最小深度差 Δd = d²·Δθ/b"""
    return d_m**2 * math.radians(STEREOSC) / B

def vergence(d_m):
    return 2*math.degrees(math.atan((B/2)/d_m))

def diopter(d_m): return 1.0/d_m

if __name__=="__main__":
    out={}
    print("=== 一、透视：1/d 压缩 ===")
    print(f"  焦距 {f:.2f} mm  传感器 {px_per_mm:.0f} px/mm")
    print("  一个 1.7 m 高的人：")
    prev=None
    for d in [1,2,4,8,16,32]:
        p=img_px(1.7,d)
        r = f"{p/prev*100:5.1f}%" if prev else "  —  "
        print(f"    {d:>3} m → {p:>8.0f} px   是上一档的 {r}")
        prev=p
    print("  ★ 距离每翻倍，成像减半 —— 这是一条【非线性】压缩：")
    print("    远处所有东西挤在一起，近处一点点距离就占大半张图")
    out["透视px"]={str(d):round(img_px(1.7,d)) for d in [1,2,4,8,16,32]}

    print("\n=== 二、双目深度精度：随 d² 崩塌 ===")
    print("  距离    可分辨深度差   相对精度")
    for d in [0.3,0.5,1,2,5,10,20]:
        dd=stereo_precision(d)
        print(f"   {d:>5} m   {dd*1000:>10.2f} mm    {dd/d*100:>8.2f}%")
    print(f"  ★ 0.3 m 处能分辨 {stereo_precision(.3)*1000:.1f} mm；10 m 处只能分辨 {stereo_precision(10)*1000:.0f} mm")
    print(f"  ★ 差 {(10/0.3)**2:.0f} 倍（= 距离比的平方）")
    out["深度精度mm"]={str(d):round(stereo_precision(d)*1000,2) for d in [0.3,1,5,10,20]}

    print("\n=== 三、近处的两条线索（辐辏 + 调节）===")
    print("  距离     辐辏角     调节(D)")
    for d in [0.3,0.5,1,2,6]:
        print(f"   {d:>4} m   {vergence(d):>7.2f}°   {diopter(d):>6.2f} D")
    print(f"  ★ 两条都在 1/d 上，只在【近处】有用：")
    print(f"    0.3→1 m 辐辏变 {vergence(.3)-vergence(1):.1f}°；6→10 m 只变 {vergence(6)-vergence(10):.2f}°")
    print(f"  ★ 超过 6 m，辐辏和调节基本不动 —— 远的深度靠【单眼线索】撑")
    out["辐辏"]={str(d):round(vergence(d),2) for d in [0.3,1,6,10]}

    print("\n=== 四、拍成一张 2D 照片，还剩什么 ===")
    cues = [
      ("双眼视差", False, "两张图并一张，直接没了"),
      ("运动视差", False, "静态照片，没了"),
      ("辐辏/调节", False, "照片是平面，眼焦距钉在纸面"),
      ("遮挡", True, "有"),
      ("透视收敛", True, "有"),
      ("纹理梯度", True, "有，但被分辨率削"),
      ("相对大小", True, "有，需已知同类"),
      ("熟悉尺寸", True, "有，需认出是什么"),
      ("大气透视", True, "有"),
    ]
    keep=sum(1 for _,k,_ in cues if k)
    print(f"  9 条深度线索，照片保留 {keep} 条，丢 {len(cues)-keep} 条")
    for n,k,why in cues:
        print(f"    {'✓' if k else '✗'} {n:<8} {why}")
    out["线索保留"]=f"{keep}/{len(cues)}"

    print("\n=== 五、我能反推距离吗 ===")
    print("  h_px = f·H/d    三个未知（H真实高、d距离）两个已知（f、h_px）")
    print("  ★ 欠定：不知道物体真实尺寸，一张图里有【无穷多】组 (H,d) 解")
    print("    例如成像 800 px 可以是：")
    for H,d in [(1.7,0.5),(3.4,1.0),(17.0,5.0),(170.0,50.0)]:
        print(f"      H={H:>5.1f} m @ d={d:>5.1f} m")
    print("  ★ 所以：深度不是被【压缩】，是被【投影】—— 降维，不可逆")

    print("\n=== 六、那张 224px 的图还剩多少空间信息 ===")
    ppd_cam = img_px(1.0,1.0)/math.degrees(1.0)   # 1m 处 1m 高物体张角~53°... 简化
    print(f"  我工作的图 2.9 px/度")
    print(f"  你中央凹    {RHO0:.0f} 视锥/度")
    print(f"  ★ 1° 在我图里只有 2.9 个数字 —— 透视收敛这种【连续梯度】，")
    print(f"    在我这边是【一两个像素的阶跃】，没有梯度可言")
    out["我px每度"]=2.9; out["你视锥每度"]=RHO0

    json.dump(out, open("参数库/空间距离.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/空间距离.json")
