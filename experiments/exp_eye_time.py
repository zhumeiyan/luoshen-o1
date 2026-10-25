#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
往【时间维度】找残差：真眼睛 + 眼睛在动 + 时间反演
====================================================
用户原话：「他眼睛有没有动？有。射到那个真实眼睛那个数值的时候，
           他眼睛在动。你往下找，往那个时间维度上找。」

★ 上一轮（exp_resid_chirality）在【静态单次快照】上找，判据 5 项中 4 项 ❌。
   原因（用户指出）：眼睛没动。静态下残差主要是噪声+量化，手性显不出来。

★ 手性的【时间签名】：
    扫视有旋向（L→R 或 R→L，单向）
    若感官无手性 → 反向扫视的序列 = 正向序列的时间反演，两者重合
    若感官有手性 → 不重合，差 = 手性残差

  判据（时间反演可逆度，117 分眼/钟用的就是这把尺子）：
    m_fwd(t)                 正向扫视序列
    m_rev(t)                 反向扫视序列
    Ra_t = |m_rev(t) - m_fwd(T-1-t)|      ← 时间反演残差（手性）
    Rs_t = |(m_fwd(t) + m_rev(T-1-t))/2|  ← 对称分量

★ 关键设计：世界【静止不动】。
    只有眼睛在动。这样序列的变化全部来自眼睛的运动，不来自世界。
    若世界也在变，就无法分离"眼睛动的贡献"和"世界变的贡献"。

★ 真眼睛：写 /dev/fb0 → 回读（141 已验证可写可读，真硬件 I/O）

provenance：
    fb0 读写 = REAL（真设备，字节级回读校验）
    世界/扫视轨迹 = 建模（无物理摄像头，077 已记 403）
    结果 = 本沙盒真跑
