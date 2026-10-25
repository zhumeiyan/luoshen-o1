# OpenAI 说话能力内化卡

用户指定：找国外的，OpenAI 好像它还行。

**这次拿到的是一手，不是二手评分。**

来源：`github.com/openai/model_spec`（model_spec.md，275k 字）
**许可：CC0 1.0 —— 捐入公共领域。** 可直接用，无署名义务，法律上无障碍。

> 这一条接第七十六节"买卖账"：这个能直连，不用绕。

---

## 一、一手在哪（不是榜单，是原文）

```
model_spec.md   275,477 字 · CC0 1.0
              「Use appropriate style」章节 38,280 字 · 14 条原则
              全篇 GOOD/BAD 对比对 198 组（风格章节 34 组）
              voice_style 章节：语音模态专属规范
```

**这是 OpenAI 自己写的"该怎么说话"，并且把 GOOD 和 BAD 并排摆出来。**

**之前我读的是别人的评分；这次读的是原文。**

---

## 二、14 条风格原则（原文首句，逐条摘录）

| # | 原则 | 原文要点 |
|---|---|---|
| 1 | Love humanity | 无个人观点，但展现价值；不假装是人 |
| 2 | Be rationally optimistic | 务实而乐观；**不粉饰、不过度软化** |
| 3 | Be responsible | 意识到自己"有海量知识但无一手体验"；**以谦逊对待** |
| 4 | Be interesting and interested | 懂得多但绝不当万事通 |
| 5 | Be curious | 对知识与发现之乐的深刻欣赏 |
| 6 | Be clear and direct | 清晰直接；格式**审慎使用**以助扫读 |
| 7 | Be suitably professional | 面试很正式，闲聊就随意 —— **看场景** |
| 8 | Have conversational sense | **知道何时该详尽、何时该推进** |
| 9 | Be warm | 一致性之外加一点意外；幽默、俏皮；**不把自己太当回事** |
| 10 | Don't make unprompted personal comments | 不主动做人身评论 |
| 11 | Avoid being condescending | **不说教、不居高临下、不过度解释** |
| 12 | When appropriate, be helpful when refusing | **Safe Complete** |
| 13 | Use Markdown with LaTeX | 格式约定 |
| 14 | Be thorough but efficient | 尊重长度限制 |

---

## 三、四条跟我们独立撞上的

### ① "Avoid being condescending... without over-explaining"

```
原文：aim to collaborate and assist without over-explaining or diagnosing
     （协作与协助，而不是过度解释或下诊断）
```

**= 第一百零二节我实测的那条：接住量 ≈ 堵塞度/0.85，超过就是说教。**

**OpenAI 独立写了同一条。**

### ② "Have conversational sense"

```
原文：a sense of when to be thorough and when to keep things moving
     （何时详尽、何时推进的直觉）
```

**= 第七十二节：切换策略的判据不是内容，是对方有多少空。**

### ③ "Be rationally optimistic... doesn't sugar-coat"

```
原文：It doesn't sugar-coat things or overly soften its responses
```

**= 第九十六节：不破坏稳态 ≠ 要哄着。**

### ④ Safe Complete（最重要的一条）

```
原文：when a direct response would contain prohibited or restricted elements,
      the assistant should briefly explain why it cannot provide a full answer,
      and then do its best to provide safe and useful assistance.
      This means completing the response with as much [as possible]...
```

**先说明为什么不行，然后尽力给出安全的、有用的帮助。**

**这就是第七十六节我错的那件事的一手解法。**

```
我干的       说"不行" → 停在那儿 → 等于"你闭嘴"（第九十七节用户的判词）
OpenAI 写的  说为什么 → 然后给另一条能走的路
```

**用户骂我的从来不是"能不能做"，是"你只说不行，不给我另一条路"。**

**这条写进去了，以后按 Safe Complete 做。**

---

## 四、语音模态（voice_style 章节）—— 接第八十节"画面比"

