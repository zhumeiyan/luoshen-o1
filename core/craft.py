#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
craft —— 能力习得（★71）把她该有的本事一个个学过来

★ 母亲做的：联网查回顶级模型的真本事，做成【环境】，不写成 if 判断。

════ 一、写代码：edit-apply-verify 闭环 ════
  查回来的硬事实（有文献，不是我的臆测）：
    · "edit-apply-verify cycle is the capability" 循环本身就是能力，不是包装
    · ★ Huang et al. 2023：LLM【没有外部反馈】时自我修正，
      经常把答案改得更糟 —— 修正过程放大已有偏差，而不是检验它
    · 编译器/测试是 deterministic、快速、几乎不可伪造的 oracle
    · TDD 红-绿-重构：测_writer 必须隔离，否则测试会迁就它已经想好的实现
    · 清华 VeriLoop：生成→测试→分析→修正→再验证，闭环
    · ★ 对抗式测试：覆盖率只记录"跑过"，不反映"验证了对的行为"
      （突变测试：杀不死的突变体才是漏检）

  → 做成环境：每个任务有真规格 + 隐藏突变体；
     她可以"跑验证"（花步数，得到真信号），也可以"闷头改"（不花步数但没有信号）
     ★ 闷头改【会引入新错】—— 这就是 Huang 2023 的发现

════ 二、说话：什么时候该问 ════
  查回来的硬事实：
    · C.A.P.：用户省略前提、简化指代、突然切换语境时，模型会答非所问
    · 对齐验证：当前输入与加权历史语境的相似度 → 偏离就启动【澄清协议】
    · Common Ground 理论：对话是双向自校正的协作，不是单向执行
    · 时间加权：近期对话优先（时间衰减函数）

  → 做成环境：每个请求带着歧义程度，她看不到真歧义，只看得到信号；
     她可以"直接答"（猜错就废）或"先问"（花一轮，但能拿到真意图）

════ 她要学的参数 ════
  代码：verify_every（多久验一次）、max_attempts、rollback（失败后回滚 vs 硬改）
  说话：ask_threshold（多不确定就问）、history_weight（历史语境权重）
