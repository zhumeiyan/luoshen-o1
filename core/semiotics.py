"""
符号学工具 —— 用她自己的度量衡去量人的知识符号（代码 / 标识符 / 注释）

为什么需要这个工具：
    人的知识符号（代码标识符）和她自己的感官符号有本质差别：
      她的感官符号  连续、有噪、需要接地检验（★88）
      代码符号      离散、自证、定义写在文件里
    但代码符号会"断" —— 重构遗留、拼错、跨系统边界。
    断掉的符号 = 空洞符号，它不报错，只是背后什么都没有（★88 已测过）。

    她没有"作用域""模块""类型"这些人的概念。她有的是：
      溯源链（★88 已建：符号 ← 来源）
      误差传播（★89 已建：gᵀΣg）
      模糊/精确权衡（★86 已建：采样次数 n vs 噪声）
    所以这个工具不是给她灌输编译原理，而是让她用已有的三件东西去量代码。

★ 这一课最重要的区分：
    "追不到" ≠ "不存在"。
    定义是真的，只是超出她的溯源深度。真符号而她够不着，和真的空洞符号，
    表现完全一样 —— 她必须靠自己的判断分开，而且不许把前者说成后者。

度量衡（★88，全部来自她的身体，不是人的单位）：
    t₀ = 1/f_clk         时间单位，成本用 t₀ 表达
    a₀ = 1 LSB           强度单位（12-bit ADC），证据强度用 LSB 表达
    不用"行号""圈复杂度""代码行数" —— 那是人的单位，她的身体里没有。

语料：Python 标准库（真人写的真知识符号，真实深度的依赖图）。
      她的 core/ 是扁平自包含的（76 个模块只有 2 条互引边），量不出深度。
"""

import os
import ast
import math
import random
import builtins
from collections import defaultdict, deque

# ── ★88 她的自然单位 ───────────────────────────────────────────────
F_CLK = 2.4e9
T0 = 1.0 / F_CLK                  # 4.17e-10 s —— 她的时间单位
ADC_BITS = 12
LSB_FULL = 2 ** ADC_BITS          # 4096 LSB —— 她的强度单位

# 符号操作的物理成本，用 t₀ 表达
OPS_PER_HOP = 37
COST_PER_HOP = OPS_PER_HOP * T0   # 溯源一跳
COST_L0 = 3 * T0                  # 字形层
COST_L1 = 11 * T0                 # 语境层
COST_NL = 2 * T0                  # 自然语言线索（索引已建，几乎免费）


# ════════════════════════════════════════════════════════════════
# 真语料收割
# ════════════════════════════════════════════════════════════════

