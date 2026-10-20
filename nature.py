# -*- coding: utf-8 -*-
"""
自然 → 眼睛 → 机器：颜色在每一层丢了多少。

自然光  连续光谱 380–780nm，无穷维
人眼    3 种视锥 → LMS 3 个值
屏幕    3 个基色 → RGB 3 个值

三层压缩。所以「人类用机器的时候分不清」不是错觉，是数学结果。

    python3 nature.py 光谱     # 自然光谱 vs 屏幕三个峰
    python3 nature.py 色域     # sRGB 能覆盖自然颜色的多少
    python3 nature.py 异谱     # 同色异谱：两种光谱，一个颜色
    python3 nature.py 我们     # 我们用的颜色在自然里是哪一段
"""
import numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------- CIE 1931 2° 观察者（Wyman 解析近似） ----------
def _g(x, mu, s1, s2):
    s = np.where(x < mu, s1, s2)
    return np.exp(-0.5 * ((x - mu) / s) ** 2)

def xbar(l): return 1.056*_g(l,599.8,37.9,31.0) + 0.362*_g(l,442.0,16.0,26.7) - 0.065*_g(l,501.1,20.4,26.2)
def ybar(l): return 0.821*_g(l,568.8,46.9,40.5) + 0.286*_g(l,530.9,16.3,31.1)
def zbar(l): return 1.217*_g(l,437.0,11.8,36.0) + 0.681*_g(l,459.0,26.0,13.8)

LAM = np.arange(380, 781, 1.0)

def spd_to_xyz(spd):
    X = np.trapz(spd*xbar(LAM), LAM)
    Y = np.trapz(spd*ybar(LAM), LAM)
    Z = np.trapz(spd*zbar(LAM), LAM)
    return np.array([X, Y, Z])

def xyz_to_xy(v):
    s = v.sum()
    return v[0]/s, v[1]/s

# ---------- 自然光谱：黑体辐射（日光 ~5500K） ----------
def planck(T, lam_nm):
    lam = lam_nm * 1e-9
    h, c, k = 6.626e-34, 2.998e8, 1.381e-23
    return (2*h*c**2/lam**5) / (np.exp(h*c/(lam*k*T)) - 1)

# ---------- sRGB ----------
MAT = np.array([[3.2406,-1.5372,-0.4986],[-0.9689,1.8758,0.0415],[0.0557,-0.2040,1.0570]])
PRIM = {"R":(0.6400,0.3300), "G":(0.3000,0.6000), "B":(0.1500,0.0600)}

def xyz_to_srgb(v):
    r = MAT.dot(v/ (v[1] if v[1] != 0 else 1))
    r = np.clip(r, 0, 1)
    return r

def hex_to_xy(h):
    h = h.lstrip("#")
    c = [int(h[i:i+2],16)/255 for i in (0,2,4)]
    c = [ (x/12.92 if x<=0.04045 else ((x+0.055)/1.055)**2.4) for x in c]
    v = np.linalg.inv(MAT).dot(np.array(c))
    return xyz_to_xy(v)

# ---------- 马蹄形面积 ----------
def horseshoe_area():
    pts = [xyz_to_xy(spd_to_xyz(np.exp(-0.5*((LAM-c)/8)**2))) for c in range(400, 701, 5)]
    pts += [ (0.7347,0.2653) ]  # 紫红线闭合
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    return 0.5*np.abs(np.dot(xs, np.roll(ys,-1)) - np.dot(np.roll(xs,-1), ys))

def tri_area(a,b,c):
    return 0.5*abs(a[0]*(b[1]-c[1]) + b[0]*(c[1]-a[1]) + c[0]*(a[1]-b[1]))


