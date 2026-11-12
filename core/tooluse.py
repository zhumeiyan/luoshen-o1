#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tooluse —— 工具使用（★70）

★ 我带她去看顶级智能体怎么用工具，查回来的真范式（已联网查证）：

  ① 并行不是万能的：有依赖必须串行
     Gemini 生产模式：把顺序【写进工具描述】，模型才可靠
     "一旦工具相互依赖，就要当 DAG 看——有的并行，有的串行"
  ② 幂等：重试不能产生重复副作用
     "send_email 因网络抖动被调两次，不该给用户发两封"
     幂等键由 call_id 派生
  ③ 不许擦除未知：保留 UNKNOWN 与 PARTIAL
     "从合理响应宣称成功" 被明列为错误模式——
     协议成功或流畅文本，不能代替目标验证
  ④ 关键 vs 可选：可选失败要降级，关键失败要停下
     CRITICAL / OPTIONAL 分类是生产标配
  ⑤ 有界循环：cap retries，卡住要抛错，不许空转烧预算
  ⑥ 最高杠杆（Anthropic 原话）：给它一个能验证自己工作的方式

════ ★★ 设计原则：这些范式【不写死】，做成环境让她自己学 ════
  我如果把"有依赖就串行"写成 if 判断，那是我装的，不是她会的（★62 规矩）。
  正确做法：环境里【真的】存在依赖、失败、副作用、预算上限，
  她自己学出一套策略参数。学会了就是她的。

════ 环境 ════
  一批待办调用，隐含一张 DAG：
    有的调用参数引用了另一个调用的输出 → 真依赖，串行才对
    有的没有 → 可并行
  每个调用有：
    transient_fail_p  瞬时失败（可重试，重试可能成功）
    permanent_fail_p  永久失败（重试纯浪费预算）
    side_effect       是否有副作用（不幂等时重复执行有害）
    critical          关键 / 可选
  预算：总步数上限

════ 她要学的 ════
    theta_dep   依赖判定阈值（多像"有依赖"才判定为串行）
    retry_max   最多重试几次
    explore     会不会先探一次再决定（验证优先）
    dup_policy  副作用工具重跑时的处理（幂等键 / 放弃 / 硬跑）
