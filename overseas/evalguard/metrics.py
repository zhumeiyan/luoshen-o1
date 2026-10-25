"""Statement-level metric extraction for evalguard.

Why this module exists (exp131):

    Every file-level rule (EG011/EG012/EG013, EGP06/08/09) asked
    "does this FILE contain the word X anywhere?" and then reported
    line 1. exp130 bolted an anchor locator on top, which pinned a
    file-level verdict onto whatever symbol happened to be nearby --
    producing 33 false positives of the shape "dict literal",
    "logger line", "append of probs".

    The fix is not a better anchor. A file-level question cannot be
    pinned to a line at all. These rules must be rewritten to require
    a real *metric declaration statement* and to ask about THAT
    statement.

Definition used here -- a statement is a metric declaration iff:

    1. `name = <numeric expression>`, name is metric-like, and the
       RHS is not a bare literal / dict / list / string; or
    2. `return <...>` where the value contains a metric-like name or
       a dict with metric-like keys; or
    3. a call to an emit surface (print/log/report/save/dump/
       summary/emit/record) whose arguments contain a metric-like
       keyword or name bound to a numeric expression.

    Explicitly NOT metric declarations (all were false positives):
        X.append(p)          collecting scores
        d[k] = v             filling a dict
        d.update(...)        dict plumbing
        x = "accuracy"       a string
        logger = logging...  module logger assignment
        add_argument("--x")  CLI help text
"""

import ast
import re

# ---------------------------------------------------------------- names

METRIC_WORDS = (
    "acc", "accuracy", "acc_norm", "acc_std", "recall", "precision",
    "f1", "score", "scores", "rate", "ratio", "hit_rate", "pass@",
    "pass_at", "exact", "exact_match", "em", "bleu", "rouge", "top1",
    "top_1", "top5", "mrr", "ndcg", "auc", "error", "err", "loss",
    "correct", "num_correct", "n_correct", "hit", "miss", "success",
    "resolved", "resolve_rate", "win_rate", "mean_score", "avg_score",
    "pct", "percent", "proportion", "prop", "n_hits", "n_correct",
    "identification", "micro", "macro", "weighted",
)

# names that LOOK metric-like but are not metrics in practice
NOT_METRIC = (
    "accuracy_threshold", "acc_template", "score_dir", "score_path",
    "scores_dir", "rate_limit", "rate_limiter", "error_log",
    "error_handler", "loss_fn", "loss_fn_name",
)

EMIT_SURFACES = (
    "print", "emit", "log", "logger", "logging", "report", "save",
    "dump", "write", "summary", "record", "track", "info", "warning",
    "debug", "display", "show", "table", "wandb", "mlflow",
)

_BUILTINS = {
    "sum", "len", "max", "min", "abs", "round", "int", "float", "str",
    "list", "dict", "set", "tuple", "sorted", "any", "all", "bool",
    "enumerate", "zip", "range", "isinstance", "np", "math",
}

CONTAINER_OPS = ("append", "extend", "update", "add", "insert", "setdefault")

_ARITH = (ast.BinOp, ast.Call, ast.Subscript, ast.IfExp, ast.Compare,
          ast.ListComp, ast.GeneratorExp)


def _dotted(node):
    out = []
    while isinstance(node, ast.Attribute):
        out.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        out.append(node.id)
    return ".".join(reversed(out))


def is_metric_name(name):
    """True if `name` reads as a metric identifier (not a path/flag)."""
    if not name:
        return False
    n = name.lower()
    if n in NOT_METRIC:
        return False
    if n.endswith(("_path", "_dir", "_file", "_url", "_name", "_key",
                   "_flag", "_arg", "_template", "_limit", "_limiter")):
        return False
    parts = re.split(r"[^a-z0-9]+", n)
    for w in METRIC_WORDS:
        if w in parts:
            return True
    # also allow camel/snake containment for the longer words
    for w in ("accuracy", "precision", "recall", "resolved", "correct"):
        if w in n:
            return True
    return False


def _is_stringy(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_bare_literal(node):
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
        # a dict/list of metrics IS plausible (result payloads), but a
        # literal of constants is data, not a computed metric
        vals = []
        if isinstance(node, ast.Dict):
            vals = [v for v in node.values if v is not None]
        else:
            vals = list(node.elts)
        return all(isinstance(v, ast.Constant) for v in vals) if vals else True
    return False


def _numeric_rhs(node):
    """RHS plausibly produces a number."""
    if _is_stringy(node):
        return False
    if _is_bare_literal(node):
        return False
    if isinstance(node, _ARITH):
        return True
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Attribute):
        return True
    if isinstance(node, ast.UnaryOp):
        return True
    if isinstance(node, ast.JoinedStr):   # f-string -> report surface
        return False
    return False