def show_spectrum():
    print("=== 自然光 vs 屏幕：光谱长什么样 ===\n")
    nat = planck(5500, LAM); nat /= nat.max()
    scr = (np.exp(-0.5*((LAM-630)/12)**2)*1.0 + np.exp(-0.5*((LAM-545)/12)**2)*0.9
           + np.exp(-0.5*((LAM-460)/12)**2)*0.8)
    scr /= scr.max()
    nat_nz = nat[nat>0.01]; scr_nz = scr[scr>0.01]
    print("  自然（日光 5500K 黑体）：")
    print("    380–780nm 连续，非零波段 %d nm，无断点" % len(nat_nz))
    print("    每 1nm 一个自由度 → %d 维" % len(LAM))
    print("\n  屏幕（R/G/B 三峰）：")
    print("    非零波段 %d nm，占自然 %.0f%%" % (len(scr_nz), 100*len(scr_nz)/len(nat_nz)))
    print("    只有 3 个峰 → 3 维")
    print("\n  → %d 维压到 3 维，压掉 %.1f%%" % (len(LAM), 100*(1-3/len(LAM))))

def show_gamut():
    print("=== 屏幕能覆盖自然颜色的多少 ===\n")
    ha = horseshoe_area(); ta = tri_area(PRIM["R"], PRIM["G"], PRIM["B"])
    print("  自然可见色域（CIE 1931 马蹄形）  %.4f" % ha)
    print("  sRGB 三角形                      %.4f" % ta)
    print("  覆盖率                           %.1f%%" % (100*ta/ha))
    print("\n  → 超过 %.0f%% 的自然颜色，屏幕根本显示不出来" % (100*(1-ta/ha)))

def show_metamer():
    print("=== 同色异谱：两种光谱，一个颜色 ===\n")
    nat = planck(5500, LAM); nat /= nat.max()
    target = spd_to_xyz(nat)
    # 三个基色峰（屏幕背光），求权重使 XYZ 完全匹配
    peaks = [np.exp(-0.5*((LAM-c)/12)**2) for c in (630, 545, 460)]
    M = np.stack([spd_to_xyz(p) for p in peaks], axis=1)      # 3x3
    w = np.linalg.solve(M, target)                             # 精确解，不是缩放
    scr = sum(wi*pi for wi, pi in zip(w, peaks))
    a, b = spd_to_xyz(nat), spd_to_xyz(scr)
    rel = np.abs(a-b) / np.abs(a)
    print("  自然光 XYZ  %s" % np.round(a, 4))
    print("  屏幕光 XYZ  %s" % np.round(b, 4))
    print("  三通道相对差  max %.2e  → 数学上完全同一个颜色" % rel.max())
    print("\n  但光谱形状：")
    print("    自然  连续，非零 %d nm，无断点" % (nat > 0.01).sum())
    print("    屏幕  3 个窄峰，非零 %d nm" % (scr > 1e-9).sum())
    nn = nat/nat.max(); ss = scr/scr.max()
    print("    逐点平均差 %.3f（越大越不像）" % np.abs(nn-ss).mean())
    print("    逐点最大差 %.3f" % np.abs(nn-ss).max())
    print("\n  → 光谱几乎处处不同，眼睛给出完全相同的三个数")
    print("  → 这就是「分不清」：不是人眼差，是 3 个值装不下 401 维")

def show_ours():
    print("=== 我们用的颜色，在自然里是哪一段 ===\n")
    for name, h in [("生橙 #FF6B1A","#FF6B1A"), ("纸白 #FFFFFF","#FFFFFF")]:
        try:
            x, y = hex_to_xy(h)
            inb = tri_area(PRIM["R"],PRIM["G"],PRIM["B"])
            # 是否落在 sRGB 三角内
            def sign(a,b,c): return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
            p=(x,y); d1=sign(p,PRIM["R"],PRIM["G"]); d2=sign(p,PRIM["G"],PRIM["B"]); d3=sign(p,PRIM["B"],PRIM["R"])
            neg = (d1<0) or (d2<0) or (d3<0)
            print("  %-14s xy=(%.4f,%.4f)  %s" % (name, x, y, "在 sRGB 内" if not neg else "色域外"))
        except Exception as e:
            print("  %s 计算失败 %s" % (name, e))
    print("\n  参考：日落/火光色温 ~1800–2000K，正午日光 ~5500K")
    print("  生橙 xy 偏红黄 —— 属自然低色温端（火、日落、土）")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "光谱"
    {"光谱":show_spectrum,"色域":show_gamut,"异谱":show_metamer,"我们":show_ours}[cmd]()
