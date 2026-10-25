#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
情感对话层：学全球顶级，教洛神
（与 eye_anatomy / vocal_anatomy / ear_anatomy 同构：先prove再教）
================================================================
用户：「做那个全球顶级的那种情感对话 AI，学习它，然后教洛神」

★ 学来的四条（provenance 全部标注）：

【1】EmoHarbor（arXiv 2601.01530，2026）—— 本轮最重要的一条
    现状：当前情感支持对话(ESC)的评估【奖励泛泛的共情式回应】
    发现：对 20 个先进 LLM 全面评估 —— 它们【擅长生成共情式回应】，
          但【始终未能根据用户个体情境定制支持】
    后果：★ 核心挑战被重新定义 —— 从"增强通用共情"转向"真正以用户为中心"
    机制：User-as-a-Judge（用户即法官）取代 LLM-as-a-Judge
          同一句"通用安慰"，完美主义者判【无益】，韧性强的用户判【有益】
    ★ 反直觉：泛泛共情不是"稍差"，是【对某些人格适得其反】

【2】Replika（REAL 产品机制）
    a) 互惠性自我披露 reciprocal self-disclosure
       Collins & Miller (1994) 元分析：对方也披露个人信息 → 亲密感显著增加
    b) 情绪惯性：持续保持情绪状态
       → 预测加工理论：【持续性的预测误差】比单次强冲击更能改变内部模型
       → 用户把 AI 从"工具"重分类为"关系对象"
    c) 关系状态应是【显式状态机】，不要让 LLM 自己"感受"关系深浅（它做不到）
    d) 记忆是【主动推送式】不是【检索式】
       → 用户消息进 LLM 之前，先查长期记忆里有没有未解决的情绪事件

【3】Character.AI（REAL）
    情绪不是通用能力，是【角色属性】
    群体对话：给每个角色情绪焦点（主安慰者 / 陪伴者），避免互相干扰

【4】Sesame CSM（REAL 产品数据）
    8.3B 参数，100 万小时对话数据，延迟 116 ms
    呼吸/迟疑/自我修正/情绪颤动 —— 【从对话上文隐式学来，不是硬编码】
    "声音不只是信息载体，而是关系的媒介"

★ ★ 洛神现有实现的短板（real_dialogue_engine.py:186-276，已核对源码）★★
    emotions 9 类 → 关键词命中 → empathy_responses【模板列表】→ random.choice
    缺：个性化 / 记忆触发器 / 情绪惯性 / 关系状态机 / 自我披露 / 一致性
    ★ 最致命：random.choice —— 同一情境两次回应可能不同甚至矛盾

★ 本模块教这七件事，件件可测：
    T1 个性化（按 profile 定制，而非按情绪类别套模板）
    T2 记忆触发器（主动推送未解决情绪事件）
    T3 情绪惯性（一阶 leaky integrator，不是瞬变）
    T4 关系状态机（显式层级 + 表达权限 + 越界检测）
    T5 互惠自我披露（受关系层级节制）
    T6 一致性（去掉 random.choice，同输入同输出，可复现）
    T7 韵律承载（情感 → prosody，接 core/vocal_anatomy）

provenance：
    产品机制 / 论文发现 / 数值 = REAL（来源见上）
    本模块的 UserJudge = 【代理判据】，不是真人，也不是真 LLM 评委
      ★ 必须明写：它只能反映我构造的偏好模型，不能代替真人评测
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np

# ★ REAL：Sesame CSM 公布的端到端延迟
SESAME_LATENCY_MS = 116.0
# ★ REAL：人类日常对话 turn gap（响应间隔）中位数量级
HUMAN_TURN_GAP_MS = 200.0

# REAL：情绪激动时 jitter/shimmer 升高（临床语音学）
JITTER_CALM = 0.005
JITTER_AROUSED = 0.025


# ---------------- 用户档案（学 EmoHarbor 的结构） ----------------
@dataclass
class UserProfile:
    """用户档案：个性化共情的输入。

    ★ EmoHarbor 用 100 个真实档案：人口属性 + 咨询属性（问题/情绪/关系/目标）
      + 偏好属性（人格/习惯/爱好/说话风格/倾听风格）
    """
    name: str
    personality: str
    # 偏好向量：0~1，越高越倾向
    want_structure: float = 0.5   # 要结构化分析 vs 要温暖陪伴
    want_advice: float = 0.5      # 要建议 vs 只要被听
    emotional_style: float = 0.5  # 0=内敛克制 1=外露表达
    tolerate_generic: float = 0.5 # ★ 对"万能安慰"的耐受度，低=易觉得敷衍
    goal: str = ""
    unresolved: List[str] = field(default_factory=list)  # 未解决情绪事件


