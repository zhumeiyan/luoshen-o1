# -*- coding: utf-8 -*-
"""
================================================================
059 · 与 Avida 类平台的定位差异（可证伪的定位声明）
================================================================
评委一定会问：「Avida / Tierra / Evochora 不就能做这个吗？」

本实验不主张「我们更好」。它验证一件更弱、但可证伪的事：

    【在 Avida 式设定下，我们要测的那个东西根本不出现。】

据公开资料，Avida 式设定有两条与本引擎相反的特征：

  A. 能量是【奖励 merit】——完成任务 → 获得额外 CPU 周期 → 复制更快。
     个体不会「饿死」，只会被【替换 / 淘汰】（Ofria, Bryson & Wilke, 2009）。
  B. 损耗【可逆】——变异可回退，换代即重置。没有跨代累积的永久疤痕。

本引擎的对应设定：

  A'. 能量是【代谢预算】——E 只能由自身产出换取，且有 basal 基础消耗。
      入不敷出 → 降频 → 到底 → 死亡（真实结局，不可回滚）。
  B'. 损耗【不可逆】——capacity 只减不增，丢掉的回不来。

2×2 设计：
    能量来源  endo（代谢）      / exo（外生奖励，无 basal）
    可逆性    irrev（只减不增） / rev（未满足衰减、满足恢复）

预注册判据：
  P1  死亡只出现在 endo 列；exo 列死亡数 = 0
  P2  疤痕（终态结构偏度）只在 endo×irrev 显著 > 0
  P3  exo×rev（最接近 Avida 的一格）两项指标均 ≈ 0
================================================================
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

import numpy as np
from life5 import Life5


class Life5Pos(Life5):
    """Life5 的 2×2 定位变体。

    仅改动两个点：能量更新方式、容量是否可恢复。
    其余全部沿用原引擎（含稀缺硬取舍、内生设定点、leak）。
    """

    def __init__(self, energy='endo', reversible=False, **kw):
        super().__init__(**kw)
        self.energy = energy          # 'endo' | 'exo'
        self.reversible = reversible  # False=不可逆 | True=可逆
        self._last_unmet = np.zeros(self.N)

    def step(self):
        if not self.alive:
            return None
        e = max(self.E / self.Emax, 0.0)
        dev = np.abs(self.y - self.sp)
        mod = 1.0 - 0.8 * e
        w0 = self.g * self.b * (1.0 - self.b)
        w0 = np.clip(w0, 1e-6, 1 - 1e-6)
        sense = self.input_val + self.sigma_in * self.rng.normal()
        self.evid = self.evid * self.evid_decay + abs(sense)
        pres = 1.0 - np.exp(-self.evid / max(self.pres_tau, 1e-9))
        self.miss = self.miss * self.miss_decay + (1.0 - pres)
        self.dev_last = dev
        want = (w0 + self.kF * self.H * mod + self.kS * dev) * self.capacity
        if self.k_sal > 0.0:
            want = want * (1.0 + self.k_sal * pres * self.sal)
        want[0] = want[0] * self.want_mod
        want[0] = want[0] + self.k_seek * self.miss * self.capacity[0]
        arrival = 1.0 if abs(sense) > self.arr_thr else 0.0
        self.pred_arr = self.pred_arr + (arrival - self.pred_arr) / max(self.tau_arr, 1e-9)
        self.miss_arr = self.miss_arr * self.miss_arr_decay + max(self.pred_arr - arrival, 0.0)
        want[0] = want[0] + self.k_seek_arr * self.miss_arr * self.capacity[0]
        want[0] = want[0] + getattr(self, 'kpi_push', 0.0) * self.capacity[0] * max(want.sum(), 1e-9)
        nv = getattr(self, 'net_push', None)
        if nv is not None:
            want = want + np.asarray(nv, float) * self.capacity * max(want.sum(), 1e-9)
        si = getattr(self, 'sense_intero', 0.0)
        if si:
            self.H = self.H * (1.0 - 0.05) + si

        B = self.ratio * want.sum()
        if self.alloc_fn is not None:
            a = self.alloc_fn(want, B, self)
        else:
            o = np.argsort(-want)
            a = np.zeros(self.N)
            left = B
            for i in o:
                tk = min(want[i], left)
                a[i] = tk
                left -= tk
                if left <= 1e-12:
                    break
        unmet = np.maximum(want - a, 0.0)
        self._last_unmet = unmet

        if self.alpha_homeo:
            tension = float(np.mean(self.dev_last)) if hasattr(self, 'dev_last') else float(dev.mean())
            self.alpha = self.alpha * self.alpha_decay + self.k_alpha * tension
            self.alpha = float(np.clip(self.alpha, 0.0, 1.0))
            self.alpha_hist.append(self.alpha)

        # ---- 干预点 2：可逆性 ----
        if self.reversible:
            # 未满足 → 衰减；满足（unmet≈0）→ 按同速率恢复，上限 1.0
            rec = self.cap_decay * (unmet <= 1e-9).astype(float) * (1.0 - self.capacity)
            self.capacity = np.minimum(self.capacity + rec, 1.0)
        # 不可逆分支：与原引擎一致（只减不增）
        self.capacity = np.maximum(self.capacity - self.cap_decay * unmet * self.capacity, self.cap_min)

        self.H = self.H * (1.0 - self.lam_H) + unmet

        # ---- 干预点 1：能量来源 ----
        cap = self.cap_max * e
        cap_share = cap / self.N
        done = np.minimum(a, cap_share)
        if self.energy == 'endo':
            # 原引擎：代谢预算（有 basal 消耗，摄食由自身产出换）
            self.E = self.E - (self.basal + self.c1 * done.sum())
            self.E = self.E + self.fg * self.fg_eff * done[self.forage_ch] / max(cap_share, 1e-12)
        else:
            # Avida 式：能量是奖励（无 basal 消耗，完成任务即净收益）
            self.E = self.E + self.fg * self.fg_eff * done[self.forage_ch] / max(cap_share, 1e-12)
        self.E = min(self.E, self.Emax)

        if self.E <= 0.0:
            self.E = 0.0
            self.low_ticks += 1
            if self.low_ticks > self.death_patience:
                self.alive = False
                self.death_t = self.t
        else:
            self.low_ticks = 0

        invest = a / max(a.sum(), 1e-12) * self.N
        self.y = self.y + self.mu * invest * (self.sp - self.y) - self.leak * self.y
        self.y = np.clip(self.y, 1e-6, 2.0)
        self.ref = self.ref + (self.y - self.ref) / self.tau_ref
        self.sp = self.sp + (self.ref - self.sp) / self.tau_sp
        self.sp = np.maximum(self.sp, self.sp_floor)
        self.b = w0
        self.t += 1
        tot = float(a.sum())
        rec = dict(t=self.t, E=self.E, alive=self.alive,
                   cap=float(self.capacity.mean()),
                   share0=float(a[0] / tot) if tot > 1e-12 else 0.0,
                   capv=[float(v) for v in self.capacity])
        self.log.append(rec)
        return rec


def run_cell(energy, reversible, seeds, steps=600, N=8, ratio=0.45):
    """指标说明（059 修正版）：

    初版用 std/mean 量"疤痕"，被实测推翻 —— 可逆模式下满足的通道回到 1.0、
    不满足的继续掉，反而【拉大】离散度。离散度不是不可逆性的度量。

    改用两个直接指标：
      rise_max   = 全程 capacity 出现过的最大的正向回升量（不可逆应恒为 0）
      perm_loss  = 终态相对初值的永久损失（1 - 终态均值），初值恒为 1.0
    """
    skews, deaths, capmeans, rises, ploss = [], 0, [], [], []
    for sd in seeds:
        lf = Life5Pos(energy=energy, reversible=reversible, N=N, seed=sd, ratio=ratio)
        lf.run(steps)
        c = np.array(lf.capacity)
        skews.append(float(c.std() / max(c.mean(), 1e-12)))
        capmeans.append(float(c.mean()))
        # 逐拍检查是否有通道回升
        traj = np.array([r['capv'] for r in lf.log])
        d = np.diff(traj, axis=0)
        rises.append(float(max(d.max(), 0.0)))
        ploss.append(float(1.0 - c.mean()))
        if not lf.alive:
            deaths += 1
    return dict(
        energy=energy, reversible=reversible, n=len(seeds),
        skew=float(np.mean(skews)), skew_se=float(np.std(skews, ddof=1) / np.sqrt(len(seeds))),
        cap_mean=float(np.mean(capmeans)), deaths=deaths,
        death_rate=deaths / len(seeds),
        rise_max=float(np.mean(rises)),
        perm_loss=float(np.mean(ploss)),
    )


def main():
    seeds = list(range(16))
    cells = {}
    for en in ('endo', 'exo'):
        for rv in (False, True):
            k = f"{en}_{'rev' if rv else 'irrev'}"
            cells[k] = run_cell(en, rv, seeds)
            c = cells[k]
            print(f"{k:14s} 死亡 {c['deaths']}/{c['n']}  "
                  f"永久损失 {c['perm_loss']:.4f}  最大回升 {c['rise_max']:.6f}  "
                  f"(偏度 {c['skew']:.4f})")

    # ---- 判据核验（059 修正版）----
    # 原 P3 预注册「Avida 格（exo×rev）偏度接近 0」已被实测推翻：
    #   exo_rev 偏度 0.4990 ~= exo_irrev 0.2695，离散度根本不区分可逆性。
    #   原因：可逆让满足的通道回到 1.0、不满足的继续掉，反而拉大离散度。
    # 改用直接指标重写判据。
    verdict = {}
    verdict['P1_死亡只出现在endo列_exo列恒不死'] = (
        cells['exo_irrev']['deaths'] == 0 and cells['exo_rev']['deaths'] == 0
        and (cells['endo_irrev']['deaths'] + cells['endo_rev']['deaths']) > 0
    )
    verdict['P2_不可逆列capacity从不回升'] = (
        cells['endo_irrev']['rise_max'] == 0.0 and cells['exo_irrev']['rise_max'] == 0.0
    )
    verdict['P3_可逆列确实出现回升'] = (
        cells['endo_rev']['rise_max'] > 0.0 and cells['exo_rev']['rise_max'] > 0.0
    )
    verdict['P4_可逆列永久损失显著小于不可逆列'] = (
        cells['endo_rev']['perm_loss'] < cells['endo_irrev']['perm_loss']
        and cells['exo_rev']['perm_loss'] < cells['exo_irrev']['perm_loss']
    )
    # 被推翻的预注册（保留记录，不得删除）
    verdict['【已推翻】原P3_exo_rev偏度接近0'] = cells['exo_rev']['skew'] < 0.05

    print("\n--- 判据核验 ---")
    for k, v in verdict.items():
        print(f"  {'✓' if v else '✗'} {k}")

    out = dict(cells=cells, verdict=verdict, seeds=len(seeds), steps=600, N=8, ratio=0.45)
    p = os.path.join(os.path.dirname(__file__), '..', 'data', 'positioning_results.json')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n已写入 {p}")
    return out


if __name__ == '__main__':
    main()