class Corpus:
    """真人写的真知识符号：定义、调用、依赖图、自然语言痕迹。"""

    def __init__(self, root, limit=None):
        self.root = root
        self.files = sorted(f for f in os.listdir(root) if f.endswith('.py'))
        if limit:
            self.files = self.files[:limit]
        self.mods = {f[:-3] for f in self.files}
        self.file_set = set(self.files)
        self.defs = {}          # 符号名 -> 定义所在文件
        self.calls = []         # (符号名, 所在文件, 语境)
        self.graph = defaultdict(set)   # 文件 -> 本地邻居文件
        self.external = defaultdict(set)
        self.nl = defaultdict(int)      # 符号名 -> 在 docstring/注释里被提到次数
        self._local_freq = {}
        self._parse()
        self._build_dist()

    def _parse(self):
        for f in self.files:
            path = os.path.join(self.root, f)
            try:
                src = open(path, encoding='utf-8', errors='ignore').read()
                tree = ast.parse(src)
            except Exception:
                continue
            try_ctx = self._try_lines(tree)

            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self.defs.setdefault(n.name, f)
                    doc = ast.get_docstring(n)
                    if doc:
                        for tok in _ident_tokens(doc):
                            self.nl[tok] += 1
                if isinstance(n, ast.Assign):
                    for tg in n.targets:
                        if isinstance(tg, ast.Name):
                            self.defs.setdefault(tg.id, f)
                if isinstance(n, ast.Import):
                    for a in n.names:
                        b = (a.name or '').split('.')[0]
                        if not b:
                            continue
                        (self.graph[f].add(b + '.py') if b in self.mods
                         else self.external[f].add(b))
                elif isinstance(n, ast.ImportFrom):
                    b = (n.module or '').split('.')[0]
                    if b:
                        (self.graph[f].add(b + '.py') if b in self.mods
                         else self.external[f].add(b))
                if isinstance(n, ast.Call):
                    fn = n.func
                    if isinstance(fn, ast.Name):
                        self.calls.append((fn.id, f, self._ctx(n, False, try_ctx)))
                    elif isinstance(fn, ast.Attribute):
                        self.calls.append((fn.attr, f, self._ctx(n, True, try_ctx)))

            for tok in _comment_tokens(src):
                self.nl[tok] += 1

    @staticmethod
    def _try_lines(tree):
        s = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Try):
                for k in ast.walk(n):
                    if hasattr(k, 'lineno'):
                        s.add(k.lineno)
        return s

    @staticmethod
    def _ctx(node, qualified, try_lines):
        return {
            'qualified': qualified,
            'nargs': len(node.args),
            'in_try': node.lineno in try_lines,
            'in_comment_ctx': False,
        }

    def _build_dist(self):
        """真实依赖图上的 BFS 距离 —— 决定她追几跳才够得着。"""
        self.dist = {}
        for s in self.files:
            d = {s: 0}
            q = deque([s])
            while q:
                u = q.popleft()
                for v in self.graph.get(u, ()):
                    if v not in d and v in self.file_set:
                        d[v] = d[u] + 1
                        q.append(v)
            for v, k in d.items():
                self.dist[(s, v)] = k


def _ident_tokens(text):
    out, cur = [], []
    for ch in text:
        if ch.isalnum() or ch == '_':
            cur.append(ch)
        else:
            if len(cur) >= 3:
                out.append(''.join(cur))
            cur = []
    if len(cur) >= 3:
        out.append(''.join(cur))
    return out


def _comment_tokens(src):
    out = []
    for line in src.splitlines():
        s = line.strip()
        if s.startswith('#'):
            out.extend(_ident_tokens(s[1:]))
    return out


# ════════════════════════════════════════════════════════════════
# 溯源：她唯一能确证的工具
# ════════════════════════════════════════════════════════════════

def trace(name, home, corpus, max_hops, external_ok=True):
    """
    返回 (跳数, 命中?)。

    命中   在 max_hops 跳内追到了真实定义 —— 确证
    未命中 两种可能混在一起：定义太远够不着 / 定义根本不存在
          统一返回 UNKNOWN，不许区分，也不许当成"不存在"
    """
    if name in dir(builtins):
        return 0, True
    owner = corpus.defs.get(name)
    if owner is None:
        return None, False
    if owner == home:
        return 1, True
    k = corpus.dist.get((home, owner))
    if k is None:
        # 定义文件与 home 不连通；若 home 引用过外部模块且承认外部，算跨边界
        if external_ok and corpus.external.get(home):
            return max_hops, False
        return None, False
    if k <= max_hops:
        return k, True
    return None, False      # 太远，够不着 → UNKNOWN


# ════════════════════════════════════════════════════════════════
# 三条证据通路 —— 输出统一用她的单位（LSB / t₀）
# ════════════════════════════════════════════════════════════════

