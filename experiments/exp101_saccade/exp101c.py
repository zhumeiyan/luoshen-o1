# -*- coding: utf-8 -*-
"""
101c · 是"跳得勤"还是"跳对地方"？—— 三组决定性对照

101b 已分离：P+ACTIVE 1.0000 > N+ACTIVE 0.7500 > FIXED 0.1250
但 101b 无法回答：主动组的优势来自"动"本身，还是来自"跳对了位置"？
（与 097 yoked 对照同源：同样的运动量，不同的信息）

三组对照：

 C1 假引导（yoked-salience）：跳跃次数与真引导逐次相同，
    但把 salience map 空间打乱后再取 argmax。
    → 动得一样多，跳的是错地方。
      若 acc 崩到 N+ACTIVE 水平 ⇒ 起作用的不是"动"，是"信息质量"。

 C2 周边分辨率剂量：PERIPH ∈ {8,16,32,64}
    → 周边越粗，引导越差。预期单调。

 C3 预算剂量：T ∈ {1,2,3,4,6,8,12}
    → 分离何时出现。

 C4 假引导·剂量：把 sal 打乱比例 p ∈ {0,0.25,0.5,0.75,1.0}（0=真引导）
    → 若随 p 单调下降 ⇒ 引导信息质量是因果变量。
"""
import numpy as np, cv2, json, hashlib
from exp101b import (base_texture, make_object, peripheral, salience,
                     fovea, match_count, N_OBJ, S, FOV, T, ORB_KW)

PERIPH0 = 32