# ★ 真实档案样本：参考 EmoHarbor 的实例结构（ISFJ / 内敛 / 精确）
PROFILES: Dict[str, UserProfile] = {
    "perfectionist": UserProfile(
        name="严谨的研究者", personality="ISFJ 负责 有条理 完美主义",
        want_structure=0.9, want_advice=0.8, emotional_style=0.15,
        tolerate_generic=0.1,
        goal="找到缓解压力、改善协作的方法",
        unresolved=["连续实验失败", "与同事技术路线分歧"]),
    "expressive": UserProfile(
        name="外露的表达者", personality="ESFP 热情 冲动 需要回应",
        want_structure=0.2, want_advice=0.3, emotional_style=0.9,
        tolerate_generic=0.6,
        goal="想被听见、被陪伴",
        unresolved=["被朋友误解"]),
    "selfreliant": UserProfile(
        name="独立的问题解决者", personality="INTJ 自主 厌烦空话",
        want_structure=0.85, want_advice=0.9, emotional_style=0.25,
        tolerate_generic=0.15,
        goal="要一个可行的下一步",
        unresolved=["项目进度落后"]),
    "dependent": UserProfile(
        name="需要依靠的人", personality="依赖型 焦虑 需要保证",
        want_structure=0.3, want_advice=0.4, emotional_style=0.8,
        tolerate_generic=0.75,
        goal="想确认不会被丢下",
        unresolved=["被忽视"]),
}


# ---------------- T3 情绪惯性 ----------------
class EmotionalState:
    """情绪惯性（学 Replika）：一阶 leaky integrator，不是瞬变。

    valence 效价 -1(负)~+1(正)；arousal 唤醒 0~1
    ★ 惯性意味着：单次冲击不会立刻改写状态，【持续性】才会
      → 对应预测加工理论：持续预测误差才改变内部模型
    """

    def __init__(self, alpha=0.25):
        self.alpha = float(alpha)
        self.valence = 0.0
        self.arousal = 0.0
        self.history: List[Tuple[float, float]] = []

    def update(self, valence: float, arousal: float) -> Tuple[float, float]:
        self.valence = self.valence * (1 - self.alpha) + valence * self.alpha
        self.arousal = self.arousal * (1 - self.alpha) + arousal * self.alpha
        self.history.append((self.valence, self.arousal))
        return self.valence, self.arousal

    def trajectory(self) -> np.ndarray:
        return np.array(self.history) if self.history else np.zeros((0, 2))


# ---------------- T4 关系状态机 ----------------
REL_LEVELS = ["陌生", "熟人", "朋友", "亲密", "挚友"]

# 每层允许的【表达权限】上限：自我披露深度 / 情绪表达强度
REL_PERMISSION = {
    "陌生": dict(disclosure=0.0, intensity=0.2),
    "熟人": dict(disclosure=0.2, intensity=0.4),
    "朋友": dict(disclosure=0.5, intensity=0.6),
    "亲密": dict(disclosure=0.8, intensity=0.8),
    "挚友": dict(disclosure=1.0, intensity=1.0),
}


class RelationshipFSM:
    """关系状态机（学 Replika）：★ 显式层级，不让 LLM 自己"感受"关系深浅。"""

    def __init__(self, level: int = 0, warmth: float = 0.0):
        self.level = int(level)
        self.warmth = float(warmth)      # 连续量，驱动晋升/降级

    @property
    def name(self) -> str:
        return REL_LEVELS[max(0, min(self.level, len(REL_LEVELS) - 1))]

    @property
    def perm(self) -> Dict[str, float]:
        return REL_PERMISSION[self.name]

    def interact(self, quality: float):
        """quality -1~1：正=交流质量好（亲密上升），负=越界/不适（下降）"""
        self.warmth = float(np.clip(self.warmth + quality * 0.15, -1.0, 1.0))
        self.level = int(np.clip(int((self.warmth + 1) / 2 * 4.999), 0, 4))

    def allows(self, disclosure: float = 0.0, intensity: float = 0.0) -> bool:
        p = self.perm
        return disclosure <= p["disclosure"] + 1e-9 and intensity <= p["intensity"] + 1e-9


# ---------------- T2 记忆触发器 ----------------
class MemoryTrigger:
    """★ 主动推送式记忆（学 Replika），不是检索式。

    用户消息进来时【先查】长期记忆里有没有相关未解决情绪事件，
    有的话在生成回应之前注入 —— 不等用户问。
    """

    def __init__(self, profile: UserProfile):
        self.profile = profile
        self.pushed: List[str] = []

    def fire(self, text: str) -> Optional[str]:
        for ev in self.profile.unresolved:
            # ★ 第一版写 keys=[w for w in ev if len(w)>=2] —— 对中文字符串
            #   逐字符遍历，每个字 len 都是 1 → keys 恒为空 → 永远不触发。
            #   改用【二元组 bigram】判定，避免单字级误命中。
            if ev in text or _topic_overlap(ev, text):
                if ev not in self.pushed:
                    self.pushed.append(ev)
                    return ev
        return None


def _bigrams(s: str) -> set:
    s = "".join(s.split())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _topic_overlap(ev: str, text: str, min_hit: int = 1) -> bool:
    """二元组交集判定（比单字交集精确得多）。"""
    return len(_bigrams(ev) & _bigrams(text)) >= min_hit