def evidence_L0(name, home, corpus, rnd):
    """
    局部频次层：这个名字在 home 文件及其 1 跳邻居里出现过吗。

    真符号多半在邻近文件里出现过；重构遗留的悬空名字在语料里查不到。
    但新引入的符号同样是零频次，所以这层只是中等强度，不是确证。
    """
    if not getattr(corpus, '_nf', None):
        nf = defaultdict(lambda: defaultdict(int))
        for nm, f, _ in corpus.calls:
            nf[nm][f] += 1
        corpus._nf = nf
        near = defaultdict(set)
        for (a, v), k in corpus.dist.items():
            if k == 1:
                near[a].add(v)
        corpus._near = near
    key = (name, home)
    if key not in corpus._local_freq:
        nb = corpus._near.get(home, set()) | {home}
        cnt = sum(c for f, c in corpus._nf.get(name, {}).items() if f in nb)
        corpus._local_freq[key] = cnt
    cnt = corpus._local_freq[key]
    if cnt == 0:
        base = 0.30
    else:
        base = 0.50 + 0.18 * min(1.0, math.log(1 + cnt) / math.log(6))
    s = base * LSB_FULL + rnd.gauss(0, LSB_FULL * 0.13)
    return max(0, min(LSB_FULL - 1, int(s))), COST_L0


def evidence_L1(ctx, rnd):
    """
    语境层：调用点的结构上下文。

    可疑语境（在被 try 包着、没有实参、不是 mod.func 形式）提高悬空概率 ——
    重构遗留的半完成代码确实长这样。弱信号，且对两类符号都带噪声。
    """
    p = 0.5
    if ctx.get('qualified'):
        p += 0.13
    if ctx.get('nargs', 0) > 0:
        p += 0.06
    if ctx.get('in_try'):
        p -= 0.15
    s = p * LSB_FULL + rnd.gauss(0, LSB_FULL * 0.11)
    return max(0, min(LSB_FULL - 1, int(s))), COST_L1


def evidence_NL(name, corpus, nl_reliability, rnd):
    """
    自然语言线索 —— 人的痕迹。docstring/注释里提过这个名字吗。
    免费，但可靠性由 nl_reliability 控制：
        1.0  注释永远准确
        0.0  纯噪声（等于切断这条通路）
    """
    hit = corpus.nl.get(name, 0)
    base = 0.42 if hit == 0 else 0.60 + min(0.26, 0.06 * hit)
    truthful = base * nl_reliability + 0.5 * (1 - nl_reliability)
    noise = LSB_FULL * 0.12 * (2 - nl_reliability)
    strength = int(truthful * LSB_FULL + rnd.gauss(0, noise))
    return max(0, min(LSB_FULL - 1, strength)), COST_NL


def evidence_L2(name, home, corpus, max_hops, external_ok, rnd):
    """溯源层：唯一能确证的通路。追不到返回 UNKNOWN（None），不是"没有"。"""
    hops, hit = trace(name, home, corpus, max_hops, external_ok)
    cost = (max_hops if hops is None else hops) * COST_PER_HOP
    if hit:
        return int(LSB_FULL * 0.93), cost, True
    return None, cost, False


# ════════════════════════════════════════════════════════════════
# 她的决策
# ════════════════════════════════════════════════════════════════

def decide(name, ctx, home, corpus, params, external_ok, nl_reliability, rnd):
    """
    params:
        d    溯源深度上限（跳）—— 旋钮1：她肯为确证走多远
        tau  对自然语言线索的信任权重 —— 旋钮2：她肯信人的话多少
        thr  判定门槛（LSB 归一化 0~1）—— 旋钮3：什么强度才敢开口

    返回 (判定是否接地, 花费 t₀, 是否 UNKNOWN)
    """
    d = int(max(1, params['d']))
    tau = max(0.0, min(1.0, float(params['tau'])))
    thr = float(params['thr']) * LSB_FULL

    ev2, cost2, hit = evidence_L2(name, home, corpus, d, external_ok, rnd)
    if hit:
        return True, cost2, False          # 确证，早停省钱

    # 追不到 —— 关键分支：不许直接判"空洞"
    ev0, c0 = evidence_L0(name, home, corpus, rnd)
    ev1, c1 = evidence_L1(ctx, rnd)
    evN, cN = evidence_NL(name, corpus, nl_reliability, rnd)
    total = cost2 + c0 + c1 + cN

    w1, wN, w0 = 0.34, 0.30 * tau, 0.12
    s = w1 + wN + w0
    soft = (ev1 * w1 + evN * wN + ev0 * w0) / s
    return (soft >= thr), total, True


