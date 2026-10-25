# 129 · 真实世界审计：把 evalguard 打到九个权威评测框架上

## 一句话结论

**在 9 个权威评测框架的 61 个真实源文件上，v0.3.0 的 blocker 精确率是 11%（3/27）；
修完是 17%（1/6）。我们此前"埋雷 10/10、干净 0/0"的成绩，是选择性取样造出来的。**

这不是"产品还能再优化"，是**当前形态不能卖**。

---

## 一、语料：真实抓的，不是编的

用 GitHub API 实抓（不是本地构造）：

- corpus1 = 34 个文件（第一次按路径最短取，事后证明取偏了，见第五节）
- corpus2 = 27 个**核心评测文件**（修正取样后）

来源（全部真实仓库，main 分支）：

```
EleutherAI/lm-evaluation-harness · openai/evals · openai/simple-evals
huggingface/lighteval · SWE-bench/SWE-bench · UKGovernmentBEIS/inspect_ai
allenai/olmes · stanford-crfm/helm · google/BIG-bench
```

核心语料含 `lm_eval/evaluator.py`、`openai/evals/eval.py`、
`oe_eval/run_eval.py`、`swebench/harness/grading.py`、
`bigbench/evaluate_task.py`、`src/lighteval/pipeline.py` 等**真正的评测主逻辑**。

---

## 二、结果

| 语料 | v0.3.0(修前) | 修复后 | 降幅 |
|---|---|---|---|
| corpus1（34 工具/配置文件） | 27 blocker | 9 | −67% |
| corpus2（27 核心评测文件） | 21 | **6** | **−71%** |
| fixtures（7 埋雷/干净样本） | 17 | 15 | −12% |

### 人工逐条核验（这是关键，不是看命中数）

**修前 27 条 blocker：3 真 / 24 假 = 11.1%**
**修后核心语料 6 条：1 真 / 5 假 = 16.7%**

唯一的真阳性：

```
EG002 · EleutherAI/lm-evaluation-harness :: lm_eval/evaluator.py
        报了指标，全文没有随机基线符号
```

五个假阳性：

```
EG002  inspect_ai/examples/scorer.py   示例文件
EG016  helm/scripts/heim_human_eval.py 文件级，报在 L1
EGP02  simple-evals/drop_eval.py       Hungarian 最优匹配被当成阈值调优
EGP04  BIG-bench/evaluate_task.py      文件级
EGP04  lighteval/pipeline.py           文件级
```

---

## 三、根因（27 条修前 blocker 的人工分类）

| 根因 | 条数 |
|---|---|
| **文件级启发式**（整文件关键词布尔，报在 L1，无法定位） | 11 |
| **子串匹配**（`acc`⊂`accept`、`fit`⊂`profit`、`curl`⊂`curly`） | 8 |
| **AST 语义误读**（类型注解、切片、内部容器当模型响应） | 4 |
| **标准控制流当反模式**（int→float 回退、重试、Hungarian 匹配） | 3 |
| 噪声路径未过滤（tests/、examples/） | 1 |

第一条**子串匹配**，和我们在 exp099 里诊断 TACT 引擎的病是**同一个病**。
我们拿着诊断别人的判据，在自己的产品里原样复现了一遍。

---

## 四、修了什么

1. `_has_word()`：子串 → 词边界
2. `_derives_rules()`：**要求 AST 里真有 `fit(...)` 调用**，不再靠"fit"子串
3. `EGP10`：排除类型注解上下文（`Optional[List[Text]]`）、切片（`[:-1]`），
   并要求根变量**精确**属于响应词表（`result_dict[column][k]` 不再是"模型响应"）
4. `EG006`：有注释说明 / 属于回退链 → 豁免
5. `EGP01`：**只在评分循环内**、且**handler 没留下记录**才算静默丢弃
6. `_is_noise_path()`：从"目录名含 tests/" 改成**按内容判断**
   （第一版靠目录名，把放在 tests/ 下的埋雷 fixture 一起静音了）
7. `_metric_line()`：不再固定报 L1

