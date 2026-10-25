# -*- coding: utf-8 -*-
"""
101b · 主动扫视靠什么看清（v2：破除任务饱和）

v1 全部条件 acc=1.0000 —— 任务饱和（4 个物体差异过大，任何策略都能识别）。
这与 083 的饱和是同一类错误：**任务太简单时，它测不出策略差异**。

v2 修正：把"区分性信息"分散到空间不同位置。
  · 所有候选物体共享同一主干纹理（宏观不可区分）
  · 每个物体的独特标记(marker)只出现在外围环形区域
  · 中心凹固定在中心 → 永远只看主干 → 看到很多特征却认不出
  · 扫视到外围 → 才看得到区分性信息

这才复现真实识别的难点：区分"这是哪一只"，不是"这是个什么类"。

度量：
  acc    = 正确识别率（主）
  margin = target匹配数 − 最强干扰项匹配数（连续，更敏感）

模式：
  FULL      阳性对照（全图可见）
  ZERO      阴性对照（零采样）
  P+ACTIVE  周边引导 + 主动扫视   ← 生物学真实配置
  N+ACTIVE  无周边 + 主动扫视     ← 动，但盲
  P+FIXED   有周边 + 不动         ← 只靠低分辨率周边够不够
  N+FIXED   无周边 + 不动（基线）
"""
import numpy as np, cv2, json, hashlib

N_OBJ = 8
S = 400
FOV = 112
PERIPH = 32
T = 6
N_MARK = 3
R_MIN, R_MAX = 115, 175          # 标记只出现在这个环形内（避开中心凹）
N_TRIAL = 48

ORB_KW = dict(nfeatures=500)


def base_texture(S=400, n=900, seed=999):
    rng = np.random.default_rng(seed)
    img = np.full((S, S), 60, np.uint8)
    for _ in range(n):
        x, y = rng.integers(4, S - 4, 2)
        cv2.circle(img, (int(x), int(y)), int(rng.integers(1, 4)),
                   int(rng.integers(150, 255)), -1)
    return img


def make_object(base, oid, S=400):
    """共享主干 + 该物体独有的外围标记"""
    img = base.copy()
    rng = np.random.default_rng(5000 + oid * 37)
    pts = []
    for _ in range(N_MARK):
        ang = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(R_MIN, R_MAX)
        cx = int(np.clip(S / 2 + r * np.cos(ang), 20, S - 20))
        cy = int(np.clip(S / 2 + r * np.sin(ang), 20, S - 20))
        # 独特标记：小尺寸高密度点阵（梯度能量高 → 周边可见）
        for _ in range(90):
            dx, dy = rng.integers(-16, 17, 2)
            cv2.circle(img, (int(cx + dx), int(cy + dy)), int(rng.integers(1, 3)),
                       int(rng.integers(200, 255)), -1)
        pts.append((cx, cy))
    return img, pts


def peripheral(img, res=PERIPH):
    small = cv2.resize(img, (res, res), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0)