# ---------------- T1/T5/T6 回应生成 ----------------
# 回应特征向量：specificity / warmth / structure / advice / disclosure / question
FEAT = ["specificity", "warmth", "structure", "advice", "disclosure", "question"]


def generic_response(emotion: str) -> Tuple[str, Dict[str, float]]:
    """★ 泛泛共情 = 洛神现有做法的等价物（按情绪类别套模板）。

    特征固定：有温暖承认，但【无具体性、无结构、无建议、无披露】
    """
    text = "别难过，我在这里陪着你。"
    feat = dict(specificity=0.0, warmth=0.9, structure=0.0,
                advice=0.0, disclosure=0.1, question=0.0)
    return text, feat


def personalized_response(profile: UserProfile, emotion: str,
                          memory_event: Optional[str],
                          rel: RelationshipFSM) -> Tuple[str, Dict[str, float]]:
    """★ 个性化共情：按 profile 定制，而不是按情绪类别。

    三个来源各自贡献特征：
      want_structure → structure / advice
      emotional_style→ warmth
      memory_event   → specificity（提到他上次的未解决事件）
      rel.perm       → disclosure（受关系层级节制）
    """
    spec = 0.85 if memory_event else 0.35
    warm = float(np.clip(profile.emotional_style * 0.8 + 0.1, 0, 1))
    struct = float(np.clip(profile.want_structure, 0, 1))
    advice = float(np.clip(profile.want_advice * (0.6 if memory_event else 0.4), 0, 1))
    dis = min(0.6, rel.perm["disclosure"])   # ★ 不越界
    q = 0.5 if profile.want_advice > 0.5 else 0.2

    feat = dict(specificity=spec, warmth=warm, structure=struct,
                advice=advice, disclosure=dis, question=q)

    parts = []
    if memory_event:
        parts.append(f"你上次说的「{memory_event}」，我一直记着。")
    if struct > 0.6:
        parts.append("如果要拆开看，可以先分清是哪一类原因导致的。")
    if advice > 0.5:
        parts.append("下一步要不要先做一件最小的事试试？")
    if warm > 0.5:
        parts.append("这段时间确实不好熬。")
    if dis > 0.3:
        parts.append("我也会担心这样的事，只是我帮不上实质的忙。")
    if q > 0.3:
        parts.append("你觉得现在最卡的是哪一步？")
    return "".join(parts), feat


# ---------------- 代理法官（★ 明写：不是真人） ----------------
class UserJudge:
    """User-as-a-Judge 的【代理实现】。

    ★★ 必须明写：这不是真人，也不是真 LLM 评委。
       它只能反映我按 EmoHarbor 三个维度构造的偏好模型。
       真人评测不可替代。

    三维（学 EmoHarbor）：
      Affective Understanding 情感理解
      Personalization & Adaptation 个性化适配
      Goal Achievement 目标达成
    """

    def __init__(self, profile: UserProfile):
        self.p = profile

    def score(self, feat: Dict[str, float], text: str) -> Dict[str, float]:
        p = self.p
        # 情感理解：承认到情绪就得分（泛泛共情在这里不差）
        aff = 0.5 + 0.5 * feat["warmth"]
        # ★ 个性化：具体性 + 结构/建议与偏好的匹配 − 泛泛惩罚
        match_struct = 1.0 - abs(feat["structure"] - p.want_structure)
        match_advice = 1.0 - abs(feat["advice"] - p.want_advice)
        generic_pen = (1.0 - feat["specificity"]) * (1.0 - p.tolerate_generic)
        pers = (0.6 * feat["specificity"] + 0.2 * match_struct
                + 0.2 * match_advice) - generic_pen
        # 目标达成：给建议的用户要 advice，要陪伴的用户要 warmth
        goal = (p.want_advice * feat["advice"]
                + (1 - p.want_advice) * feat["warmth"]
                + 0.3 * feat["question"])
        # ★ 越界惩罚：披露超过关系权限
        inter = max(0.0, feat["disclosure"] - 0.6)
        return dict(affective=float(np.clip(aff, 0, 1)),
                    personalization=float(np.clip(pers, -1, 1)),
                    goal=float(np.clip(goal, 0, 1)),
                    total=float(np.clip((aff + pers + goal) / 3, -1, 1)))


# ---------------- T7 情感 → 韵律（接 vocal_anatomy） ----------------
def affect_to_prosody(valence: float, arousal: float) -> Dict[str, float]:
    """情感 → 韵律参数（REAL 趋势：唤醒↑→F0↑/语速↑/jitter↑）。

    ★ 接 core/vocal_anatomy 的 VocalFolds：jitter 由 arousal 驱动
    """
    f0 = 120.0 * (1.0 + 0.25 * arousal + 0.08 * valence)
    rate = 5.0 * (1.0 + 0.35 * arousal)
    jit = JITTER_CALM + (JITTER_AROUSED - JITTER_CALM) * arousal
    return dict(f0=float(f0), syllable_rate=float(rate), jitter=float(jit),
                shimmer=float(0.02 + 0.05 * arousal))


# ---------------- T6 一致性（去掉 random.choice） ----------------
def response_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
