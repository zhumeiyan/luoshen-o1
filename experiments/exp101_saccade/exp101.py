# -*- coding: utf-8 -*-
"""
101 · 主动扫视靠什么看清：周边视觉引导 vs 盲动

生物学事实：人类中心凹(fovea)只占视野约 1~2°，高分辨率但极窄；
周边视觉(peripheral)分辨率低但覆盖广，它的功能是**告诉中心凹该往哪跳**。
扫视(saccade)不是随机的，是被周边视觉引导的。

科学问题：
  在同样的采样预算下，"主动扫视"本身够不够？
  还是必须搭配周边引导才有效？

2x2 设计：
  A 周边+主动    ← 生物学真实配置
  B 周边+固定
  C 无周边+主动  ← 主动但盲（瞎动）
  D 无周边+固定  ← 基线

任务：4 个候选物体，扫视其中一个，用累积特征识别它是哪个。
关键：总采样预算固定，只有移动策略不同。

阳性对照：能看到全图时识别率必须为 1.0，否则任务本身无效。
"""
import numpy as np, cv2, json, os, hashlib

N_OBJ = 4          # 候选物体数
S = 400            # 物体尺寸
FOV = 128          # 中心凹尺寸
PERIPH = 32        # 周边视觉分辨率
T = 8              # 采样预算（扫视次数）
N_TRIAL = 24       # 每个条件的试验数（物体 x 起始位置）

ORB_KW = dict(nfeatures=600)


def make_object(seed, S=400, n=1400):
    """合成一个带丰富局部特征的物体（不同 seed = 不同物体）"""
    rng = np.random.default_rng(1000 + seed)
    img = np.full((S, S), 60, np.uint8)
    for _ in range(n):
        x, y = rng.integers(4, S - 4, 2)
        r = int(rng.integers(1, 4))
        cv2.circle(img, (int(x), int(y)), r, int(rng.integers(150, 255)), -1)
    # 加一点结构（让不同物体有可区分的宏观布局）
    for _ in range(6):
        cx, cy = rng.integers(80, S - 80, 2)
        a = int(rng.integers(20, 60))
        cv2.rectangle(img, (int(cx) - a, int(cy) - a), (int(cx) + a, int(cy) + a),
                      int(rng.integers(90, 140)), 2)
    return img


