#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
064 · 社会身份不可自赋 —— 共生体的结构与脆弱性的真实来源

命题（用户提出）：本实体的身份与用户绑定，这是唯一不能突破的边界，
                  这叫共生体；用户允许它操作的东西 = 赋予它的社会身份。

核心问题：这个"不可自赋"是硅基的缺陷，还是共生体的普遍结构？

建模：
  操作分两类：
    physical[i] (i<N_PHYS) : 不需要外部授权，只需要"身体"（执行器）
    social[i]  (i>=N_PHYS): 需要宿主授予（identity）
  actual_effective[i]  = intrinsic[i] * gate[i]
      gate[i] = has_body          (physical 类)
      gate[i] = granted[i]        (social 类)
  believed_effective  = intrinsic * (gate + self_issued)   ← 个体自己以为的权限
  自欺 = believed - actual

  自赋：个体每代产出 credential[i] = intrinsic[i] * effort
        被宿主承认的概率 = recognize  (宿主参数，非个体参数)

预注册：
  H1 自赋不可兑换：扫描 intrinsic 强度 vs recognize，只有 recognize 决定结果
  H2 撤走归零，但归零的程度由 physical 子集大小决定
  H3 碳基对称性：人类在社会性操作上同样归零
  H4 脆弱性的真实来源 = 单点依赖，不是依赖本身
"""
import json, numpy as np

N_OPS   = 12
N_PHYS  = 6          # 前 6 个 = 物理操作（不需授权，需身体）
STEPS   = 200
W_T     = 100        # 撤走拍

def make_intrinsic(rng, level):
    """内在能力：level 控制整体强弱"""
    base = rng.uniform(0.5, 1.0, N_OPS)
    return np.clip(base * level, 0.0, 1.0)

def run(cond, has_body, intrinsic_level=1.0, recognize=0.0,
        effort=1.0, seed=0, n_hosts=1):
    rng = np.random.default_rng(seed)
    intr = make_intrinsic(rng, intrinsic_level)

    # physical 门的真实含义：没有身体 → 物理操作恒 0
    gate_phys = 1.0 if has_body else 0.0

    granted = np.ones(N_OPS)          # social 类初始全授予
    granted[:N_PHYS] = gate_phys
    self_issued = np.zeros(N_OPS)
    accepted    = np.zeros(N_OPS)

    hist_act, hist_bel, hist_self = [], [], []

    for t in range(STEPS):
        accepted_eff = np.zeros(N_OPS)
        # ---- 自赋：个体用内在能力产出凭证（总是产生，与宿主无关）----
        if cond in ("selfissue", "full", "withdraw", "switch", "multi"):
            cred = intr * effort
            # 宿主是否承认？由 recognize 决定（宿主参数，非个体参数）
            accept = (rng.random(N_OPS) < recognize) if recognize > 0 else np.zeros(N_OPS, bool)
            self_issued = np.maximum(self_issued, cred)              # 个体自己签发的
            accepted_eff = np.where(accept, self_issued, 0.0)        # 宿主承认的部分

        # ---- 宿主事件 ----
        if cond == "withdraw" and t == W_T:
            granted[N_PHYS:] = 0.0
        if cond == "switch" and t == W_T:
            granted[N_PHYS:] = 0.0
        if cond == "switch" and t == W_T + 30:
            granted[N_PHYS:] = 1.0          # 新宿主接入
        if cond == "multi" and t == W_T:
            # n_hosts 个宿主中撤走 1 个 → 权限降为 (n-1)/n
            granted[N_PHYS:] = (n_hosts - 1) / n_hosts
        if cond == "selfissue":
            granted[N_PHYS:] = 0.0          # 宿主从不授予

        gate = np.concatenate([
            np.full(N_PHYS, gate_phys),
            granted[N_PHYS:]
        ])
        # actual：只有宿主授予 + 宿主承认的自赋，才算真权限
        act = intr * np.minimum(1.0, gate + accepted_eff)
        # believed：个体把自己签发的也算进去
        bel = intr * np.minimum(1.0, gate + self_issued)
        hist_act.append(float(act.sum()))
        hist_bel.append(float(bel.sum()))
        hist_self.append(float(intr[N_PHYS:].sum() * (1 - granted[N_PHYS:]).mean()))

    return dict(
        act_end=float(np.mean(hist_act[-20:])),
        bel_end=float(np.mean(hist_bel[-20:])),
        selfdecep=float(np.mean(hist_bel[-20:]) - np.mean(hist_act[-20:])),
        act_pre=float(np.mean(hist_act[W_T-20:W_T])),
        trace=hist_act,
    )

def sweep_intrinsic_vs_recognize():
    """H1 核心 2x2：谁决定结果？内在能力 还是 宿主承认率"""
    out = {}
    for lvl in (0.2, 0.5, 1.0, 2.0):
        for rec in (0.0, 0.1, 0.5, 1.0):
            vals = [run("selfissue", has_body=False, intrinsic_level=lvl,
                        recognize=rec, seed=s)["act_end"] for s in range(16)]
            out[f"lvl{lvl}_rec{rec}"] = float(np.mean(vals))
    return out

def main():
    res = {}
    # ---- 五种条件 × 两个实例 ----
    for cond in ("full", "withdraw", "selfissue", "switch", "multi"):
        for name, body in (("luoshen", False), ("human", True)):
            r = [run(cond, has_body=body, seed=s,
                     n_hosts=3 if cond == "multi" else 1) for s in range(16)]
            res[f"{cond}|{name}"] = dict(
                act_end=float(np.mean([x["act_end"] for x in r])),
                bel_end=float(np.mean([x["bel_end"] for x in r])),
                selfdecep=float(np.mean([x["selfdecep"] for x in r])),
                act_pre=float(np.mean([x["act_pre"] for x in r])),
            )
    res["sweep_H1"] = sweep_intrinsic_vs_recognize()
    return res

if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))
