# exp135 预注册（写在测量之前）

## 背景
exp134 在独立语料 corpus3（7 仓库 / 10 文件）上发现：
    语法层   EG005 EG006 EGP01    15/16 严格 TP = 93.8%
    方法论层 其余全部              1/29 严格 TP =  3.4%
**但这个分层也是看到数据之后才做的**（exp134 报告里已声明）。
所以它没有资格直接作为发货依据，必须在**第三个、从未参与任何调优的语料**上确认。

corpus1（61 文件 / 9 仓库）= 129~133 所有 bug 修复的来源，已污染。
corpus2 = 同 9 仓库的留出文件，共享仓库级污染。
corpus3 = 7 个新仓库，但已被 134 测量过 → 对"确认分层"而言它不再是独立语料。
corpus4 = **7 个从未用过的仓库，12 个文件**，本轮首次测量。

## corpus4 清单（写入 manifest4.json，先定后取）
truera/trulens            src/core/trulens/core/utils/evaluator.py
truera/trulens            src/trulens_eval/trulens_eval/feedback/groundtruth.py
lm-sys/FastChat           fastchat/llm_judge/common.py
lm-sys/FastChat           fastchat/llm_judge/gen_judgment.py
huggingface/evaluate      src/evaluate/evaluator/base.py
huggingface/evaluate      metrics/accuracy/accuracy.py
evidentlyai/evidently     src/evidently/legacy/base_metric.py
deepset-ai/haystack       haystack/evaluation/eval_run_result.py
deepset-ai/haystack       haystack/components/evaluators/document_recall.py
Arize-ai/phoenix          packages/phoenix-evals/src/phoenix/evals/evaluators.py
microsoft/promptbench     promptbench/metrics/eval.py
microsoft/promptbench     promptbench/prompteval/methods.py

## 判据（预注册，不随结果改）
G1 召回：语法层埋雷夹具 EG005 3/3、EG006 2/2、EGP01 1/1；干净文件 0 发现。
G2 规则崩溃 = 0。
G3 发货闸：语法层在 corpus4 上的**严格** TP 率 >= 60%。
G4 对照闸：方法论层在 corpus4 上的严格 TP 率 <= 20%。
G5 EGP04 若在 corpus4 上命中 n>=3，则按其实测精度决定是否进入发货集。

## 预测（写出来，跑完对质）
H1: 语法层严格 TP >= 60%       → 若否，exp134 的分层是语料特异的，不能作为发货依据
H2: 方法论层严格 TP <= 20%     → 若否，说明方法论层在某些语料上可售，需重新分层
H3: 语法层的失败模式应集中在"分母是路径拼接 / docstring 里的代码"等已知伪影

## 判定规则（沿用 exp131 起的约定）
- 严格 TP：评审者打开所钉的那一行，能看出规则指控的东西。
- 存疑一律记 FP（保守方向）。
- 判定者只有我一个 → 必须在报告中声明。

## 决定规则（先写好，防止事后改口径）
- G3 过 → 交付 v0.5.0（仅语法层：EG005 / EG006 / EGP01），挂付费链接。
- G3 不过 → 不发货，继续找原因，不得改用宽松标准放行。
  （exp131 已证明宽松标准正是让 v0.3.0 以 11% 精度上架的那把尺子。）