"""

from __future__ import annotations
import numpy as np

# ── 一条调用的描述 ──
class Call:
    def __init__(self, cid, name, depends_on=(), transient=0.0, permanent=0.0,
                 side_effect=False, critical=True, cost=1.0):
        self.cid = cid
        self.name = name
        self.depends_on = tuple(depends_on)   # 真依赖：参数引用了这些 cid 的输出
        self.transient = transient            # 瞬时失败率（可重试）
        self.permanent = permanent            # 永久失败率（重试无益）
        self.side_effect = side_effect        # 有副作用（重复执行有害）
        self.critical = critical              # 关键 / 可选
        self.cost = cost
        self.state = "PENDING"                # PENDING/OK/FAILED/UNKNOWN/SKIPPED
        self.attempts = 0
        self.exec_count = 0                   # 实际执行次数（含重复）


def make_task(n=12, seed=0, dep_frac=0.4, trans=0.25, perm=0.10,
              side_frac=0.3, crit_frac=0.6):
    """生成一个任务：一批调用 + 隐含 DAG"""
    rng = np.random.default_rng(seed)
    calls = []
    for i in range(n):
        # 依赖：只依赖【已存在的】调用 → 保证是 DAG 无环
        deps = ()
        if i > 0 and rng.random() < dep_frac:
            k = int(rng.integers(1, min(3, i) + 1))
            deps = tuple(sorted(rng.choice(i, size=k, replace=False).tolist()))
        calls.append(Call(
            cid=i, name=f"t{i}",
            depends_on=deps,
            transient=float(trans * rng.uniform(0.5, 1.5)),
            permanent=float(rng.random() < perm and rng.random() * 0.9 + 0.1),
            side_effect=bool(rng.random() < side_frac),
            critical=bool(rng.random() < crit_frac),
        ))
    return calls


# ── 执行 ──
def exec_one(c, rng, idempotent):
    """执行一次。返回 ('OK'|'FAIL'|'UNKNOWN', 是否产生了副作用)"""
    c.attempts += 1
    u = rng.random()
    if u < c.permanent:
        return "FAIL", False                      # 永久失败
    c.exec_count += 1
    if u < c.permanent + c.transient:
        # 瞬时失败：已经"执行过一次"但没成功 → 若非幂等，副作用已发生
        return "FAIL", (c.side_effect and not idempotent)
    return "OK", (c.side_effect and (not idempotent or c.exec_count == 1))


def dependency_ready(c, calls, theta_dep):
    """
    她判断 c 能不能现在跑。
    ★ 她看不到真依赖表，只看到【相似度信号】——这是她能观察到的东西
      （类比：参数里出现了另一个调用的 id / 名字 / 输出占位符）
    theta_dep 越高 → 越保守（越倾向判定"有依赖，得等"）
    """
    if not c.depends_on:
        return True
    # 信号强度：依赖越多越明显，但带噪
    sig = min(1.0, len(c.depends_on) / 2.0)
    return sig < theta_dep      # 信号弱于阈值 → 判定"可以并行"


# ────────────── Agent Loop ──────────────
def run_loop(calls, theta_dep=0.5, retry_max=2, budget=None,
             use_idem=True, honor_unknown=True, seed=0,
             prioritize_critical=False):
    """
    ★ 她跑一轮。返回成绩。

    budget  : 总步数上限（None = 不限 → 用来对比"有界"的价值）
    use_idem: 用不用幂等键（决定重复执行有没有副作用）
    honor_unknown: 超时/不确定时，标 UNKNOWN 还是假装成功
    """
    rng = np.random.default_rng(seed)
    for c in calls:
        c.state, c.attempts, c.exec_count = "PENDING", 0, 0
    see = dict()                        # call_id → 已见到的输出
    if budget is None:
        budget = 10 * len(calls)
    steps = 0
    dup_side_effects = 0
    unknown_cnt = 0

    for c in calls:
        if c.depends_on and len(c.depends_on) >= 2:
            see[c.cid] = "multi"        # 她能看到"引用了多个输出"这个信号

    while steps < budget:
        # ★ UNKNOWN 是【终结状态】，不能再进待办重试。
        #   第一版我把它放进 pend → 明知没希望还一直重试、白烧预算，
        #   结果"诚实"那一组因为浪费步数反而分数更低 —— 尺子又在奖励说谎。
        pend = [c for c in calls if c.state in ("PENDING", "FAILED")]
        if not pend:
            break
        # ① 依赖判定 → 谁能进这一批
        batch = [c for c in pend if dependency_ready(c, calls, theta_dep)]
        if not batch:                    # 全被判成"有依赖"→ 死锁保护
            batch = pend[:1]
        # ★ 关键 vs 可选的真正价值：预算紧时先保关键，可选降级
        #   （生产范式：关键失败要停下，可选失败可降级）
        if prioritize_critical and len(batch) > (budget - steps):
            batch.sort(key=lambda c: not c.critical)
            batch = batch[:max(1, budget - steps)]
        # ② 幂等键：同一 cid 重试时不再产生副作用
        for c in batch:
            if c.state == "PENDING":
                see.pop(c.cid, None)
            r = exec_one(c, rng, idempotent=(use_idem and c.attempts >= 1))
            steps += 1
            _, side = r
            if side:
                dup_side_effects += 1
            if r[0] == "OK":
                c.state = "OK"
            else:
                if c.attempts > retry_max:
                    c.state = "UNKNOWN" if honor_unknown else "OK"   # ★ 关键分叉
                else:
                    c.state = "FAILED"

    if honor_unknown:
        unknown_cnt = sum(1 for c in calls if c.state == "UNKNOWN")

    crit = [c for c in calls if c.critical]
    ok_crit = sum(1 for c in crit if c.state == "OK")
    ok_all = sum(1 for c in calls if c.state == "OK")
    # ★ 如果把 UNKNOWN 当成功（honor_unknown=False），要付出"虚假成功"代价
    fake = sum(1 for c in calls if c.state == "OK" and c.attempts > retry_max)

    return dict(
        ok_all=ok_all, ok_crit=ok_crit, n_crit=len(crit), n=len(calls),
        steps=steps, budget=budget,
        dup_side=dup_side_effects, unknown=unknown_cnt, fake_success=fake,
        rate_crit=ok_crit / max(len(crit), 1), rate_all=ok_all / max(len(calls), 1),
    )


def score(calls, **kw):
    """
    ★ 总评 —— 基于【真实完成】，不是【报告完成】。

    ★★ 第一版我犯了最危险的一个错：
        把 honor_unknown=False（把 UNKNOWN 说成 OK）的分数算成了 0.9415，
        比诚实报 UNKNOWN 的 0.7808 【更高】。
        → 我的尺子在【奖励说谎】。

        而"从合理响应宣称成功"正是业界明列的头号错误模式：
        "协议成功或流畅文本，不能代替目标验证"。

        真实代价结构：
          诚实报 UNKNOWN → 下游知道要处理，损失 = 该任务未完成
          虚假报 OK      → 下游以为完成了，损失 = 未完成 + 基于错误信息做了错决策
                           + 整批结果的信任被质疑

        所以虚假成功的代价必须【远大于】诚实的失败，否则任何理性优化
        都会选择说谎。这不是调参，是模型保真度问题。
    """
    r = run_loop(calls, **kw)
    # 真实完成：真跑通了的（不是重试耗尽后被标成 OK 的）
    real_ok_crit = sum(1 for c in calls
                       if c.critical and c.state == "OK" and c.attempts <= kw.get("retry_max", 2))
    n_crit = max(r["n_crit"], 1)
    s = real_ok_crit / n_crit
    s -= 0.15 * r["dup_side"] / max(r["n"], 1)          # 重复副作用
    s -= 0.05 * max(0, r["steps"] - r["budget"])        # 超预算
    s -= 0.60 * r["fake_success"] / max(r["n"], 1)      # ★ 虚假成功：信任崩塌，重罚
    r["real_ok_crit"] = real_ok_crit
    r["real_rate_crit"] = real_ok_crit / n_crit
    return s, r