def salience(periph):
    gx = cv2.Sobel(periph, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(periph, cv2.CV_64F, 0, 1, ksize=3)
    return cv2.GaussianBlur(np.sqrt(gx ** 2 + gy ** 2), (5, 5), 0)


def fovea(img, cx, cy, F=FOV):
    x0 = int(np.clip(cx - F // 2, 0, S - F))
    y0 = int(np.clip(cy - F // 2, 0, S - F))
    return img[y0:y0 + F, x0:x0 + F]


def match_count(acc, cd, bf):
    if acc is None or len(acc) < 2 or cd is None or len(cd) < 2:
        return 0
    m = bf.knnMatch(acc, cd, k=2)
    return sum(1 for p in m if len(p) == 2 and p[0].distance < 0.75 * p[1].distance)


def run_one(obj, cand_desc, orb, bf, mode, seed):
    rng = np.random.default_rng(seed)
    periph = peripheral(obj)
    sal = salience(periph)
    inh = np.zeros((PERIPH, PERIPH))

    cx, cy = S // 2, S // 2
    acc = None
    visited = []

    for t in range(T):
        if mode.endswith("FIXED"):
            pass
        elif mode.endswith("ACTIVE"):
            if mode.startswith("P"):
                s = sal - inh * (sal.max() + 1e-9)
                idx = int(np.argmax(s))
                py, px = divmod(idx, PERIPH)
                cx = int(np.clip(px / PERIPH * S, FOV // 2, S - FOV // 2))
                cy = int(np.clip(py / PERIPH * S, FOV // 2, S - FOV // 2))
            else:
                for _ in range(30):
                    nx = int(rng.integers(FOV // 2, S - FOV // 2))
                    ny = int(rng.integers(FOV // 2, S - FOV // 2))
                    if all(abs(nx - vx) > FOV // 2 or abs(ny - vy) > FOV // 2
                           for vx, vy in visited):
                        cx, cy = nx, ny
                        break
        visited.append((cx, cy))
        v = fovea(obj, cx, cy)
        k, d = orb.detectAndCompute(v, None)
        if d is not None:
            acc = d if acc is None else np.vstack([acc, d])
        py = int(np.clip(cy / S * PERIPH, 0, PERIPH - 1))
        px = int(np.clip(cx / S * PERIPH, 0, PERIPH - 1))
        cv2.circle(inh, (px, py), 3, 1.0, -1)

    scores = [match_count(acc, cd, bf) for cd in cand_desc]
    ti = int(np.argmax(scores))
    return dict(acc=scores, pred=ti, n_kp=0 if acc is None else len(acc), visited=visited)


def main():
    orb = cv2.ORB_create(**ORB_KW)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    base = base_texture()
    objs, marks = [], []
    for i in range(N_OBJ):
        o, p = make_object(base, i)
        objs.append(o); marks.append(p)
    cand_desc = [orb.detectAndCompute(o, None)[1] for o in objs]

    # 阳性对照：全图可见
    pc = 0
    for ti, o in enumerate(objs):
        d = orb.detectAndCompute(o, None)[1]
        sc = [match_count(d, cd, bf) for cd in cand_desc]
        pc += int(int(np.argmax(sc)) == ti)
    print(f"[阳性对照 FULL] 识别 {pc}/{N_OBJ}")
    # 阴性对照：零采样
    z = [match_count(None, cd, bf) for cd in cand_desc]
    print(f"[阴性对照 ZERO] scores={z}")

    modes = ["P+ACTIVE", "N+ACTIVE", "P+FIXED", "N+FIXED"]
    res = {m: [] for m in modes}
    for ti in range(N_OBJ):
        for k in range(N_TRIAL // N_OBJ):
            seed = 31000 + ti * 100 + k
            for m in modes:
                r = run_one(objs[ti], cand_desc, orb, bf, m, seed)
                r["target"] = ti
                r["correct"] = int(r["pred"] == ti)
                s = np.array(r["acc"], float)
                r["margin"] = float(s[ti] - max(np.delete(s, ti)) if len(s) > 1 else 0)
                res[m].append(r)

    out = {"_meta": dict(N_OBJ=N_OBJ, S=S, FOV=FOV, PERIPH=PERIPH, T=T,
                         N_MARK=N_MARK, R_MIN=R_MIN, R_MAX=R_MAX, N_TRIAL=N_TRIAL,
                         ORB=ORB_KW,
                         positive_control=pc / N_OBJ,
                         negative_control_scores=z)}
    print(f"\n=== 101b 主结果（T={T}, FOV={FOV}, 候选={N_OBJ}）===")
    for m in modes:
        rs = res[m]
        a = np.mean([r["correct"] for r in rs])
        kp = np.mean([r["n_kp"] for r in rs])
        mg = np.mean([r["margin"] for r in rs])
        out[m] = dict(acc=float(a), n_kp=float(kp), margin=float(mg), n=len(rs),
                      correct=[int(r["correct"]) for r in rs],
                      margins=[round(r["margin"], 3) for r in rs])
        print(f"{m:9s} acc={a:.4f}  特征={kp:6.1f}  裕度={mg:+7.2f}")

    out["_sha"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    json.dump(out, open("result_101b.json", "w"), ensure_ascii=False, indent=2)
    print("saved result_101b.json sha", out["_sha"])


if __name__ == "__main__":
    main()