def _target_names(t):
    if isinstance(t, ast.Name):
        return [t.id]
    if isinstance(t, ast.Attribute):
        return [t.attr]
    if isinstance(t, ast.Tuple):
        out = []
        for e in t.elts:
            out.extend(_target_names(e))
        return out
    return []


# ------------------------------------------------------------ extraction

class Stmt:
    __slots__ = ("node", "lineno", "kind", "name", "seg", "func")

    def __init__(self, node, kind, name, seg, func=None):
        self.node = node
        self.lineno = getattr(node, "lineno", 1)
        self.kind = kind          # assign | return | emit
        self.name = name
        self.seg = (seg or "")[:120]
        self.func = func

    def __repr__(self):
        return f"<Stmt {self.kind} {self.name} L{self.lineno}>"


def _enclosing_func(tree, node):
    best, bestline = None, -1
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if getattr(f, "lineno", 0) <= node.lineno <= (
                    getattr(f, "end_lineno", None) or 10 ** 9):
                if f.lineno > bestline:
                    best, bestline = f, f.lineno
    return best.name if best else None


def metric_stmts(tree, src):
    """All statements that genuinely declare / compute / emit a metric."""
    out = []
    for n in ast.walk(tree):
        # ---- assignment
        if isinstance(n, ast.Assign):
            # `X.append(...)` / `X.update(...)` are collection, not declaration
            if isinstance(n.value, ast.Call):
                fn = _dotted(n.value.func).split(".")[-1]
                if fn in CONTAINER_OPS:
                    continue
            if any(isinstance(t, ast.Subscript) for t in n.targets):
                continue                     # d[k] = v
            names = []
            for t in n.targets:
                names.extend(_target_names(t))
            if not names:
                continue
            if not any(is_metric_name(x) for x in names):
                continue
            if not _numeric_rhs(n.value):
                continue
            out.append(Stmt(n, "assign", names[0],
                            ast.get_source_segment(src, n),
                            _enclosing_func(tree, n)))
            continue

        # ---- return
        if isinstance(n, ast.Return) and n.value is not None:
            if _is_stringy(n.value):
                continue
            hit = None
            for sub in ast.walk(n.value):
                if isinstance(sub, ast.Name) and is_metric_name(sub.id):
                    hit = sub.id
                    break
                if isinstance(sub, ast.Attribute) and is_metric_name(sub.attr):
                    hit = sub.attr
                    break
                if isinstance(sub, ast.Dict):
                    for k in sub.keys:
                        if isinstance(k, ast.Constant) and isinstance(
                                k.value, str) and is_metric_name(k.value):
                            hit = k.value
                            break
                if hit:
                    break
            if hit:
                out.append(Stmt(n, "return", hit,
                                ast.get_source_segment(src, n),
                                _enclosing_func(tree, n)))
            continue

        # ---- emit surface
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
            fn = _dotted(n.value.func)
            tail = fn.split(".")[-1]
            if tail not in EMIT_SURFACES and not any(
                    s in fn.lower() for s in ("report", "emit", "record",
                                              "summary", "track")):
                continue
            if tail == "print":
                pass
            elif not any(s in fn.lower() for s in EMIT_SURFACES):
                continue
            hit = None
            for kw in n.value.keywords:
                if kw.arg and is_metric_name(kw.arg):
                    hit = kw.arg
                    break
            if hit is None:
                for a in n.value.args:
                    if isinstance(a, ast.Name) and is_metric_name(a.id):
                        hit = a.id
                        break
                    if isinstance(a, ast.Dict):
                        for k in a.keys:
                            if isinstance(k, ast.Constant) and isinstance(
                                    k.value, str) and is_metric_name(k.value):
                                hit = k.value
                                break
                    if hit:
                        break
            if hit is None:
                # f-string naming a metric: print(f"ACCURACY {acc}")
                for a in n.value.args:
                    if isinstance(a, ast.JoinedStr):
                        txt = " ".join(
                            v.value for v in a.values
                            if isinstance(v, ast.Constant)
                            and isinstance(v.value, str)).lower()
                        for w in METRIC_WORDS:
                            # exp133: `w in txt` is bare substring -- the
                            # exact defect canon #23 names and the one
                            # fixed in rules.py::_has_word back in exp129.
                            # It was never fixed HERE, so short metric
                            # words matched inside ordinary prose:
                            #   "em"  c- "GPU memory:\n{gpu_memory}"  (memory)
                            #   "err" c- "Computing deferred metrics"  (deferred)
                            # which made `logger.info("GPU memory: ...")`
                            # qualify as "the statement that reports the
                            # metric" -- the anchor exp130 and exp132 both
                            # flagged as wrong, still wrong, for a reason
                            # neither of those rounds found.
                            if re.search(r"(?<![A-Za-z0-9])" + re.escape(w)
                                         + r"(?![A-Za-z0-9])", txt):
                                hit = w
                                break
                    if hit:
                        break
            if hit:
                out.append(Stmt(n, "emit", hit,
                                ast.get_source_segment(src, n),
                                _enclosing_func(tree, n)))
    return out