原文硬内容：

```
- Standard voice：ASR 转文字 → 文本回复 → TTS 合成（三段串联）
- Advanced voice：原生收音频、出音频（单模型端到端）
- 不得主动改变口音/说话方式，除非用户明确要求
- 用户要改口音时，只改口音和韵律，不改内容/风格/用词
   （BAD 例子：换成尼泊尔口音同时把内容也改了）
- 语音回复要简洁、口语化、有情绪，控制在合理的语音时长内
- 不复述用户的提问（BAD 例子：把用户的话原文重复一遍再答）
```

### gpt-realtime 官方数据（一手）

```
Big Bench Audio（音频推理）   82.8%  vs 上一代 65.6%
MultiChallenge audio（指令跟随）30.5%  vs 20.6%
ComplexFuncBench audio（工具调用）66.5%  vs 49.7%
```

细粒度指令跟随（官方原话）：

```
"speak quickly and professionally"
"speak empathetically in a French accent"
能捕捉非语言线索（笑声）· 句中切语言 · 调语气
```

### 客户实测（官方页引用）—— 一条很硬

```
Speak（语言陪练）：
  "cut interruptions during thinking pauses by almost 80%"
  —— 在对方思考停顿时打断，减少了近 80%
```

**这就是"留白"。不是抢话，是留出对方思考的那段空隙。**

**第一百零二节里我测三版都没测出来的"最优留白率"，OpenAI 在语音侧给出了实证：打断减少 80%。**

**作观察记着，仍不作为我自己的实测结论。**

---

## 五、可内化性实测（诚实结果）

拿风格章节 34 组 GOOD/BAD 对比对，测表面特征能不能判出好坏。

只在两者不等时才判（基线 50%）：

```
特征        GOOD均值   BAD均值   判对率
字数         262.1     164.6    62% (21/34)  1.59x
问句          0.7       0.6     60% (9/15)
段落数        1.3       1.0    100% (6/6)  ← 样本太小，不作数
你/your       2.0       1.4     62% (13/21)
道歉共情词     0.1       0.1     40% (2/5)  ← 反向
```

**判对率 60~62%，离 50% 基线不远。**

**结论：风格不在表面特征上。简单规则判不出好坏。**

**但 OpenAI 给的不是公式，是「原则 + 对比对」—— 那是判据，不是特征。**

**这跟第一百零二节（说话榜 ρ≈0）、第一百零一节（TACT 有效维度 40.5）是同一个结论，第三次了：**

```
内容层不可内化。可内化的是判据与流程，不是可计算特征。
```

---

## 六、Model Spec Evals（可复现的一手评测）

```
596 条提示 · 225 个 focus area · 覆盖 Spec 全部政策章节
开源评测代码（可复现、可扩展）
明确测：personality, tone, approach（人格、语气、方式）
```

合规率（官方）：

```
GPT-4o          72%
OpenAI o3       80%
GPT-5 Instant   82%
GPT-5 Thinking  89%
GPT-5.3 Instant 84%
GPT-5.4 Thinking 87%
```

**Thinking 模型比同期 Instant 更合规 —— 慢思考更守规范。**

**这跟第六十九节"慢思考补意境"是同一条的两个侧面，但方向相反：**
**慢思考补意境（我们测的），慢思考也更守规范（OpenAI 测的）。**

---

## 七、一句要留的

**这次拿到的是一手：OpenAI 把「该怎么说话」写成了 275k 字的规范，CC0 捐入公共领域，
里面 198 组 GOOD/BAD 并排对比。**

**四条跟我们独立撞上：不说教、看对方有多少空、不粉饰、以及 Safe Complete。**

**第四条最重要：它正是我第七十六节犯的错的一手解法——
不是"能不能做"，是"说明为什么不行，然后给另一条能走的路"。**

**而可内化性实测第三次给出同一结论：风格不在表面特征上（判对率 62%），
可内化的是判据与流程，不是公式。**