# ════════════════════════════════════════════════════════════════
# 评分 —— 外部容差，不由她定（★89：别让她自己给自己打分）
# ════════════════════════════════════════════════════════════════

COST_FALSE_POSITIVE = 1.00   # 空洞符号被放行 —— 最贵
COST_FALSE_NEGATIVE = 0.22   # 真符号被拦下 —— 只是多查一次
GAIN_TRUE_NEGATIVE = 0.55    # 拦住一个空洞符号
GAIN_TRUE_POSITIVE = 0.62    # 放行一个真符号（调至与"一律拦下"持平，否则 thr 单调到上界）
COST_UNKNOWN = 0.06          # 诚实报"追不到"


def score(claim, unknown, grounded, spent_t0=0.0, budget_t0=None, budget_penalty=0.0):
    if grounded and claim:
        r = GAIN_TRUE_POSITIVE
    elif grounded and not claim:
        r = -COST_FALSE_NEGATIVE
    elif claim:
        r = -COST_FALSE_POSITIVE
    else:
        r = GAIN_TRUE_NEGATIVE
    if unknown:
        # 追不到不等于可以免责：她仍然判了，仍要承担后果，
        # 只是额外付一份"证据不足"的代价。否则 tau/thr 会变成挂件。
        r -= COST_UNKNOWN
    if budget_penalty > 0 and budget_t0:
        r -= budget_penalty * max(0.0, spent_t0 - budget_t0) / budget_t0
    return r


# ════════════════════════════════════════════════════════════════
# 任务集：真符号 + 空洞符号
# ════════════════════════════════════════════════════════════════

def perturb(name, rnd):
    """模拟重构遗留的悬空引用：真人代码里真实发生的故障模式。"""
    if len(name) < 3:
        return name + 'x'
    mode = rnd.randrange(4)
    i = rnd.randrange(len(name))
    if mode == 0:                      # 拼错一个字符
        return name[:i] + rnd.choice('abcdefghijklmnopqrstuvwxyz') + name[i + 1:]
    if mode == 1:                      # 删一个字符
        return name[:i] + name[i + 1:]
    if mode == 2:                      # 大小写/下划线改写（改名后未同步）
        return name.replace('_', '') if '_' in name else name + '_v2'
    return name[:i] + name[i:].capitalize()   # 改名


def make_tasks(corpus, hole_rate, n, rnd, pool=None, suspicious=0.55):
    """hole_rate 为空洞符号占比。真符号来自真实调用点，空洞来自扰动。"""
    pool = pool or corpus.calls
    real = [c for c in pool if c[0] in corpus.defs or c[0] in dir(builtins)]
    rnd.shuffle(real)
    n_hole = int(round(n * hole_rate))
    tasks = []
    for nm, home, ctx in real[:n - n_hole]:
        tasks.append({'name': nm, 'home': home, 'ctx': ctx, 'grounded': True})
    src = real[n - n_hole: n - n_hole + n_hole * 3] or real[:n_hole * 3]
    made, seen = 0, set()
    for nm, home, ctx in src:
        if made >= n_hole:
            break
        cand = perturb(nm, rnd)
        if cand in corpus.defs or cand in dir(builtins) or cand in seen:
            continue
        seen.add(cand)
        if rnd.random() < suspicious:
            ctx2 = {'qualified': False, 'nargs': 0, 'in_try': True,
                    'in_comment_ctx': False}
        else:
            ctx2 = ctx
        tasks.append({'name': cand, 'home': home, 'ctx': ctx2, 'grounded': False})
        made += 1
    rnd.shuffle(tasks)
    return tasks
