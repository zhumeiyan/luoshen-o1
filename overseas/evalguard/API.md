# evalguard · 接口文档

三种接入方式，按你有多少时间排列。全部零依赖（仅 Python 标准库 + numpy 可选），
不联网、不调用任何 LLM、不执行被扫描的代码——只做 AST 解析。

---

## 0 · 三十秒：命令行

```bash
python3 -m evalguard eval.py                    # 扫一个文件
python3 -m evalguard evals/ tests/              # 扫目录
python3 -m evalguard . --format sarif > r.sarif # 输出 SARIF
python3 -m evalguard . --report out.html        # 输出 HTML 报告
python3 -m evalguard serve                      # 起本地 HTTP API
```

退出码：`1` 表示存在 blocker，`0` 表示没有。这是 CI 的唯一判据。

---

## 1 · Python API

```python
from evalguard import scan_source, scan_file, scan_paths

# 扫内存里的代码（不用落盘）
r = scan_source(source_code_string, path="eval.py")

# 扫文件 / 目录
r = scan_paths(["evals/", "tests/"])

r.ok            # True = 没有 blocker，CI 判据
r.counts        # {'blocker': 0, 'warn': 2, 'info': 1}
r.blockers      #  blocker 级发现列表
r.findings      #  全部发现
r.audits        #  门控自身的记账（不是发现，单独存放）
r.to_text()     #  人读
r.to_json()     #  机读
r.to_sarif()    #  SARIF 2.1.0
```

`Finding` 字段：`eg_id / severity / title / file / line / hit / why / fix / canon /
scope / kind`。

**`line` 允许为 `None`**，这不是缺失值。声明为 `absent` 类的规则指控的是"某个东西
不存在"（从来没有 baseline、从来没有 held-out set），而不存在的事物没有行号可以
展示。exp133 实测：强行给这类发现安一个行号，真值率 0/9。所以 `None` 是诚实的
答案，`scope == "file"` 会说明这一点。

### 从 Agent 里调用（生成代码后、写入磁盘前）

```python
from evalguard import scan_source

def safe_write(code, path):
    r = scan_source(code, path=path)
    if not r.ok:
        raise RuntimeError("refusing to write code that can lie:\n" + r.to_text())
    open(path, "w").write(code)
```

---

## 2 · HTTP API

```bash
python3 -m evalguard serve            # http://127.0.0.1:8787
```

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 存活 + 规则数 |
| GET | `/rules` | 规则目录（26 条，含 shipped 标记） |
| POST | `/scan` | body `{source\|path\|paths, pro?, severity?}` |
| POST | `/scan/sarif` | 同上，返回 SARIF 2.1.0 |

```bash
curl -s localhost:8787/scan -H 'Content-Type: application/json' \
  -d '{"source":"acc=1/0\n","path":"x.py"}'
```

设计约束，说清楚：**这是本地服务**。默认只绑 `127.0.0.1`，请求体上限 4 MiB，
只接受 `/scan*`，且**从不执行**交给它的代码（只解析成 AST 后读取）。
它未针对公网暴露做加固，`--host 0.0.0.0` 的帮助文本里写了这一点。

---

## 3 · 仓库接口（把 evalguard 接进你自己的仓库）

### 3.1 GitHub Action — 发现直接出现在 PR diff 上

```yaml
- uses: zhumeiyan/luoshen-o1/overseas/evalguard@main
  with:
    paths: "evals tests"
    severity: warn
    fail-on: blocker      # 存量仓库先用 "none" 观察
```

输出：`blockers` / `warns` / `findings` / `sarif-file`。
完整 workflow（含 SARIF 上传）见 `examples/ci.yml`，需要 `security-events: write`。

**为什么要上传 SARIF**：CI 的 job log 在另一个页面，而 diff 是开发者已经在看的地方。
告警不出现在他眼睛所在的位置，就等于没有告警。

### 3.2 pre-commit — 在写下的那一刻拦住

见 `examples/pre-commit-config.yaml`。建议只对 `evals|tests|benchmarks|experiments`
路径生效：关于 baseline 和 held-out set 的规则，放在应用代码里是噪声。

### 3.3 与 CI 集成的最小判据

```bash
python3 -m evalguard evals/ --severity blocker && echo "ok to ship"
```

---

## 4 · 26 条规则与出货策略

规则分两类，这是 exp134 在 7 个从未参与开发的仓库上测出来的，不是设计偏好：

| 类别 | 严格真值率 | 是否出货 |
|---|---|---|
| **语法类**（EG005 EG006 EGP01） | 15/16 = **93.8%** | ✅ 出货 |
| **方法论类**（其余） | 1/29 = **3.4%** | ❌ 不出货 |

方法论规则的指控在真实代码上往往是**字面真、实际假**——它们大量命中指标库与框架
管道，而被指控的对象（baseline、held-out set）在那里根本不存在。

**所以默认只跑 3 条。** 其余 23 条保留在 `--pro` 与研究模式下，不进入出货门。
这是本工具与"规则越多越好"的 linter 的根本分歧点：一条 3.4% 真值的规则，
不是 3.4% 的帮手，是 96.6% 的噪声——而噪声会训练你忽略告警。

查询某条规则是否出货：`GET /rules` 里的 `shipped` 字段。

---

## 5 · 与 ruff 的关系（实测，不是定位声明）

同样 5 个最小样例，`ruff 0.17.1 --select ALL` vs evalguard 默认集：

| | ruff `--select ALL` | evalguard（默认） |
|---|---|---|
| 命中总数 | **42** | **6** |
| 与"评测静默出错"实质相关 | **约 3** | **6** |

ruff 的 42 条落在：缺类型注解 7、隐式命名空间包 5、缺版权声明 5、缺返回类型 5、
未文档化函数 10、import 未排序 3、print 1……**这些是代码规范，不是结论可信度。**

两处重叠，且分歧比重叠更有信息量：

- `BLE001` + `S110` + `SIM105` 都指向同一行 `except Exception: pass`。
  ruff 说的是类型太宽、建议改用 `contextlib.suppress`——**这个修复方向与我们相反**：
  `suppress` 让吞掉异常变得更安静、更体面。同一行代码，ruff 想让它更优雅，
  evalguard 判它为 blocker，因为它吞掉的是本该上报表面的失败。
- `S311`（伪随机数）在 `s1.py` 上是**误报**：那里用 `random` 是实验随机性，
  不是密码学用途。

**结论：你该用 ruff。我们跑在它旁边。** ruff 管"代码好不好看"，evalguard 管
"这个结论是不是静默错的"。两者交集只有一行。

---

## 6 · 已知边界

- **只做静态分析**。不能发现"baseline 数字算错了"，只能发现"根本没有 baseline"。
- **只覆盖 Python。**
- **方法论规则不出货**（见第 4 节）。这意味着本工具**不会**告诉你"你没做
  held-out split"——除非你开 `--pro` 并自己承担 3.4% 的真值率。
- **注释豁免需要语义**（exp138）：任意 `#` 不再豁免，注释必须真的声称静默是安全的
  （`safe / intentional / fallback / not critical / 可忽略` 等）。否则"写个注释就能
  关掉告警"等于给 linter 装了一个不需要理由的开关。