def fovea_view(img, cx, cy, F=FOV):
    """中心凹：切出以 (cx,cy) 为中心的高分辨率局部"""
    h, w = img.shape
    x0 = int(np.clip(cx - F // 2, 0, w - F))
    y0 = int(np.clip(cy - F // 2, 0, h - F))
    return img[y0:y0 + F, x0:x0 + F], (x0, y0)


def peripheral_view(img, res=PERIPH):
    """周边视觉：低分辨率全图（信息少但覆盖全）"""
    small = cv2.resize(img, (res, res), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0)


def salience_map(periph):
    """从周边图算显著性：局部梯度能量（哪里有结构）"""
    gx = cv2.Sobel(periph, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(periph, cv2.CV_64F, 0, 1, ksize=3)
    return cv2.GaussianBlur(np.sqrt(gx ** 2 + gy ** 2), (5, 5), 0)


def identify(acc_desc, cand_desc, orb):
    """用累积描述子在候选中做识别，返回 (预测idx, 各候选匹配数)"""
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    scores = []
    for cd in cand_desc:
        if acc_desc is None or len(acc_desc) < 2 or cd is None or len(cd) < 2:
            scores.append(0)
            continue
        m = bf.knnMatch(acc_desc, cd, k=2)
        good = [a for p in m if len(p) == 2 for a, b in [p] if a.distance < 0.75 * b.distance]
        scores.append(len(good))
    return int(np.argmax(scores)), scores


def run_one(obj, cand_desc, orb, mode, seed, start=(200, 200)):
    rng = np.random.default_rng(seed)
    periph = peripheral_view(obj) if mode.startswith("P") else None
    sal = salience_map(periph) if periph is not None else None

    acc = None
    cx, cy = start
    visited = []
    # 已访问抑制：避免重复看同一处（模拟扫视的抑制返回）
    inh = np.zeros((PERIPH, PERIPH)) if sal is not None else None

    for t in range(T):
        if mode.endswith("FIXED"):
            pass  # 固定：不动
        elif mode.endswith("ACTIVE"):
            if sal is not None:
                # 主动+周边：跳向当前最显著且未访问过的位置
                s = sal - inh * (sal.max() + 1e-9)
                idx = int(np.argmax(s))
                py, px = divmod(idx, PERIPH)
                cx = int(np.clip(px / PERIPH * S, FOV // 2, S - FOV // 2))
                cy = int(np.clip(py / PERIPH * S, FOV // 2, S - FOV // 2))
            else:
                # 主动但盲：随机跳，只避开已访问
                for _ in range(20):
                    nx = int(rng.integers(FOV // 2, S - FOV // 2))
                    ny = int(rng.integers(FOV // 2, S - FOV // 2))
                    if all(abs(nx - vx) > FOV // 2 or abs(ny - vy) > FOV // 2
                           for vx, vy in visited):
                        cx, cy = nx, ny
                        break
                else:
                    cx, cy = int(rng.integers(FOV // 2, S - FOV // 2)), \
                             int(rng.integers(FOV // 2, S - FOV // 2))
        elif mode.endswith("RANDOM"):
            cx, cy = int(rng.integers(FOV // 2, S - FOV // 2)), \
                     int(rng.integers(FOV // 2, S - FOV // 2))

        visited.append((cx, cy))
        view, _ = fovea_view(obj, cx, cy)
        k, d = orb.detectAndCompute(view, None)
        if d is not None:
            acc = d if acc is None else np.vstack([acc, d])
        if inh is not None:
            py = int(np.clip(cy / S * PERIPH, 0, PERIPH - 1))
            px = int(np.clip(cx / S * PERIPH, 0, PERIPH - 1))
            cv2.circle(inh, (px, py), 4, 1.0, -1)

    n_kp = 0 if acc is None else len(acc)
    pred, scores = identify(acc, cand_desc, orb)
    return dict(n_kp=n_kp, pred=pred, scores=scores, visited=visited)


def main():
    orb = cv2.ORB_create(**ORB_KW)
    objs = [make_object(i) for i in range(N_OBJ)]
    cand_desc = []
    for o in objs:
        k, d = orb.detectAndCompute(o, None)
        cand_desc.append(d)
        print(f"object {len(cand_desc)-1}: full kp = {len(k)}")

    # ===== 阳性对照：看得见全图 =====
    pc_ok, pc_acc = 0, []
    for ti, o in enumerate(objs):
        k, d = orb.detectAndCompute(o, None)
        pred, _ = identify(d, cand_desc, orb)
        pc_ok += int(pred == ti)
        pc_acc.append(pred == ti)
    print(f"[阳性对照] 全图可见 识别率 = {pc_ok}/{N_OBJ}")
    assert pc_ok == N_OBJ, "阳性对照未通过：任务本身无效"

    # ===== 阴性对照：完全不看 =====
    nc_pred, nc_sc = identify(None, cand_desc, orb)
    print(f"[阴性对照] 零采样 scores = {nc_sc}")

    modes = ["P+ACTIVE", "P+FIXED", "N+ACTIVE", "N+RANDOM", "N+FIXED"]
    results = {m: [] for m in modes}
    for ti in range(N_OBJ):
        for si in range(N_TRIAL // N_OBJ):
            seed = 7000 + ti * 100 + si
            start = (int(120 + 160 * ((si * 7) % 3) / 2), int(120 + 160 * ((si * 5) % 3) / 2))
            for m in modes:
                r = run_one(objs[ti], cand_desc, orb, m, seed, start)
                r["target"] = ti
                r["correct"] = int(r["pred"] == ti)
                results[m].append(r)

    out = {}
    print("\n=== 主结果（预算 T=%d，fovea=%d）===" % (T, FOV))
    for m in modes:
        rs = results[m]
        acc = np.mean([r["correct"] for r in rs])
        kp = np.mean([r["n_kp"] for r in rs])
        out[m] = dict(acc=float(acc), n_kp=float(kp), n=len(rs),
                      per_target=[int(r["correct"]) for r in rs])
        print(f"{m:10s} 识别率 {acc:.4f}  累积特征 {kp:.1f}")

    out["_meta"] = dict(T=T, FOV=FOV, PERIPH=PERIPH, N_OBJ=N_OBJ, N_TRIAL=N_TRIAL,
                        orb=ORB_KW,
                        positive_control=float(pc_ok / N_OBJ),
                        negative_control_scores=nc_sc)
    out["_sha"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    with open("result_101.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nsaved result_101.json  sha", out["_sha"])


if __name__ == "__main__":
    main()