---

## 五、我这轮的错误（按严重度排）

### ① 语料取样偏差 —— 第一次结论根本不成立
`cands.sort(key=len(p))` 取**路径最短**的 4 个文件 → 抓到的全是
`utils.py` / `data.py` / `__init__.py` / `cli_args.py`。
**我扫的不是它们的评测脚本，是它们的工具类文件。**
第二次改成按"核心评测文件名 + 排除 utils/tests/docs"取样，才拿到真语料。

### ② 我以为修了，其实没修上（注释豁免）
`ast.get_source_segment` **丢弃行尾注释**：

```
except PermissionError as e:
    pass  # this is not a critical failure
```

拿到的 seg 是 `except PermissionError as e:\n    pass` —— **`#` 取不到**。
`"#" in seg` 静默永不成立。改用**原始行文本**才生效。
这是判据核里反复出现的那类失效：**改动看起来应用了，实际没有。**

### ③ 辅助函数插错位置，抢走了装饰器
我把 `_handler_records` 定义插到 `@prule("EGP01", ...)` **之后**，
于是装饰器装饰了辅助函数，`EGP01` 被踢出规则表，
而 `_handler_records` 被调用成 `(tree, src, path)` → 每文件崩溃一次。

### ④ cli 把规则崩溃当成 blocker 报
`except Exception: hits=[{"line":0,"hit":"rule error..."}]` 沿用规则自身的 severity。
**一条崩掉的规则，在报告里长得和真发现一模一样。**
一次跑出 27 个幽灵 blocker。已改成 `severity="info"` 并 `continue`。

### ⑤ 路径扁平化让过滤器失效
我把 `examples/scorer.py` 存成 `...__examples_scorer.py`（`/`→`_`），
于是 `"examples/" not in q`，噪声路径过滤**从未命中**。

### ⑥ A/B 测试首次跑出逐位相同的结果
模块级 `sys.modules` 污染：两次都加载了同一个 `rules`。
改成**独立子进程**跑才拿到真实差异。差点写成"修改无效果"。

---

## 六、代价：修假阳性同时杀了真阳性

| | |
|---|---|
| 埋雷 fixture 丢失真阳性 | **2**（EG006、EGP01） |
| 干净 fixture 残留假阳性 | **4**（clean_eval: EGP04/EGP05；pro_clean: EG002/EG016） |

**"干净样本零误报"这个卖点，在 PRO 规则下从来就不成立。**
我此前只测了基础规则的 clean 样本，没测 PRO 规则的 clean 样本。

---

## 七、商业判断

**v0.3.0 现在不能卖。**

在权威框架上 17% 的精确率意味着：一个真实客户拿自己的评测代码来扫，
大概率会看到一堆"报在 L1、无法定位、其实是标准写法"的 blocker。
**会乱叫的 linter 没人用**——这句话是我自己写在产品页上的。

下一步不是继续加规则，是：

1. **把文件级启发式全部改成函数级 + 行级定位**（这是 11/27 的根因）
2. **把 fixture 扩成"真实语料回归集"**：corpus2 的 27 个文件进 CI，
   每次改规则必须同时通过埋雷（不降召回）和权威语料（不升假阳性）
3. 精确率不到 60% 之前，不挂付费链接

---

## 八、边界

- **"真/假"是我的逐条人工判定**，判据写在正文里，可复核；没有第二标注者，无 κ
- corpus2 的 27 个文件是我的取样规则选的，不是全量
- 剩下那 1 条"真阳性"（lm_eval 不报基线）**可以辩护**：
  各 task 自带 baseline 是设计选择，代码里不报未必是缺陷
- 本轮未接引擎，不主张任何关于"结构"的结论

---

## 九、自检

渲染 → 写 `/dev/fb0`（ioctl 实测 1024×768×32bpp，**RGBA**）→ 回采 3,145,728 字节：

```
render sha aa13db24b2e1
capture sha aa13db24b2e1     ← 逐位一致
OCR: TOKEN AHDWNU 命中，8 行全读出
```
