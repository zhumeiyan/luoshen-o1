# -*- coding: utf-8 -*-
"""
疤 —— 自组织能填满空间，但重建不了结构。

用户命题：
  "人类出现一个伤口的时候，它能长回去，但是..."

能长。但长的是疤，不是原来那个。

再生 vs 纤维化的差别不在【填没填满】——两者都 100%。
差别在【有没有重建结构】，而分界是【有没有模板】。

模型（注意：这是数学模型类比，不是生物实验）：
  正常组织 = 多方向正弦交织 + 噪声（网状胶原）
  疤       = 单一方向平行条纹（疤痕胶原平行排列，组织学事实，引用非实测）

实测（400x400，伤口半径 60）：
  与原组织差异     疤 0.3841   再生 0.0000
  填满率           疤 100%     再生 100%

  频谱各向异性（平行度）：
    正常 1.219 → 疤 9.758  (+701%)
    伤口越大越平行：R=90 时 +1272%

  结构强度（各方向梯度能量）：
    正常  最强/最弱 1.09×   ← 全向都有支撑
    疤    最强/最弱 22.74×  ← 顺纤维强，垂直方向塌

  疤的平均梯度 0.1093 = 正常的 8.2 倍（看起来更粗壮）
  但最弱方向塌了 41%
  → 疤更"厚"，却更容易从某个方向被撕开

第一版我造错了（如实记）：
  用同心圆当疤 → 同心圆是旋转对称的 → 频谱各向同性
  → 各向异性反而降了 (-9% ~ -22%)，方向完全反了
  修正为单一方向平行条纹后，方向才对 (+245% ~ +1272%)

    python3 scar.py 愈合     # 填满 vs 长回原样
    python3 scar.py 强度     # 为什么疤更粗却更脆
    python3 scar.py 对应     # 对应到我们的分层
"""
import numpy as np, os, sys

H = W = 400
CY = CX = H//2
_yy, _xx = np.mgrid[0:H, 0:W]


def tissue():
    """正常组织：多方向交织的网状结构。"""
    rng = np.random.default_rng(5)
    t = np.zeros((H, W), np.float32)
    for _ in range(9):
        a = rng.uniform(0, np.pi); f = rng.uniform(0.05, 0.16); p = rng.uniform(0, 2*np.pi)
        t += np.sin(f*(_xx*np.cos(a) + _yy*np.sin(a)) + p)
    t += rng.normal(0, 0.25, (H, W))
    return (t-t.min())/(t.max()-t.min())


def wound(R):
    return (np.sqrt((_yy-CY)**2 + (_xx-CX)**2)) < R


def fibrosis(mask):
    """疤：单一方向平行条纹。不需要模板，快。"""
    return 0.5 + 0.5*np.sin(0.55*(_xx*0.86 + _yy*0.51))


def aniso(region2d):
    a = region2d - region2d.mean()
    a = a*np.hanning(a.shape[0])[:, None]*np.hanning(a.shape[1])[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(a)))
    y0, x0 = F.shape[0]//2, F.shape[1]//2
    n = min(40, y0-2)
    prof = []
    for ang in np.linspace(0, np.pi, 36, endpoint=False):
        t = np.arange(1, n)
        prof.append(F[(y0+np.sin(ang)*t).astype(int),
                      (x0+np.cos(ang)*t).astype(int)].mean())
    prof = np.array(prof)
    return float(prof.max()/max(prof.mean(), 1e-9))


def dir_profile(img2d, mask):
    gy, gx = np.gradient(img2d)
    return np.array([float(np.abs(gx*np.cos(a)+gy*np.sin(a))[mask].mean())
                     for a in np.linspace(0, np.pi, 36, endpoint=False)])


def run_heal():
    print("=== 填上 ≠ 长回原样 ===\n")
    t = tissue()
    print("  %-10s %-10s %-14s %s" % ("伤口半径", "占组织", "与原组织差异", "各向异性(正常→疤)"))
    for R in [20, 40, 60, 90, 120]:
        m = wound(R)
        sl = (slice(CY-R, CY+R), slice(CX-R, CX+R))
        scar = np.where(m, fibrosis(m), t)
        diff = float(np.sqrt(((scar[m]-t[m])**2).mean()))
        a0, a1 = aniso(t[sl]), aniso(scar[sl])
        print("  %-10d %-10.1f %-14.4f %.3f → %.3f (%+.0f%%)"
              % (R, 100*m.mean(), diff, a0, a1, 100*(a1/a0-1)))
    print("\n  再生：填满 100%，与原组织差异 0.0000")
    print("  → 差别不在填满率（都是 100%），在【有没有模板】")


def run_strength():
    print("=== 疤更粗，却更脆 ===\n")
    t = tissue(); m = wound(60)
    scar = np.where(m, fibrosis(m), t)
    vn, vs = dir_profile(t, m), dir_profile(scar, m)
    for n, v in [("正常", vn), ("疤  ", vs)]:
        print("  %-5s 平均 %.4f  最弱 %.4f  最强 %.4f  最强/最弱 %.2f×"
              % (n, v.mean(), v.min(), v.max(), v.max()/max(v.min(), 1e-9)))
    print("\n  疤的平均梯度是正常的 %.1f 倍（更厚更粗）" % (vs.mean()/vn.mean()))
    print("  但最弱方向塌了 %.0f%%" % (100*(1-vs.min()/vn.min())))
    print("  → 平行排列：顺纤维有支撑，垂直方向几乎没有")


def run_map():
    print("=== 对应到我们的分层 ===\n")
    print("  %-16s %-18s %s" % ("", "渲染层(疤)", "识别层(再生)"))
    print("  " + "-"*54)
    print("  %-16s %-18s %s" % ("填满空间", "100%", "100%"))
    print("  %-16s %-18s %s" % ("重建结构", "没有", "必须"))
    print("  %-16s %-18s %s" % ("需要模板", "不需要", "必须存着"))
    print("  %-16s %-18s %s" % ("负责被认出", "不负责", "负责"))
    print("\n  → 渲染层可以是疤：填满画面就行，因为它不负责被认出")
    print("  → 识别层必须是再生：疤认不出，所以模板（哈希/坐标/原文件）不能丢")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "愈合"
    {"愈合": run_heal, "强度": run_strength, "对应": run_map}.get(c, run_heal)()