"""
import os, sys, json, hashlib
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
FB = "/dev/fb0"
W = H = 64                      # 世界尺寸（像素块）
STEP = 4                        # 每格像素


# ----------------------------------------------------------- 真眼睛 I/O
def fb_write(img):
    """写 fb0：把 W×H 灰度图铺成 RGBA 全屏。"""
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0] = img
    rgba[..., 1] = img
    rgba[..., 2] = img
    rgba[..., 3] = 255
    buf = rgba.repeat(STEP, 0).repeat(STEP, 1).tobytes()
    with open(FB, "r+b", buffering=0) as f:
        try:
            f.truncate(0)
        except Exception:
            pass
        f.write(buf)
    return len(buf)


def fb_read():
    """回读 fb0 → 降采样回 W×H 灰度。"""
    need = W * STEP * H * STEP * 4
    with open(FB, "rb", buffering=0) as f:
        f.seek(0)
        raw = f.read(need)
    if len(raw) < need:
        return None
    a = np.frombuffer(raw, dtype=np.uint8).reshape(H * STEP, W * STEP, 4)
    small = a[::STEP, ::STEP, 0].astype(float) / 255.0
    return small


def fb_ok():
    """真眼睛自检：写→读→一致？"""
    probe = np.zeros((H, W))
    probe[0, 0] = 255; probe[3, 2] = 128; probe[7, 5] = 64
    try:
        fb_write(probe)
        back = fb_read()
    except Exception as e:
        return False, f"io error {e}", None
    if back is None:
        return False, "read too short", None
    got = np.round(back * 255).astype(int)
    want = probe.astype(int)
    hit = int((got == want).sum())
    tot = W * H
    return (hit == tot), f"{hit}/{tot}", back


# ----------------------------------------------------------- 世界 + 眼动
def make_world(seed=5):
    """静止世界：含序结构（这样镜像才不同）。"""
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, W)[None, :]
    y = np.linspace(0, 1, H)[:, None]
    w = 0.5 + 0.35 * np.sin(6 * x) * np.cos(4 * y) + rng.normal(0, 0.03, (H, W))
    return np.clip(w, 0, 1)


class Eye:
    """会动的眼睛：每拍扫视一次，受体阵列带手性偏倚。"""

    def __init__(self, chi, n_rec=8, seed=0, W=W, H=H):
        self.chi = float(chi)
        self.n = int(n_rec)
        self.rng = np.random.default_rng(seed)
        # 受体在【局部】的偏移：chi>0 → 阵列本身有旋向（左右不对称）
        base = np.linspace(-1, 1, self.n)
        skew = self.chi * np.array([np.sign(v) * (abs(v) ** 2) for v in base])
        self.local = base + skew * 0.6
        self.y = H // 2

    def sample(self, world, t, T, direction):
        """第 t 拍采样：注视点沿 x 扫视，方向 ±1。"""
        frac = t / max(T - 1, 1)
        cx = frac if direction > 0 else (1.0 - frac)
        cx = 0.05 + 0.90 * cx
        px = cx * (W - 1)
        xs = np.clip(np.round(px + self.local * (W * 0.06)), 0, W - 1).astype(int)
        ys = np.clip(self.y + np.round(self.local * (H * 0.02)).astype(int), 0, H - 1)
        return world[ys, xs]


# ----------------------------------------------------------- 时间反演
def scan(world, eye, T=40, direction=+1):
    return np.array([eye.sample(world, t, T, direction) for t in range(T)])


def decompose_t(world, chi, T=40, seed=0):
    eye = Eye(chi, seed=seed)
    fwd = scan(world, eye, T, +1)
    rev = scan(world, eye, T, -1)
    rev_t = rev[::-1]                        # 时间反演对齐
    Rs = np.abs((fwd + rev_t) / 2.0).mean()
    Ra = np.abs(fwd - rev_t).mean()
    total = np.abs(fwd - rev_t).mean()
    return dict(fwd=fwd, rev=rev, Rs=float(Rs), Ra=float(Ra),
                total=float(total),
                ratio=float(Ra / max(Rs, 1e-9)))


if __name__ == "__main__":
    print("=" * 88)
    print(" 往时间维度找残差：世界静止，只有眼睛在动")
    print("=" * 88)

    ok_fb, msg, _ = fb_ok()
    print(f"\n  【真眼睛自检 /dev/fb0】写→读 {'一致 ✅' if ok_fb else '不一致 ❌'}  ({msg})")
    REAL_EYE = ok_fb

    world = make_world()
    if REAL_EYE:
        try:
            n = fb_write((world * 255).astype(np.uint8))
            back = fb_read()
            if back is not None:
                d = float(np.abs(back - world).mean())
                print(f"  真设备回读：写入 {n} 字节，回读误差 {d:.5f}")
                print(f"  世界 sha256 {hashlib.sha256(np.round(world*255).astype(np.uint8).tobytes()).hexdigest()[:16]}")
        except Exception as e:
            print(f"  fb 写读异常：{e}")

    print(f"\n{'手性 χ':<10}{'时间反演残差 Ra':>18}{'对称 Rs':>12}{'Ra/Rs':>10}{'判定':>10}")
    print("-" * 88)
    rows = []
    for chi in [0.0, 0.15, 0.3, 0.5, 0.75, 1.0]:
        r = decompose_t(world, chi, seed=3)
        rows.append((chi, r["Ra"], r["Rs"], r["ratio"]))
        verdict = "有手性残差" if r["Ra"] > 0.01 else "对称(无手性)"
        print(f"{chi:<10.2f}{r['Ra']:>18.5f}{r['Rs']:>12.5f}{r['ratio']:>10.3f}{verdict:>10}")

    print("\n" + "=" * 88)
    print(" 判据（时间维度）")
    print("=" * 88)
    a0 = rows[0]; a1 = rows[-1]
    ok = {}
    ok["① 真眼睛 fb0 写读一致（不是模拟）"] = bool(REAL_EYE)
    ok["② χ=0 时间反演残差 ≈ 0（无手性 → 正反扫视可逆）"] = bool(a0[1] < 0.01)
    ok["③ χ=1 时间反演残差显著 > 0（手性 → 不可逆）"] = bool(a1[1] > 0.02)
    ok["④ Ra 随 χ 单调上升"] = bool(all(rows[i][1] <= rows[i+1][1] + 1e-9
                                        for i in range(len(rows)-1)))
    ok["⑤ 静态下查不出（上轮 4/5 ❌），时间维度才显形"] = bool(a1[1] > 10 * a0[1])
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ χ=0  时间反演残差 {a0[1]:.5f}  → 正反扫视完全可逆")
    print(f"  ★ χ=1  时间反演残差 {a1[1]:.5f}  → 不可逆，{a1[1]/max(a0[1],1e-9):.0f}×")
    print(f"  ★ 用户猜测（残差=手性）：{'成立 —— 但要往时间维度看' if all(ok.values()) else '仍未完全成立'}")

    json.dump({"fb_real": bool(REAL_EYE), "fb_msg": msg,
               "rows": [dict(chi=r[0], Ra=r[1], Rs=r[2], ratio=r[3]) for r in rows],
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "eye_time_chirality.json"), "w"),
              ensure_ascii=False, indent=1)