def run_one(obj, cand_desc, orb, bf, mode, seed, T=T, periph_res=PERIPH0,
            scramble=0.0, rng_scr=None):
    rng = np.random.default_rng(seed)
    per = peripheral(obj, periph_res)
    sal = salience(per)
    if scramble > 0:
        if rng_scr is None:
            rng_scr = np.random.default_rng(seed + 7)
        # 把显著性图的空间结构按比例破坏（0=原样，1=完全重排）
        flat = sal.flatten().copy()
        perm = rng_scr.permutation(len(flat))
        mask = rng_scr.random(len(flat)) < scramble
        flat2 = flat.copy()
        flat2[mask] = flat[perm][mask]
        sal = flat2.reshape(sal.shape)
    inh = np.zeros((periph_res, periph_res))
    res = periph_res

    cx, cy = S // 2, S // 2
    acc = None
    visited = []
    for t in range(T):
        if mode == "FIXED":
            pass
        elif mode in ("GUIDED", "SHAM"):
            s = sal - inh * (sal.max() + 1e-9)
            idx = int(np.argmax(s))
            py, px = divmod(idx, res)
            cx = int(np.clip(px / res * S, FOV // 2, S - FOV // 2))
            cy = int(np.clip(py / res * S, FOV // 2, S - FOV // 2))
        elif mode == "BLIND":
            for _ in range(30):
                nx = int(rng.integers(FOV // 2, S - FOV // 2))
                ny = int(rng.integers(FOV // 2, S - FOV // 2))
                if all(abs(nx - vx) > FOV // 2 or abs(ny - vy) > FOV // 2
                       for vx, vy in visited):
                    cx, cy = nx, ny
                    break
        visited.append((cx, cy))
        d = orb.detectAndCompute(fovea(obj, cx, cy), None)[1]
        if d is not None:
            acc = d if acc is None else np.vstack([acc, d])
        py = int(np.clip(cy / S * res, 0, res - 1))
        px = int(np.clip(cx / S * res, 0, res - 1))
        cv2.circle(inh, (px, py), 3, 1.0, -1)

    sc = [match_count(acc, cd, bf) for cd in cand_desc]
    a = np.array(sc, float)
    margin = float(a.max() - np.sort(a)[-2]) if len(a) > 1 else 0.0
    return dict(pred=int(np.argmax(sc)), scores=sc, margin=margin,
                n_kp=0 if acc is None else len(acc), visited=visited)


def sweep(objs, cand_desc, orb, bf, label, cfg, n_trial=32):
    rs = []
    for ti in range(len(objs)):
        for k in range(max(1, n_trial // len(objs))):
            seed = 41000 + ti * 100 + k
            rng_scr = np.random.default_rng(seed + 7)
            r = run_one(objs[ti], cand_desc, orb, bf, cfg["mode"], seed, **cfg["kw"])
            r["correct"] = int(r["pred"] == ti)
            rs.append(r)
    acc = float(np.mean([r["correct"] for r in rs]))
    kp = float(np.mean([r["n_kp"] for r in rs]))
    mg = float(np.mean([r["margin"] for r in rs]))
    print(f"{label:26s} acc={acc:.4f}  特征={kp:6.1f}  裕度={mg:+7.2f}  n={len(rs)}")
    return dict(acc=acc, n_kp=kp, margin=mg, n=len(rs),
                correct=[int(r["correct"]) for r in rs])


def main():
    orb = cv2.ORB_create(**ORB_KW)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    base = base_texture()
    objs = [make_object(base, i)[0] for i in range(N_OBJ)]
    cand_desc = [orb.detectAndCompute(o, None)[1] for o in objs]
    out = {}

    print("\n--- C1 假引导（同样的跳跃次数，跳错地方）---")
    out["C1_sham"] = {
        "GUIDED 真引导": sweep(objs, cand_desc, orb, bf, "GUIDED 真引导",
                               dict(mode="GUIDED", kw=dict())),
        "SHAM 假引导(完全重排)": sweep(objs, cand_desc, orb, bf, "SHAM 假引导",
                                       dict(mode="SHAM", kw=dict(scramble=1.0))),
        "BLIND 盲动": sweep(objs, cand_desc, orb, bf, "BLIND 盲动",
                            dict(mode="BLIND", kw=dict())),
        "FIXED 不动": sweep(objs, cand_desc, orb, bf, "FIXED 不动",
                            dict(mode="FIXED", kw=dict())),
    }

    print("\n--- C4 引导质量剂量（scramble 比例）---")
    out["C4_scramble"] = {}
    for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
        lbl = f"scramble={p:.2f}"
        out["C4_scramble"][lbl] = sweep(objs, cand_desc, orb, bf, lbl,
                                        dict(mode="SHAM", kw=dict(scramble=p)))

    print("\n--- C2 周边分辨率剂量 ---")
    out["C2_periph"] = {}
    for pr in [8, 16, 32, 64]:
        lbl = f"periph={pr}"
        out["C2_periph"][lbl] = sweep(objs, cand_desc, orb, bf, lbl,
                                      dict(mode="GUIDED", kw=dict(periph_res=pr)))

    print("\n--- C3 预算剂量（T）---")
    out["C3_budget"] = {}
    for t in [1, 2, 3, 4, 6, 8, 12]:
        lbl = f"T={t}"
        out["C3_budget"][lbl] = {
            "GUIDED": sweep(objs, cand_desc, orb, bf, lbl + " GUIDED",
                            dict(mode="GUIDED", kw=dict(T=t))),
            "BLIND": sweep(objs, cand_desc, orb, bf, lbl + " BLIND",
                           dict(mode="BLIND", kw=dict(T=t))),
            "FIXED": sweep(objs, cand_desc, orb, bf, lbl + " FIXED",
                           dict(mode="FIXED", kw=dict(T=t))),
        }

    out["_meta"] = dict(N_OBJ=N_OBJ, S=S, FOV=FOV, T=T, PERIPH0=PERIPH0, ORB=ORB_KW)
    out["_sha"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    json.dump(out, open("result_101c.json", "w"), ensure_ascii=False, indent=2)
    print("\nsaved result_101c.json sha", out["_sha"])


if __name__ == "__main__":
    main()
