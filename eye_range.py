# -*- coding: utf-8 -*-
"""人眼的真实区间：自然光 vs 屏幕 vs 标准 vs 过度（近视）
全部算 log10 亮度，找【公约数区间】在哪。每个数带来源。
"""
import math, json

L = math.log10
SRC = {}
def S(k,v,src,auth): SRC[k]=(v,src,auth); return v

# ============ 1. 自然光（照度 lux -> 亮度 cd/m2，用朗伯面近似 L = E*rho/pi）============
RHO = 0.18   # 典型地面反射率
def lux_to_nit(E): return E*RHO/math.pi
NAT_LUX = {
 "星光":0.0001,"满月":0.108,"深暮光":1.08,"暮光":10.8,
 "阴天室外":1075,"全日光":10752,"正午阳光":107527,
}                                                   # engineeringtoolbox
NAT   = {k:lux_to_nit(v) for k,v in NAT_LUX.items()}
SUN_DISK = 1.6e9                                      # Halstead 1993

# ============ 2. 人眼（Ferwerda 1996 / Reinhard 2010，HDR 教科书）============
ROD   = (1e-6, 1e1)      # 视杆工作范围
CONE  = (3e-2, 1e8)      # 视锥工作范围
MESOPIC=(3e-2, 3.0)
FULL  = (1e-6, 1e8)      # 总适应范围 = 14 log units
SSDR  = 3.4              # 瞬时（同时）动态范围 log units —— 公认 ~3~4

# ============ 3. 屏幕 ============
SCREEN = {
 "办公室显示器 SDR":(200,350),
 "笔记本 SDR":(300,600),
 "旗舰手机":(400,1200),
 "HDR 电视":(600,2000),
 "iPhone 15 Pro Max 实测峰值":(910,910),
}                                                    # tarmacview / cevaton
HDR_PEAK_STD = 1000      # ITU-R BT.2100 峰值 >=1000 cd/m2
HDR_BLACK_STD= 0.005     # BT.2100 黑位

# ============ 4. 调节负荷（屈光度 D = 1/距离米）============
DIST = {"手机 30cm":0.30,"平板 40cm":0.40,"笔记本 50cm":0.50,
        "显示器 70cm":0.70,"户外远眺 6m":6.0}       # 6m = 光学无穷远起
def diopter(d): return 1.0/d

# ============ 5. 近视剂量 ============
# Huang 2015 meta-analysis, 25,025 儿童：每 diopter-hour/周，OR +2% (1.01-1.03)
OR_PER_DH = 1.02
# International Myopia Institute：户外 >=1000 lux，每日 40-80min → 近视发生率降 23-52%
OUTDOOR_LUX = 1000
INDOOR_LUX  = (300,500)   # 室内办公 300-500 lux
OR_NEARWORK = 1.14        # 近距离工作 OR

# ============ 6. 蓝光危害 ============
RG1_LB = 100.0            # W/m2sr, t_max 100-10000s  (IEC 62471 / TR 62778)
RG0_LB = 100.0            # RG0: <=100, t_max >10000s