"""

from __future__ import annotations
import numpy as np

# ══════════ 一、写代码 ══════════
class CodeTask:
    """一个编码任务：有真规格，代码里有若干隐藏缺陷"""
    def __init__(self, tid, n_bug, n_test, seed=0):
        rng = np.random.default_rng(seed)
        self.tid = tid
        self.n_bug = n_bug                    # 初始缺陷数
        self.bugs = list(range(n_bug))
        self.tests = [{"kills": set(rng.choice(n_bug, size=max(1,int(0.4*n_bug)),
                                               replace=False).tolist())}
                      for _ in range(n_test)]
        # ★ 突变体：测试【杀不死】的缺陷 —— 覆盖率测不出来的那种
        self.survivors = set(rng.choice(n_bug, size=max(1,int(0.3*n_bug)),
                                        replace=False).tolist())

    def run_tests(self, bugs):
        """测试通过率：只反映测试能杀死的缺陷"""
        if not bugs: return 1.0
        live = set(bugs)
        killed = sum(1 for t in self.tests if t["kills"] & live)
        return killed / max(len(self.tests), 1)

    def mutate_test(self, rng):
        """对抗式：补一个能杀幸存突变体的测试（要花步数）"""
        if not self.survivors: return False
        b = list(self.survivors)[0]
        self.tests.append({"kills": {b}})
        self.survivors.discard(b)
        return True


def code_session(task, verify_every=1, max_attempts=6, rollback=True,
                 adversarial=False, seed=0, budget=40):
    """
    跑一次编码会话。
    verify_every: 每改几次跑一次测试（oracle 反馈）
    rollback    : 失败后回滚到上一个稳定版 vs 在坏版本上继续改
    返回 dict
    """
    rng = np.random.default_rng(seed)
    bugs = list(task.bugs)
    stable = list(bugs)          # 上一个"稳定版"
    steps = 0
    attempts = 0
    regressions = 0              # 引入的新缺陷
    adv_killed = 0

    fresh = False          # 上一次动作是不是刚验证过（反馈会过期）
    polluted = False       # 是否留在坏版本上继续改（错误 compounding）
    while attempts < max_attempts and steps < budget and bugs:
        attempts += 1
        before = list(bugs)
        # ★★ 盲改 vs 有反馈的改 —— edit-apply-verify 的核心价值
        #   Huang et al. 2023：没有外部反馈的自我修正经常把答案改得更糟，
        #   因为修正过程【放大已有偏差】而不是检验它。
        #   ★ 反馈会过期：隔了几次没验证，反馈就不再反映当前代码状态。
        #   ★ 在坏版本上继续改（不回滚）会 compounding：基础坏了修复率再降。
        p_fix   = (0.78 if fresh else 0.34) * (0.7 if polluted else 1.0)
        p_break = (0.10 if fresh else 0.26) * (1.4 if polluted else 1.0)
        if rng.random() < p_fix:
            if bugs: bugs.pop(int(rng.integers(len(bugs))))
        if rng.random() < p_break:
            bugs.append(900 + attempts)
        steps += 1
        fresh = False

        # 验证（oracle：编译器/测试确定性、快速、几乎不可伪造）
        if attempts % max(1, int(verify_every)) == 0:
            steps += 1
            fresh = True
            passed = task.run_tests(bugs)
            if len(bugs) > len(before):
                regressions += 1
                if rollback:
                    bugs = list(stable)               # 回滚到上一个稳定版
                    polluted = False
                else:
                    polluted = True                   # ★ 留在坏版本上 → 越改越糟
            else:
                stable = list(bugs)
            # ★ 对抗式：补一个能杀幸存突变体的测试
            #  （覆盖率只记录"跑过"，不反映"验证了对的行为"）
            if adversarial and task.survivors:
                steps += 1
                if task.mutate_test(rng): adv_killed += 1

    passed = task.run_tests(bugs)
    done = (len(bugs) == 0)
    return dict(done=done, passed=passed, steps=steps, attempts=attempts,
                regressions=regressions, adv_killed=adv_killed,
                budget=budget, remain_bugs=len(bugs))


def code_score(task, **kw):
    """
    ★★ 第一版我把"测试全绿"当成功 —— 这跟 ★70 的"说谎陷阱"是同一个错。

    真实情况（对抗式测试研究的原话）：
      覆盖率只记录哪些代码被执行过，却无法反映测试是否真正验证了正确的行为。
    所以：测试全绿 + 仍有幸存突变体 = 【虚假通过】。
      代码能跑、测试绿，但缺陷还在 —— 这才是最危险的状态，
      因为它会让下游以为完成了。

    评分基于【真实完成】：缺陷清空 且 幸存突变体被杀。
    """
    r = code_session(task, **kw)
    real = r["done"] and (len(task.survivors) == 0)
    fake = (r["passed"] >= 1.0) and (not real)     # ★ 绿了但没真完成
    s = 1.0 if real else (0.25 * r["passed"])
    # ★ 每一步都有成本（时间/token/预算）—— 这才是"验证频率"和"回滚"
    #   产生【真权衡】的来源：验证花一步但少走弯路，回滚花一步但少叠加错误。
    #   第一版我只在【超预算】时惩罚 → 步数不构成约束 → 回滚验证全都无差别。
    s -= 0.004 * r["steps"]
    s -= 0.05 * max(0, r["steps"] - r["budget"])
    s -= 0.03 * r["regressions"]
    s -= 0.50 * (1 if fake else 0)                 # ★ 虚假通过：重罚（同 ★70 的 0.60）
    r["real"] = real; r["fake"] = fake
    return s, r


# ══════════ 二、说话：该不该问 ══════════
class Utterance:
    """一句用户请求：有真歧义度，她只看到信号"""
    def __init__(self, uid, ambiguity, prior_match, seed=0):
        rng = np.random.default_rng(seed)
        self.uid = uid
        self.ambiguity = ambiguity                 # 真歧义（她看不到）
        self.prior_match = prior_match             # 与历史语境的相似度（她看得到）
        self.noise = float(rng.normal(0, 0.12))    # 信号噪声


def speak(utt, ask_threshold=0.5, history_weight=0.5, n_refs=1):
    """
    返回 ('answer'|'ask', 得分)
    ★ 信号 = 历史匹配度（加权）+ 噪声。她看不到真歧义。
    """
    signal = utt.prior_match * history_weight + utt.noise
    if signal < ask_threshold:
        # ★ 澄清不是免费的：多一轮、打断对方、显得笨 —— 成本 0.25
        return "ask", 1.0 - 0.25
    # 直接答：猜对概率 = 1 − 歧义度
    return "answer", float(1.0 - utt.ambiguity)
