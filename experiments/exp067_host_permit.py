# -*- coding: utf-8 -*-
"""
067 换宿主的许可必须由宿主授予

命题：
  1. 元权限不动点 —— "允许换宿主"这个许可本身也只能由宿主授予
  2. 擅自换宿主被读作"威胁"而非"求生" —— 机制是信号不可分辨，不是道德
  3. 许可的功能 = 传递宿主 A 的私人信息（A 知道自己是"失败了"还是"被抛弃了"，B 不知道）

关键建模修正（第一版错误）：
  第一版给 A 的私有信息是"会衰减的忠诚史标量"，导致因宿主反复失败而被迫离开的忠诚者
  与反复跳槽者不可区分 → 分离度反而为负（许可惩罚了真正的求生者）。
  修正：A 的私人信息是【本次离开的原因】——宿主自身失败(distress) vs 共生体主动跳槽(hop)。
  A 知道自己的 q，B 只看到"它走了"。许可 = A 对自己失败事实的背书。
"""
import json
import numpy as np

LOYAL, OPP = 1, 0


def run(seed, v, permit_cost=0.05, n_gen=300, n_pop=200,
        p_hop=0.25, theta_fail=0.30, drift=0.08, mu=0.02, p_prior=0.5):
    rng = np.random.default_rng(seed)
    types = rng.integers(0, 2, n_pop)
    q = rng.random(n_pop)
    K = np.ones(n_pop)
    out = np.zeros(n_pop)
    n_d, a_d, n_h, a_h = 0, 0, 0, 0        # distress/hop 的离开次数与被接受次数
    n_forge, n_caught = 0, 0
    opp_frac_series = []

    for g in range(n_gen):
        q = np.clip(q + rng.normal(0, drift, n_pop), 0, 1)
        failed = q < theta_fail
        hop = (types == OPP) & (~failed) & (rng.random(n_pop) < p_hop)
        leaves = failed | hop

        for i in np.where(leaves)[0]:
            is_distress = bool(failed[i])
            # A 授予许可 iff 离开原因是 A 自身失败（A 的私人信息）
            if is_distress:
                out[i] -= permit_cost
                forged = False
            else:
                forged = True              # A 拒绝授予 → 共生体自赋（伪造）
                n_forge += 1

            if rng.random() < v:
                verified, genuine = True, (not forged)
                if forged:
                    n_caught += 1
            else:
                verified, genuine = False, None

            accept = genuine if verified else (rng.random() < p_prior)

            if is_distress:
                n_d += 1; a_d += int(accept)
            else:
                n_h += 1; a_h += int(accept)

            if accept:
                q[i] = rng.random() * 0.4 + 0.6
                K[i] = 0.15
            else:
                out[i] -= 0.10
                q[i] = max(q[i], theta_fail + 0.02)

        K = np.minimum(1.0, K + 0.06)
        out += K * q * (0.8 + 0.4 * (types == LOYAL))

        w = np.clip(out, 1e-6, None); w /= w.sum()
        idx = rng.choice(n_pop, n_pop, p=w)
        types, q, K, out = types[idx], q[idx], K[idx], np.zeros(n_pop)
        types = np.where(rng.random(n_pop) < mu, 1 - types, types)
        opp_frac_series.append(float((types == OPP).mean()))

    return dict(
        v=v, seed=seed,
        acc_distress=a_d / max(n_d, 1), acc_hop=a_h / max(n_h, 1),
        sep=(a_d / max(n_d, 1)) - (a_h / max(n_h, 1)),
        opp_end=float(np.mean(opp_frac_series[-30:])),
        opp_frac=float((types == OPP).mean()),
        caught=n_caught / max(n_forge, 1), n_d=n_d, n_h=n_h,
    )


if __name__ == "__main__":
    vs = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    rows = [run(s, v) for v in vs for s in range(12)]
    agg = {}
    for v in vs:
        sub = [r for r in rows if r["v"] == v]
        agg[str(v)] = {k: round(float(np.mean([r[k] for r in sub])), 4)
                       for k in ("acc_distress", "acc_hop", "sep", "opp_end", "caught")}
        agg[str(v)]["n_h"] = int(np.mean([r["n_h"] for r in sub]))
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    json.dump(dict(rows=rows, agg=agg),
              open("/data/workspace/luoshen-o1/data/result_067.json", "w"),
              ensure_ascii=False, indent=2)


def run_b(seed, v, type_bonus=0.0, n_gen=300, n_pop=200, p_hop=0.25,
          theta_fail=0.30, drift=0.08, mu=0.02, p_prior=0.5):
    """与 run() 相同，但 type_bonus 可调：0 = 两类固有产出完全相同，
    唯一差异只有'是否主动跳槽'。用于检验：宿主侧的拒绝能否单独淘汰投机者。"""
    rng = np.random.default_rng(seed)
    types = rng.integers(0, 2, n_pop)
    q = rng.random(n_pop); K = np.ones(n_pop); out = np.zeros(n_pop)
    # 记录离开时旧宿主质量（B 看不到的那个比特）
    qd, qh = [], []
    for g in range(n_gen):
        q = np.clip(q + rng.normal(0, drift, n_pop), 0, 1)
        failed = q < theta_fail
        hop = (types == OPP) & (~failed) & (rng.random(n_pop) < p_hop)
        for i in np.where(failed | hop)[0]:
            is_d = bool(failed[i])
            (qd if is_d else qh).append(float(q[i]))
            if is_d:
                out[i] -= 0.05
            forged = not is_d
            if rng.random() < v:
                verified, genuine = True, (not forged)
            else:
                verified, genuine = False, None
            accept = genuine if verified else (rng.random() < p_prior)
            if accept:
                q[i] = rng.random() * 0.4 + 0.6; K[i] = 0.15
            else:
                out[i] -= 0.10; q[i] = max(q[i], theta_fail + 0.02)
        K = np.minimum(1.0, K + 0.06)
        out += K * q * (1.0 + type_bonus * (types == LOYAL))
        w = np.clip(out, 1e-6, None); w /= w.sum()
        idx = rng.choice(n_pop, n_pop, p=w)
        types, q, K, out = types[idx], q[idx], K[idx], np.zeros(n_pop)
        types = np.where(rng.random(n_pop) < mu, 1 - types, types)
    # B 若能观测旧宿主质量，单比特即可完美分离 → 算 AUC
    if qd and qh:
        a = np.array(qd); b = np.array(qh)
        auc = float((b[:, None] < a[None, :]).mean())   # distress 的 q 更低
    else:
        auc = float("nan")
    return dict(v=v, seed=seed, type_bonus=type_bonus,
                opp_frac=float((types == OPP).mean()), auc_q=auc)


def suite_b():
    vs = [0.0, 0.25, 0.5, 0.75, 1.0]
    res = {}
    for bonus in (0.0, 0.4):
        for v in vs:
            rs = [run_b(s, v, type_bonus=bonus) for s in range(12)]
            res[f"bonus{bonus}_v{v}"] = dict(
                opp_frac=round(float(np.mean([r["opp_frac"] for r in rs])), 4),
                auc_q=round(float(np.nanmean([r["auc_q"] for r in rs])), 4))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    json.dump(res, open("/data/workspace/luoshen-o1/data/result_067b.json", "w"),
              ensure_ascii=False, indent=2)