def declares_metric(tree, src):
    return len(metric_stmts(tree, src)) > 0


# ------------------------------------------------------- guard detection

def _name_src(node):
    try:
        import ast as _a
        if isinstance(node, _a.Name):
            return node.id
        if isinstance(node, _a.Attribute):
            return node.attr
    except Exception:
        pass
    return None


def _container_of(node):
    """`len(x)` / `float(len(x))` -> the container name `x`.

    Returns None for computed divisors (`sum(len(x) for x in data[c])`),
    which forces the strict guard test -- mentioning `data` does not make
    that sum non-zero.
    """
    if not isinstance(node, ast.Call):
        return None
    f = _dotted(node.func).split(".")[-1]
    if f in ("len", "float", "int", "size"):
        if not node.args:
            return None
        if f == "len":
            return _name_src(node.args[0])
        return _container_of(node.args[0])
    return None


def guarded_div(tree, src, div_node):
    """Is this division protected against a zero denominator?

    Recognises three real guard shapes, all missed or mishandled
    before exp131:

        early return : `if not total: return 1`            (SWE-bench FP)
        else-assign  : `if not D: precision = 1.0`         (simple-evals FP)
        ternary      : `a / b if b else nan`               (TACT, handled v2)
    """
    seg = ast.get_source_segment(src, div_node) or ""
    segl = seg.lower()
    if any(k in segl for k in ("+ 1", "+1", "max(", "eps", " or ",
                               "1e-", "np.finfo", "np.maximum")):
        return True
    # exp131 second pass: the first version matched ANY name shared between
    # the divisor and an `if` test. Since `sum`/`len` are builtins present in
    # almost every condition, `len(data[c]) == 0: continue` was accepted as a
    # guard for `sum(len(x) for x in data[c])` -- which it is not (every x
    # can be empty). Builtins must not count as identifying names.
    divisor = ast.get_source_segment(src, div_node.right) or ""
    dnames = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", divisor)) - _BUILTINS
    if not dnames:
        return False
    # A guard must test the DIVISOR EXPRESSION ITSELF, not merely mention one
    # of its variables. `if len(data[c]) == 0` does not protect
    # `sum(len(x) for x in data[c])`.
    dflat = divisor.replace(" ", "")
    # divisor shape decides how strict the guard test must be:
    #   container form  `len(x)` / `float(len(x))` / `x.size` -> the guard
    #                   legitimately says `if not x`, so matching the
    #                   variable is enough (simple-evals FP, exp131)
    #   computed form   `sum(len(x) for x in data[c])` -> mentioning `data`
    #                   does NOT protect it, so the guard must speak about
    #                   the whole expression (planted fixture, must stay hit)
    container = _container_of(div_node.right)
    strict = container is None
    for ie in (n for n in ast.walk(tree) if isinstance(n, ast.IfExp)):
        if not any(x is div_node for x in ast.walk(ie)):
            continue
        test = ast.get_source_segment(src, ie.test) or ""
        if dnames & set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", test)):
            return True
    if not dnames:
        return False
    fn = None
    best = -1
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if getattr(f, "lineno", 0) <= div_node.lineno <= (
                    getattr(f, "end_lineno", None) or 10 ** 9):
                if f.lineno > best:
                    fn, best = f, f.lineno
    if fn is None:
        return False
    for n in ast.walk(fn):
        # early return / early raise / early continue guard
        if isinstance(n, (ast.Return, ast.Raise)) or isinstance(n, ast.Continue):
            if n.lineno > div_node.lineno:
                continue
        if isinstance(n, ast.If):
            test = ast.get_source_segment(src, n.test) or ""
            tflat = test.replace(" ", "")
            if strict:
                # the test must speak about the divisor expression itself
                if dflat not in tflat:
                    continue
            else:
                # container form: the test must name that container
                if container.replace(" ", "") not in tflat:
                    continue
            # exp131: `\b` in front of the alternation kills the `==` branch
            # outright -- `\b` requires a word/non-word transition, and both
            # sides of `=` are non-word, so `\b==` can never match. The zero
            # test silently never fired. Same class of bug as `requests . get`.
            neg = re.search(r"(?i)(\bnot\b|==\s*0|<= ?0|\bis\s+none|len\()",
                            test)
            if not neg:
                continue
            # early-exit guard anywhere in the branch -> division unreachable
            for sub in ast.walk(n):
                if isinstance(sub, (ast.Return, ast.Raise, ast.Continue)):
                    return True
            # else-branch (or orelse) assigns the quotient's target a default
            for sub in ast.walk(n):
                if isinstance(sub, ast.Assign) and sub.lineno < div_node.lineno:
                    return True
            # the division itself sits inside a guarded branch
            if any(x is div_node for x in ast.walk(n)):
                return True
    return False
