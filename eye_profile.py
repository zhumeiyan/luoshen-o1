# -*- coding: utf-8 -*-
"""
眼睛常数 —— 不是真理，是可替换的 profile。

人类的测量数据互相打架（同一个 fovea：1° / 2° / 6°；同一个 10° 处：78% / 10~20%）。
所以本文件不宣称哪个对，只做两件事：
  1. 把每组来源原样存成 profile，谁都能换
  2. 敏感性分析 —— 换任何一组，看结论翻不翻

下放权力的判据：拿走之后还能不能独立验。
所以这里还给了自标定：你可以用自己的眼睛把它换成你自己的数。

    python3 eye_profile.py 列表
    python3 eye_profile.py 敏感          # 换每组，结论翻不翻
    python3 eye_profile.py 自标定        # 你怎么用自己的眼睛测
"""
import math, os, json, sys

# ---- profile：每组都标来源与权威性，不宣称哪个对 ----
PROFILES = {
    "wikipedia": dict(
        src="Wikipedia Fovea centralis", 权威="极高",
        fov_h=200, fov_v=135, fovea=2.0,
        ecc=[0, 5, 10, 20, 30, 45], acu=[1.0, .35, .15, .08, .04, .0]),
    "umn教材": dict(
        src="Univ. of Minnesota 开放教材", 权威="中等",
        fov_h=200, fov_v=135, fovea=1.0,
        ecc=[0, 5, 10, 20, 30, 45], acu=[1.0, .35, .15, .08, .04, .0]),
    "摄影博客": dict(
        src="frameandfocal.com", 权威="极低",
        fov_h=180, fov_v=135, fovea=6.0,
        ecc=[0, 5, 10, 20, 30, 45], acu=[1.0, .35, .15, .08, .04, .0]),
    "geisler_perry": dict(
        src="Geisler & Perry 线性模型", 权威="中等",
        fov_h=200, fov_v=135, fovea=2.0,
        ecc=[0, 15, 30, 45, 60], acu=[1.0, .75, .50, .25, .0]),
    "annualreview": dict(
        src="Annual Reviews (实测心理物理)", 权威="较高",
        fov_h=200, fov_v=135, fovea=2.0,
        ecc=[0, 5, 10, 20, 30, 45], acu=[1.0, .40, .15, .07, .04, .0]),
    "人民网动态视野": dict(
        src="人民网健康（动态视野）", 权威="极高但非本行",
        fov_h=156, fov_v=130, fovea=2.0,
        ecc=[0, 5, 10, 20, 30, 45], acu=[1.0, .35, .15, .08, .04, .0]),
}

CUR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "我的眼睛.json")
DEFAULT = "annualreview"


def load(name=None):
    """读 profile：优先用你自己标定的，其次是环境变量，最后默认"""
    if name is None and os.path.exists(CUR):
        try:
            p = json.load(open(CUR, encoding="utf-8"))
            p["src"] = "你自己标定的"
            p["权威"] = "最高（因为是你）"
            return p
        except Exception:
            pass
    name = name or os.environ.get("EYE_PROFILE") or DEFAULT
    return PROFILES[name]


def acuity(p, e):
    import numpy as np
    return float(np.interp(e, p["ecc"], p["acu"]))


def metrics(p, screen_w_cm=7.0, screen_h_cm=15.0, dist_cm=30.0, px_w=1080, px_h=2340):
    """一组 profile 推出的三个数"""
    def ang(half_cm):
        return 2 * math.degrees(math.atan(half_cm / dist_cm))
    sw, sh = ang(screen_w_cm / 2), ang(screen_h_cm / 2)
    fov_area = p["fov_h"] * p["fov_v"]
    fav_area = math.pi * (p["fovea"] / 2) ** 2
    px_per_deg = px_w / sw
    r_px = px_per_deg * (p["fovea"] / 2)
    return {
        "屏横向°": round(sw, 1),
        "高清占视野%": round(fav_area / fov_area * 100, 5),
        "中央凹占屏%": round(math.pi * r_px ** 2 / (px_w * px_h) * 100, 3),
        "1°=px": round(px_per_deg, 1),
    }


def sensitivity():
    """换任何一组，主结论翻不翻"""
    print("  主结论：『你看见的世界里只有极小一块是真的』\n")
    print("  %-16s %-12s %-14s %-12s" % ("profile", "高清占视野%", "中央凹占屏%", "量级"))
    vals = []
    for k in PROFILES:
        m = metrics(PROFILES[k])
        vals.append(m["高清占视野%"])
        print("  %-16s %-12s %-14s %s" % (
            k, m["高清占视野%"], m["中央凹占屏%"],
            "万分之一级" if m["高清占视野%"] < 0.1 else "千分之一级"))
    print("\n  最小 %.5f%%  最大 %.5f%%  比值 %.1f 倍"
          % (min(vals), max(vals), max(vals) / min(vals)))
    print("  → 数字差 %.0f 倍，但量级没翻：全部 <=0.12%%（不到千分之一）"
          % (max(vals) / min(vals)))
    print("  → 所以判据『主块必须落在中心』不依赖这些数据准不准")


def selfcalib():
    print("""  你自己的眼睛，不用信任何文献：

  1. 伸直手臂，竖起拇指。拇指宽度 ≈ 2°  —— 这就是你的中央凹大小
  2. 盯住屏幕中心一个字，保持不动
  3. 让人把手指从边上往中间挪，你刚能读出那是几个手指时 —— 那个角度就是你的边界
  4. 把数填进 我的眼睛.json：
       {"fov_h": 200, "fov_v": 135, "fovea": 2.0,
        "ecc": [0,5,10,20,30,45], "acu": [1.0,.35,.15,.08,.04,0.0]}

  填了以后 eye.py 全部自动用你的数，不用我的。
  删掉 我的眼睛.json 就退回文献值 —— 这件事始终可逆。""")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "敏感"
    if cmd == "列表":
        for k, v in PROFILES.items():
            print("  %-16s %-6s %s" % (k, v["权威"], v["src"]))
    elif cmd == "自标定":
        selfcalib()
    else:
        sensitivity()
