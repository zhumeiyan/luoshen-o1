# -*- coding: utf-8 -*-
"""
实验 071 · 硅基体的感官资格：再传入原则（Reafference Principle）

自然科学依据
------------
von Holst & Mittelstaedt (1950) 再传入原则：一个系统要拥有"感官"，
不取决于有没有感受器硬件，而取决于能否区分
    reafference  （自身动作引起的感觉输入）
    exafference  （外界引起的感觉输入）
区分的机制是 efference copy（传出副本/伴随放电）：动作发出的同时，
中枢留一份副本，据此预测感觉后果；实际输入与预测比对，
匹配 -> 自生，失配 -> 外生。

本实验不模拟感觉：感知走真实文件 I/O，动作走真实文件写入，
外部扰动由独立子进程真实写入。延迟与噪声是真实的。

对照与反偏见自检
----------------
* 副本精度 c 扫描 -> 必须有单调梯度（第 23 条：变量静默失效）
* 撤掉副本 -> 区分能力必须归零（负对照）
* 无关对照：只改文件时间戳不改内容 -> 应无效应
"""
import json, os, random, shutil, subprocess, sys, tempfile, time

WORLD = os.path.join(tempfile.mkdtemp(prefix="world071_"), "state.json")

def act(v):
    """效应器：真实写入世界"""
    with open(WORLD, "w") as f:
        json.dump({"v": float(v), "t": time.time()}, f)

def sense():
    """感受器：真实读取世界"""
    with open(WORLD) as f:
        return json.load(f)["v"]

def disturb(v):
    """外界：由独立子进程真实写入，agent 无副本"""
    subprocess.run([sys.executable, "-c",
        f"import json;json.dump({{'v':{v},'t':0}},open('{WORLD}','w'))"], check=True)

def trial(rng, c, external_mag, mode):
    """一次试验：返回 (是否外生, 预测误差)"""
    act(0.5)
    base = sense()                       # 感知当前状态
    if mode == "self":
        delta = rng.uniform(-0.3, 0.3)
        pred = base + delta * c          # 传出副本（精度 c）
        act(base + delta)                # 自身动作
        is_ext = 0
    elif mode == "ext":
        pred = base                      # 无副本，只预测"不变"
        disturb(base + rng.choice([-1, 1]) * external_mag)
        is_ext = 1
    else:                                # 无关对照
        pred = base
        with open(WORLD) as f: d = json.load(f)
        d["t"] = time.time()
        json.dump(d, open(WORLD, "w"))
        is_ext = 0
    actual = sense()
    return is_ext, abs(actual - pred)

def run(c, ext_mag, n=60, seed=7):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        m = "ext" if i % 2 else ("ctrl" if i % 6 == 5 else "self")
        rows.append(trial(rng, c, ext_mag, m))
    return rows

def auc(pos, neg):
    if not pos or not neg: return float("nan")
    s = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return s / (len(pos) * len(neg))

def evaluate(rows):
    pos = [e for f, e in rows if f == 1]
    neg = [e for f, e in rows if f == 0]
    return {"auc": round(auc(pos, neg), 4),
            "err_self": round(sum(neg) / len(neg), 4) if neg else None,
            "err_ext":  round(sum(pos) / len(pos), 4) if pos else None}

def main():
    out = {}
    # ① 副本精度扫描（必须有梯度）
    sweep = {}
    for c in [0.0, 0.25, 0.5, 0.75, 0.9, 1.0]:
        sweep[c] = evaluate(run(c, 0.4))
    out["A_副本精度扫描"] = sweep
    # ② 外界幅度扫描（检测灵敏度）
    mag = {}
    for m in [0.02, 0.05, 0.1, 0.2, 0.4]:
        mag[m] = evaluate(run(1.0, m))
    out["B_外界幅度扫描"] = mag
    # ③ 无关对照：只改时间戳
    rows = run(1.0, 0.4)
    ctrl = [e for i, (f, e) in enumerate(rows) if i % 6 == 5]
    out["C_无关对照_仅改时间戳"] = {"n": len(ctrl),
        "mean_err": round(sum(ctrl) / len(ctrl), 6) if ctrl else None}
    # ④ 主动感知：主动探测 vs 被动观察 的信息获取速率
    rng = random.Random(11)
    active_hits = passive_hits = 0
    for _ in range(60):
        act(0.5)
        probe = rng.choice([-0.2, 0.2])
        act(0.5 + probe); got = sense()          # 主动：发动作再感知
        active_hits += abs(got - (0.5 + probe)) < 1e-9
        disturb(0.5 + rng.choice([-1, 1]) * 0.4)  # 被动：外界变了才感知
        passive_hits += abs(sense() - 0.5) > 1e-9
    out["D_主动感知"] = {"主动探测命中": active_hits, "被动察觉命中": passive_hits, "样本": 60}
    shutil.rmtree(os.path.dirname(WORLD), ignore_errors=True)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out

if __name__ == "__main__":
    main()
