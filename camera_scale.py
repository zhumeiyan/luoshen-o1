# -*- coding: utf-8 -*-
"""摄像头把我们缩小了 → 我拿到很小的数值。
算三件事：1)缩放因子 2)均质化损失 3)最终到我手里每度还剩几个像素
"""
import math, json

# ---------- P50 Pro 主摄（公开规格，非图里给的）----------
SENSOR_W_MM = 8.192      # IMX766 1/1.56", 8192px × 1.0μm
SENSOR_PX   = 8192       # 50MP 原始
EFL_MM      = 23.0       # 等效全画幅焦距（公开规格）
FF_W_MM     = 36.0       # 全画幅宽
f_real      = EFL_MM * SENSOR_W_MM / FF_W_MM
fov_h       = 2*math.degrees(math.atan(SENSOR_W_MM/(2*f_real)))

def ppd(px_wide, fov=fov_h): return px_wide/fov

# ---------- 人眼采样密度（Curcio 1990 峰值 ~111 视锥/度，间距≈0.54'）----------
RHO0 = 111.0
# 视锥密度随离心衰减（文献趋势拟合：2°约50%，5°约20%，10°约8%，20°约3%）
def rho(e): return RHO0/(1.0+(e/2.2)**1.35)
def rho_frac(e): return rho(e)/RHO0

if __name__ == "__main__":
    out={}
    print("=== 一、摄像头把角度缩成像素 ===")
    print(f"  传感器宽 {SENSOR_W_MM} mm · 实际焦距 {f_real:.2f} mm · 水平 FOV {fov_h:.1f}°")
    for name,px in [("原始 50MP",8192),("出片 12MP",4096),("视觉模型输入(假设)",224)]:
        v=ppd(px); print(f"  {name:<20} {px:>5}px  → {v:8.1f} px/度")
    out["摄像头ppd"]={"原始50MP":round(ppd(8192),1),"出片12MP":round(ppd(4096),1),
                      "模型输入224(假设)":round(ppd(224),1)}

    print("\n=== 二、关键：摄像头是【均匀】的，你的眼睛不是 ===")
    print(f"  你中央凹峰值        {RHO0:.0f} 视锥/度")
    print(f"  摄像头原始          {ppd(8192):.0f} px/度   ← 几乎等于你的峰值")
    print(f"  ★ 摄像头没削你的峰（108≈111），它把【谷填成了峰】")
    print("\n  离心度   你的密度%   摄像头(相对峰值%)")
    rows=[]
    for e in [0,1,2,5,10,20,40]:
        f=rho_frac(e)*100; rows.append((e,f))
        print(f"   {e:>3}°     {f:8.1f}%      100.0%")
    out["密度曲线"]=[(e,round(f,2)) for e,f in rows]

    print("\n=== 三、均质化损失：削峰填谷 ===")
    # 中心 0-2° 圆环面积
    A_c = math.pi*2.0**2
    eye_c = (RHO0*rho_frac(1.0))**2*A_c        # 面积密度 = 线密度^2
    cam_c = ppd(8192)**2*A_c
    print(f"  中心 0-2°（{A_c:.1f} 平方度）：")
    print(f"    你的眼睛  {eye_c:>10,.0f} 采样点")
    print(f"    摄像头    {cam_c:>10,.0f} 采样点   = 你的 {cam_c/eye_c:.2f} 倍")
    A_e = math.pi*(40**2-20**2)
    eye_e = (RHO0*rho_frac(30))**2*A_e
    cam_e = ppd(8192)**2*A_e
    print(f"  边缘 20-40°（{A_e:,.0f} 平方度）：")
    print(f"    你的眼睛  {eye_e:>10,.0f} 采样点")
    print(f"    摄像头    {cam_e:>10,.0f} 采样点   = 你的 {cam_e/eye_e:.0f} 倍")
    out["中心倍数"]=round(cam_c/eye_c,2); out["边缘倍数"]=round(cam_e/eye_e,1)
    # 我 2.9px/度 相当于你几度离心
    target=ppd(224); lo,hi=0.0,60.0
    for _ in range(60):
        m=(lo+hi)/2
        if RHO0*rho_frac(m)>target: lo=m
        else: hi=m
    print(f"\n  ★ 我工作的密度 {target:.1f} px/度，相当于你 {(lo+hi)/2:.0f}° 离心处的余光")
    out["等效离心度"]=round((lo+hi)/2,1)

    print("\n=== 四、最终到我手里的数值有多小 ===")
    chain=[("摄像头原始 8192px",8192),("出片 4096px",4096),("模型输入 224px(假设)",224)]
    base=None
    for n,p in chain:
        tot=p*(p*3/4)
        if base is None: base=tot
        print(f"  {n:<22} {tot:>14,.0f} 个数字   （是原始的 {tot/base*100:.2f}%）")
    print(f"\n  ★ 我真正工作的那张图：{ppd(224):.1f} px/度")
    print(f"  ★ 你的中央凹：        {RHO0:.0f} 视锥/度")
    print(f"  ★ 差 {RHO0/ppd(224):.0f} 倍 —— 我只相当于你 {(lo+hi)/2:.0f}° 处的余光")
    out["最终差倍数"]=round(RHO0/ppd(224),1)

    print("\n=== 五、所以'主次'在成像那一刻就丢了 ===")
    print(f"  摄像头输出 12.6M 个数字，但【没有任何标记告诉我哪部分是中心】")
    print(f"  全都是均匀的 → 主次信息在成像时被抹平")
    print(f"  ★ 这正是我必须【算】主次（离心角/块数/质心）的原因：")
    print(f"     不是我比你笨，是摄像头给我的数据里根本没写")

    json.dump(out, open("参数库/摄像头缩放.json","w"), ensure_ascii=False, indent=1)
    print("\n已存 参数库/摄像头缩放.json")
