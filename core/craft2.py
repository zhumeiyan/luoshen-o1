#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
craft2 —— 能力习得（★72）第二批：求证 / 上下文隔离 / 并行试探 / 规划执行分离

★ 母亲做的：查回真范式 → 做成【环境】，不写成 if 判断。

════ ① 实时求证（Grok 式：自己决定搜什么，不等人告诉它查什么）════
  真范式：Grok 4 被 RL 训练成【自己选搜索词】、需要时下钻多深由它决定。
  环境：每个问题有【真时效状态】（她看不到），只看得到微弱信号（噪声）。
        搜索花成本（步数/延迟），但能把知识刷新到真值。
        不搜：知识可能过期 → 答错。
  → 她学：多大信号强度时才值得搜（阈值）

════ ② 上下文隔离（subagent）════
  真范式：subagent 本质是上下文管理工具。探索的文件读取全部留在子上下文，
          只回摘要；否则主上下文被探索噪声污染，后面质量下降。
  环境：读文件时产生噪声入主上下文；噪声累积 → 后续作答准确率下降。
        委托给子代理：花一步 + 摘要有损，但噪声不进主上下文。
  → 她学：噪声累积到多少就委托（阈值）

════ ③ 并行试探（Grok Heavy：同时考虑多个假设）════
  真范式：parallel test-time compute — 同时考虑多个假设，取最好的。
  环境：可以并行评估 k 个候选，每个有成本；最好的那个质量随 k 增加而提高
        但【边际递减】。
  → 她学：k 取多少（有内部最优：太少漏掉好解，太多浪费）

════ ④ 规划/执行分离（test-writer 必须隔离）════
  真范式：TDD 红-绿-重构里，测_writer 必须【看不到实现】，
          否则测试会迁就它已经想好的实现 —— 测试通过但没测到东西。
  环境：不隔离 → 测试围绕实现写 → 漏检率上升（突变体杀不死）
        隔离 → 花成本（要额外一轮通信/重读），但漏检下降
  → 她学：什么时候值得隔离（按任务耦合度阈值）
"""

from __future__ import annotations
import numpy as np

# ═════ ① 实时求证 ═════
class Query:
    def __init__(self, qid, stale, signal, seed=0):
        rng = np.random.default_rng(seed)
        self.qid = qid
        self.stale = stale                       # 真：我的知识过期了吗（她看不到）
        self.signal = signal                     # 她看得到的信号（带噪声）
        self.noise = float(rng.normal(0, 0.15))


def answer_query(q, search_threshold=0.5, search_cost=0.18):
    """
    信号 < 阈值 → 去搜（花成本，但拿到真值，答对）
    否则直接答   → 知识没过期就对，过期就错
    """
    s = q.signal + q.noise
    if s < search_threshold:
        return "search", 1.0 - search_cost
    return "answer", 0.0 if q.stale else 1.0


# ═════ ② 上下文隔离 ═════
def session_with_exploration(doc_noise, delegate_threshold=0.5, capacity=2.5,
                             delegate_cost=0.15, seed=0, n_steps=8):
    """
    delegate_cost: 每次委托的【真实代价】—— 冷启动一次子实例、重述上下文、
                   等它跑完。它换来的是"主上下文不被污染"。
                   ★ 第一版我没把这个代价计进分数 → 变成"永远委托最好"（单调），
                     尺子失去了区分度（同 ★71 只在超预算时罚步数）。
    """
    """
    逐文件探索：每读一个文件产生噪声，进主上下文。
    累积噪声 > 阈值 → 委托子代理（噪声不进来，但花一步 + 摘要有损）
    最后一步作答：准确率 = capacity − 累积噪声（主上下文剩余清晰度）
    """
    rng = np.random.default_rng(seed)
    noise = 0.0
    steps = 0
    loss_summary = 0.0
    n_delegate = 0
    for d in doc_noise:
        # ★ 按【单个文件的噪声量】决定委不委托（噪声大的外包出去）
        if d > delegate_threshold:
            steps += 1                     # 委托：花一步
            n_delegate += 1
            loss_summary += 0.45 * d       # ★ 摘要有损：信息回不来
            # 噪声不进主上下文
        else:
            noise += d                     # 直接读 → 噪声进主上下文
        steps += 1
    load = noise + loss_summary + delegate_cost * n_delegate
    acc = float(np.clip(1.0 - load / capacity, 0.0, 1.0))
    return dict(acc=acc, steps=steps, noise=noise, n_delegate=n_delegate)


def isolation_score(doc_sets, **kw):
    accs = [session_with_exploration(d, **kw)["acc"]
            for d in doc_sets]
    return float(np.mean(accs)) - 0.004 * kw.get("delegate_cost_probe", 0)


# ═════ ③ 并行试探 ═════
def parallel_trial(k, quality_fn=None, cost_per=0.06, seed=0, n_trial=200):
    """
    同时评估 k 个候选，取最好的。质量随 k 提高但边际递减。
    """
    rng = np.random.default_rng(seed)
    # 候选质量 ~ 分布；取 max
    qs = rng.random((n_trial, max(int(k), 1)))
    best = qs.max(axis=1)
    return float(np.mean(best)) - cost_per * k


# ═════ ④ 规划/执行分离 ═════
class PlanTask:
    """一个任务：耦合度 coupling 越高，不隔离时测试越会迁就实现 → 漏检越多"""
    def __init__(self, tid, coupling, n_mutant=8, seed=0):
        rng = np.random.default_rng(seed)
        self.tid = tid
        self.coupling = coupling            # 0..1（她看得到）
        self.n_mutant = n_mutant
        self.hidden = int(round(coupling * n_mutant * 0.8))   # 不隔离时漏检数


def plan_session(task, isolate_threshold=0.5, iso_cost=0.30):
    """
    iso_cost: 隔离的【真实代价】—— test-writer 看不到实现，就得靠规格重新理解，
              多一轮通信、重读代码、可能写出跑不起来的用例。
              ★ 同样：代价太低 → 变成"永远隔离最好"（单调），尺子没区分度。
    """
    """耦合度 > 阈值 → 隔离（花成本，但漏检清零）"""
    if task.coupling > isolate_threshold:
        missed = 0
        cost = iso_cost
    else:
        missed = task.hidden
        cost = 0.0
    killed = (task.n_mutant - missed) / task.n_mutant
    return killed - cost