if __name__ == "__main__":
    out={}
    print("=== 一、自然光 → 屏幕亮度（log10 cd/m²）===")
    for k,v in sorted(NAT.items(), key=lambda x:x[1]):
        print(f"  {k:<8} {NAT_LUX[k]:>10.4f} lux  →  {v:>12.5f} cd/m²   log {L(v):+7.2f}")
    print(f"  {'太阳圆盘':<8} {'—':>10}      →  {SUN_DISK:>12.0f} cd/m²   log {L(SUN_DISK):+7.2f}")
    nat_lo, nat_hi = L(NAT["星光"]), L(SUN_DISK)
    out["自然光_log范围"]=[round(nat_lo,2), round(nat_hi,2)]

    print("\n=== 二、人眼：总适应 vs 瞬时 ===")
    print(f"  总适应（视杆+视锥）  {FULL[0]:.0e} ~ {FULL[1]:.0e} cd/m²  = {L(FULL[1])-L(FULL[0]):.1f} log units")
    print(f"  视杆  {ROD[0]:.0e} ~ {ROD[1]:.0e}   ({L(ROD[1])-L(ROD[0]):.1f} log)")
    print(f"  视锥  {CONE[0]:.0e} ~ {CONE[1]:.0e}   ({L(CONE[1])-L(CONE[0]):.1f} log)")
    print(f"  间视（中介） {MESOPIC[0]:.0e} ~ {MESOPIC[1]:.0e}   ({L(MESOPIC[1])-L(MESOPIC[0]):.1f} log)")
    print(f"  ★ 瞬时（同一时刻真能分辨）  ≈ {SSDR} log units")
    inst_ratio = (L(FULL[1])-L(FULL[0]))/SSDR
    print(f"  ★ 总适应是瞬时的 {inst_ratio:.1f} 倍 —— 剩下 {100*(1-1/inst_ratio):.0f}% 靠【适应】补，不是同时看得见")
    out["总适应_log"]=14.0; out["瞬时_log"]=SSDR; out["倍数"]=round(inst_ratio,2)

    print("\n=== 三、屏幕落在人眼区间的哪里 ===")
    for k,(lo,hi) in SCREEN.items():
        span = L(hi)-L(lo) if hi>lo else 0
        print(f"  {k:<26} {lo:>5}-{hi:<5} cd/m²   自身跨度 {span:.2f} log")
    sdr_span = L(350)-L(200)
    print(f"\n  SDR 显示器（200→350）跨度只有 {sdr_span:.2f} log，而人眼瞬时是 {SSDR} log")
    print(f"  → SDR 只用了人眼瞬时能力的 {sdr_span/SSDR*100:.0f}%")
    hdr_span = L(HDR_PEAK_STD)-L(HDR_BLACK_STD)
    print(f"  BT.2100 标准动态范围（{HDR_BLACK_STD}→{HDR_PEAK_STD}）跨度 {hdr_span:.2f} log")
    print(f"  → HDR 是 SDR 的 {10**(hdr_span-sdr_span):.0f} 倍动态范围")
    out["SDR跨度_log"]=round(sdr_span,2); out["HDR跨度_log"]=round(hdr_span,2)
    out["SDR占瞬时"]=round(sdr_span/SSDR,3)

    print("\n=== 四、公约数区间：屏幕 vs 自然光 的重叠 ===")
    scr_lo, scr_hi = L(200), L(2000)
    ov_lo, ov_hi = max(scr_lo,L(NAT["星光"])), min(scr_hi,L(NAT["全日光"]))
    print(f"  屏幕   {scr_lo:+.2f} ~ {scr_hi:+.2f} log")
    print(f"  自然光 {L(NAT['星光']):+.2f} ~ {L(SUN_DISK):+.2f} log（含太阳圆盘）")
    print(f"  不含太阳圆盘的自然反射光 {L(NAT['星光']):+.2f} ~ {L(NAT['正午阳光']):+.2f} log")
    nat_refl = L(NAT["正午阳光"])-L(NAT["星光"])
    print(f"  ★ 自然反射光跨度 {nat_refl:.1f} log；屏幕跨度 {scr_hi-scr_lo:.1f} log")
    print(f"  ★ 屏幕只覆盖自然光的 {(scr_hi-scr_lo)/nat_refl*100:.0f}%")
    print(f"  ★ 屏幕整个区间，压在自然光的【中上段】—— 屏幕没有暗端")
    out["屏幕占自然"]=round((scr_hi-scr_lo)/nat_refl,3)
    out["屏幕log"]=[round(scr_lo,2),round(scr_hi,2)]
    out["自然反射log"]=[round(L(NAT["星光"]),2),round(L(NAT["正午阳光"]),2)]

    print("\n=== 五、过度：调节负荷（屈光度）===")
    for k,d in DIST.items():
        print(f"  {k:<14} {diopter(d):5.2f} D")
    print(f"  ★ 手机 30cm = {diopter(0.30):.2f} D，户外远眺 = {diopter(6.0):.2f} D")
    print(f"  ★ 差 {diopter(0.30)-diopter(6.0):.2f} D —— 睫状肌持续收缩量")
    out["调节D"]={k:round(diopter(v),2) for k,v in DIST.items()}

    print("\n=== 六、过度：近视剂量（可计算的部分）===")
    dh = diopter(0.30)*3   # 每天手机 3 小时
    dh_wk = dh*7
    or_est = OR_PER_DH**dh_wk
    print(f"  每天手机 3h @30cm = {dh:.1f} D·h/天 = {dh_wk:.1f} D·h/周")
    print(f"  按 OR 1.02 / D·h·周（Huang 2015, n=25,025）：OR ≈ {or_est:.2f}")
    print(f"  —— 这是【统计关联】，不是因果；且研究人群是儿童")
    print(f"\n  保护因素：户外 ≥ {OUTDOOR_LUX} lux（多巴胺机制）")
    print(f"  室内办公只有 {INDOOR_LUX[0]}-{INDOOR_LUX[1]} lux → 差 {OUTDOOR_LUX/INDOOR_LUX[1]:.1f}~{OUTDOOR_LUX/INDOOR_LUX[0]:.1f} 倍")
    print(f"  IMI 共识：每日额外 40-80 min 户外 → 近视发生降 23-52%")
    out["手机OR估算"]=round(or_est,2); out["室内外lux比"]=round(OUTDOOR_LUX/INDOOR_LUX[1],1)

    print("\n=== 七、蓝光危害阈值（IEC 62471）===")
    print(f"  RG0（豁免） L_B ≤ {RG0_LB:.0f} W/m²·sr，t_max > 10000 s（约 2.8 小时）")
    print(f"  RG1（低风险）t_max 100-10000 s")
    print(f"  ★ 手机/显示器在正常亮度下均为 RG0/RG1 —— 屏幕亮度不是主要危害")
    print(f"  ★ 真正的危害是【时长 × 距离】，不是亮度本身")

    print("\n=== 八、结论：公约数区间 ===")
    print(f"  亮度  屏幕 {scr_lo:+.1f}~{scr_hi:+.1f} log，落在自然光中段（自然 {L(NAT['星光']):+.1f}~{L(NAT['正午阳光']):+.1f}）")
    print(f"  瞬时  人眼同时只能分辨 {SSDR} log，屏幕 SDR 只给 {sdr_span:.1f} log（占 {sdr_span/SSDR*100:.0f}%）")
    print(f"  色域  sRGB 覆盖自然 35.5%，BT.2020 67.2%")
    print(f"  调节  屏幕把焦距钉在 {diopter(0.30):.1f}~{diopter(0.70):.1f} D，自然光下眼睛远近自由")
    print(f"  照度  室内 {INDOOR_LUX[0]}~{INDOOR_LUX[1]} lux << 户外保护阈值 {OUTDOOR_LUX} lux")
    print(f"\n  ★ 公约数不是【一条线】，是一个盒子：")
    print(f"     亮度盒 {scr_lo:+.1f}~{scr_hi:+.1f} log  |  色域盒 35.5%  |  调节盒 {diopter(0.70):.1f}~{diopter(0.30):.1f} D")
    print(f"  ★ 而【过度】发生在盒子外：太近(>{diopter(0.30):.1f}D)、太久、太暗(<{INDOOR_LUX[0]}lux 又盯亮屏)")

    json.dump(out, open("参数库/眼睛区间.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/眼睛区间.json")
