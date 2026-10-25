"""
evalguard PRO rule pack -- 10 additional rules for LLM / Agent evaluation
scripts.  These target failure modes that survive code review because the
code *looks* correct: the bug is in what the number means, not in whether it
runs.

Every rule traces to a numbered entry in the Luoshen Failure-Mode Canon.
"""
import ast
import re

try:
    from .rules import _code_only as _strip
except ImportError:  # direct module load
    from rules import _code_only as _strip

PRO_RULES = []

# Tokens that prove the caller validated the response before indexing.
# Deliberately excludes bare ".get(" -- `requests.get(` satisfies it, which
# made every remote call look guarded (v1 false negative).
RESP_GUARDS = ("status_code", "raise_for_status", "if not resp",
               "if not choices", "if not payload", "is none", "try")


def prule(eg_id, canon, severity, title, why, fix):
    def deco(fn):
        fn.meta = dict(eg_id=eg_id, canon=canon, severity=severity,
                       title=title, why=why, fix=fix)
        PRO_RULES.append(fn)
        return fn
    return deco


def _dotted(n):
    if isinstance(n, ast.Attribute):
        try:
            return _dotted(n.value) + "." + n.attr
        except Exception:
            return n.attr
    if isinstance(n, ast.Name):
        return n.id
    return ""


def _calls(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            yield n


def _str_consts(tree):
    return " ".join(n.value.lower() for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str))


def _body_loops(tree):
    return [n for n in ast.walk(tree)
            if isinstance(n, (ast.For, ast.While, ast.AsyncFor))]


def _fn_scope(tree, src, node):
    """Source of the smallest enclosing function of `node`.

    Gruard tokens must be searched in the function that performs the risky
    operation, not anywhere in the file -- see the EGP10 v1 bug.
    """
    best = None
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(fn):
            if sub is node:
                try:
                    seg = ast.get_source_segment(src, fn) or ""
                except Exception:
                    seg = ""
                if best is None or len(seg) < len(best):
                    best = seg
                break
    return best


def _handler_has_silencer(h):
    """True if an except handler swallows without recording.

    v1 treated `except Exception:` as *narrowed* and let it pass. It is not:
    `Exception` catches everything a bare `except` catches except for
    BaseException. Only a specific type (KeyError, ValueError, ...) counts
    as narrowed.
    """
    if h.type is not None:
        name = _dotted(h.type).split(".")[-1]
        if name not in ("Exception", "BaseException"):
            return False
    body = h.body
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True
    for st in body:
        # `continue` / `return` inside handler = sample silently dropped
        if isinstance(st, (ast.Continue, ast.Return)):
            return True
    return False


# ---------------------------------------------------------------- EGP01
@prule("EGP01", [23, 371], "blocker",
       "Failed samples are dropped before the score is computed",
       "Canon #23/#371: a bare `except: continue` inside the scoring loop "
       "removes exactly the cases the benchmark was built to catch. The "
       "accuracy then measures the subset that did not fail — a number that "
       "goes up as the model gets worse at the hard cases.",
       "Count every exception into a separate `n_error` bucket and report "
       "score alongside error rate. Never let an exception leave the loop "
       "without incrementing a counter.")
def egp01(tree, src, path):
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Try):
            in_loop = any(n in ast.walk(L) for L in _body_loops(tree))
            for h in n.handlers:
                if _handler_has_silencer(h):
                    hits.append({"line": h.lineno or n.lineno,
                                 "hit": ("silent handler inside scoring loop"
                                         if in_loop else "silent handler")})
                    break
    return hits[:5]


# ---------------------------------------------------------------- EGP02
@prule("EGP02", [139, 142], "blocker",
       "Threshold / selection tuned on the same split used to report",
       "Canon #139/#142: if the cut-off is chosen by looking at test labels, "
       "the reported score is a fit to those labels, not a prediction. The "
       "optimism is unbounded and invisible in the final number.",
       "Pick the threshold on a held-out dev split, freeze it, then evaluate "
       "once on test. Log both the dev-chosen value and the frozen value.")
def egp02(tree, src, path):
    hits = []
    for n in _calls(tree):
        d = _dotted(n.func).lower()
        if not any(k in d for k in ("argmax", "max", "min", "best", "argmin")):
            continue
        seg = ""
        try:
            seg = (ast.get_source_segment(src, n) or "").lower()
        except Exception:
            pass
        # does the selection expression read evaluation labels?
        if any(k in seg for k in ("y_test", "ytest", "test_label", "labels",
                                  "y_true", "ytrue", "gold", "gt")):
            # is there a separate dev/val split anywhere in the file?
            # v1 matched the substring "val", which "pvals" satisfies -- a file
            # that merely computes p-values looked like it had a dev split.
            low = _strip(src)
            if not re.search(r"\b(dev|val|valid|validation|heldout|holdout|"
                             r"hold_out|校准|开发集)\b", low):
                hits.append({"line": n.lineno,
                             "hit": f"selection on labels without dev split ({d})"})
    return hits[:4]


# ---------------------------------------------------------------- EGP03
@prule("EGP03", [152], "warn",
       "Many comparisons reported without multiplicity correction",
       "Canon #152: run 20 subgroup comparisons at alpha=0.05 and one of them "
       "will be 'significant' by construction. The headline p-value is then a "
       "sampling artifact.",
       "Apply Bonferroni or Benjamini-Hochberg across the family of tests you "
       "report, or pre-register the single primary comparison.")
def egp03(tree, src, path):
    low = _strip(src).lower()
    n_tests = 0.0
    comps = {id(c) for g in ast.walk(tree)
             for c in getattr(getattr(g, "generators", []), "__iter__", lambda: [])()}
    for n in _calls(tree):
        d = _dotted(n.func).lower()
        if not any(k in d for k in ("ttest", "ttest_ind", "mannwhitney", "chi2",
                                    "fisher_exact", "wilcoxon", "pearsonr",
                                    "spearmanr", "anova", "p_value", "pvalue")):
            continue
        n_tests += 1
        # a test call inside a comprehension runs once per iteration
        for node in ast.walk(tree):
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp,
                                 ast.DictComp)) and any(x is n for x in ast.walk(node)):
                for gen in node.generators:
                    it = gen.iter
                    if isinstance(it, ast.Call) and _dotted(it.func) == "range" \
                       and it.args and isinstance(it.args[0], ast.Constant) \
                       and isinstance(it.args[0].value, int):
                        n_tests += it.args[0].value - 1
                break
    # v1 counted every *occurrence* of a variable named `p` at 0.34 each, so a
    # file that merely formats a string called `p` nine times looked like it
    # ran three significance tests. Count distinct test calls only.
    p_names = {n.id.lower() for n in ast.walk(tree)
               if isinstance(n, ast.Name)
               and n.id.lower() in ("pvalue", "p_value", "pval")}
    n_tests += min(len(p_names), 1)
    if n_tests >= 3:
        corrected = any(k in low for k in ("bonferroni", "holm", "fdr",
                                           "benjamini", "bh_correct",
                                           "multipletests", "多重", "校正"))
        if not corrected:
            return [{"line": 1, "hit": f"~{int(n_tests)} comparisons, no correction"}]
    return []


# ---------------------------------------------------------------- EGP04
@prule("EGP04", [145], "blocker",
       "Pairwise LLM/human judgement without order or position debiasing",
       "Canonical position bias: when A is always shown first, 'A wins' "
       "partly measures reading order. Canon #145: the confound is invisible "
       "in the aggregate and can be larger than the effect.",
       "Randomise presentation order per pair and report the win rate "
       "separately for each order; assert the two are statistically "
       "indistinguishable before pooling.")
def egp04(tree, src, path):
    low = _strip(src).lower()
    judge = any(k in low for k in ("judge", "prefer", "winner", "which is better",
                                   "a_vs_b", "pairwise", "compare", "pair",
                                   "偏好", "胜出", "两两"))
    if not judge:
        return []
    debias = any(k in low for k in ("swap", "reverse", "order", "shuffle",
                                    "position", "ab_ba", "both_orders",
                                    "顺序", "置换"))
    if not debias:
        return [{"line": 1, "hit": "pairwise judgement with no order swap"}]
    return []


# ---------------------------------------------------------------- EGP05
@prule("EGP05", [139], "blocker",
       "Train and evaluation data loaded from the same source with no split",
       "Canon #139: recall measured on material the system has already seen "
       "measures memorisation. The number is real and the claim is false.",
       "Materialise disjoint train/eval splits with an explicit ID-level "
       "disjointness assertion, and print the overlap size (must be 0).")
def egp05(tree, src, path):
    low = _strip(src).lower()
    has_load = any(k in low for k in ("load", "read_csv", "read_json",
                                      "open(", "dataset", "split"))
    if not has_load:
        return []
    has_split = any(k in low for k in ("train_test_split", "train_test",
                                       "split(", "shuffle", "sample(",
                                       "disjoint", "overlap", "holdout"))
    if not has_split:
        # `assert not (set(train_ids) & set(test_ids))` is a disjointness
        # proof -- v1 needed the literal word "split" and missed it.
        for n in ast.walk(tree):
            if isinstance(n, ast.Assert):
                seg = ""
                try:
                    seg = ast.get_source_segment(src, n) or ""
                except Exception:
                    seg = ""
                if "set(" in seg and ("&" in seg or "isdisjoint" in seg
                                      or "intersection" in seg):
                    has_split = True
                    break
    evaluates = any(k in low for k in ("recall", "accuracy", "precision",
                                       "f1", "score", "命中", "准确率"))
    if evaluates and not has_split:
        return [{"line": 1, "hit": "evaluation with no train/eval split"}]
    return []


# ---------------------------------------------------------------- EGP06
@prule("EGP06", [141], "warn",
       "Single-seed single-run: no variance reported",
       "Canon #141: one run gives a point, not an interval. Two configs that "
       "differ by less than the run-to-run spread are indistinguishable, and "
       "without a spread you cannot tell.",
       "Repeat over >=5 seeds and report mean +/- std or a bootstrap CI; "
       "treat any gap inside the interval as 'no difference'.")
def egp06(tree, src, path):
    low = _strip(src).lower()
    reports_metric = any(k in low for k in ("print", "report", "result",
                                            "logging", "json.dump", "save"))
    if not reports_metric:
        return []
    # A deterministic rule engine has no run-to-run spread by construction;
    # demanding a CI there is noise (false positive on the TACT engine).
    try:
        from .rules import _uses_stochastic
    except ImportError:
        from rules import _uses_stochastic
    stochastic = _uses_stochastic(tree) or any(
        k in low for k in ("llm", "openai", "chat", "completion", "model",
                           "api", "sample(", "shuffle", "bootstrap"))
    if not stochastic:
        return []
    # v1 matched the substring "ci", which "scipy" satisfies -- importing
    # scipy made the file look like it reported a confidence interval.
    spread = re.search(r"\b(std|stdev|var|variance|ci|confidence|bootstrap|"
                       r"percentile|spread|方差|置信)\b", low) is not None
    multi = any(k in low for k in ("for seed", "seeds", "n_runs", "n_seeds",
                                   "repeat", "trials", "多次", "多种子"))
    if not spread and not multi:
        return [{"line": 1, "hit": "metric reported with no spread or repeat"}]
    return []


# ---------------------------------------------------------------- EGP07
@prule("EGP07", [377], "warn",
       "Cached results reused without a hash or version check",
       "Canon #377: a cache written under an older code version silently "
       "answers for the new one. Every downstream number is then a mixture.",
       "Store a hash of (code version + inputs + config) with each cache "
       "entry and refuse to load on mismatch.")
def egp07(tree, src, path):
    hits = []
    for n in _calls(tree):
        d = _dotted(n.func).lower()
        if not any(k in d for k in ("json.load", "pickle.load", "read_csv",
                                    "read_parquet", "open")):
            continue
        seg = ""
        try:
            seg = (ast.get_source_segment(src, n) or "").lower()
        except Exception:
            pass
        cached = any(k in seg for k in ("cache", "cached", "ckpt", "checkpoint",
                                        "prev", "saved", "dump"))
        if not cached:
            continue
        low = _strip(src).lower()
        guarded = any(k in low for k in ("sha256", "md5", "hashlib", "hash",
                                         "version", "etag", "mtime"))
        if not guarded:
            hits.append({"line": n.lineno, "hit": f"cache load unhashed ({d})"})
    return hits[:4]


# ---------------------------------------------------------------- EGP08
@prule("EGP08", [23], "warn",
       "Assertions only guard the success path",
       "Canon #23: asserts that all sit after a successful call never fire, "
       "because the failure arrives as an exception, not as a wrong value. "
       "The suite reports green while the pipeline is broken.",
       "Assert on the failure path too: after catching, check that the "
       "recorded failure count matches what you expected to trigger.")
def egp08(tree, src, path):
    n_assert = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Assert))
    n_try = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Try))
    if n_assert and n_try:
        for n in ast.walk(tree):
            if isinstance(n, ast.Try):
                inner = sum(1 for x in ast.walk(n) if isinstance(x, ast.Assert))
                if inner:
                    break
        else:
            return [{"line": 1,
                     "hit": f"{n_assert} assert(s), none inside any try block"}]
    return []


# ---------------------------------------------------------------- EGP09
@prule("EGP09", [40], "warn",
       "Per-sample scores collapsed to a mean with no tail reported",
       "Canon #40: a mean of 0.8 can be 100% of samples at 0.8, or 80% at 1.0 "
       "and 20% at 0.0. These are opposite products with the same score.",
       "Report p0/p50/p90 or the failure-count alongside the mean, and gate "
       "release on the tail, not the average.")
def egp09(tree, src, path):
    low = _strip(src).lower()
    # a list that is appended to inside a loop IS a per-sample score list,
    # whatever it is named -- v1 required the name to contain "scores".
    per_sample = any(k in low for k in ("per_sample", "scores", "results",
                                        "each", "逐条", "每条"))
    if not per_sample:
        for loop in _body_loops(tree):
            for n in ast.walk(loop):
                if isinstance(n, ast.Call) and _dotted(n.func).endswith("append"):
                    per_sample = True
                    break
            if per_sample:
                break
    if not per_sample:
        return []
    uses_mean = any(k in low for k in (".mean(", "np.mean", "mean(",
                                       "average", "sum(", "/ len"))
    tail_tokens = ("percentile", "quantile", "p90", "p95", "p10", "worst",
                   "tail", "hist", "分位", "最差")
    # v1 searched the whole file, so an unrelated `min(pvals)` counted as a
    # tail statistic. The tail must accompany the aggregation.
    # v2: scope to the enclosing function. v1 was statement-scoped and
    # flagged correct code that computes the mean on one line and reports
    # p50/p90/worst on the next.
    scope = (_fn_scope(tree, src, tree) or _strip(src)).lower()
    if not any(k in scope for k in (".mean(", "np.mean", "mean(",
                                    "average", "/ len")):
        return []
    if any(k in scope for k in tail_tokens):
        return []
    return [{"line": 1, "hit": "mean over samples with no tail statistic"}]


# ---------------------------------------------------------------- EGP10
@prule("EGP10", [378], "blocker",
       "Model response indexed into without validating its shape",
       "Canon #378: `resp['choices'][0]['content']` on a rate-limit or refusal "
       "response raises, or worse, silently yields an empty string that scores "
       "as a miss. The failure is attributed to the model, not the caller.",
       "Check status and presence of each level before indexing; record a "
       "typed failure reason (refusal / timeout / malformed) per item.")
def egp10(tree, src, path):
    hits = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Subscript):
            continue
        seg = ""
        try:
            seg = ast.get_source_segment(src, n) or ""
        except Exception:
            continue
        if not seg:
            continue
        low = seg.lower()
        deep = low.count("[") >= 2 and any(
            k in low for k in ("choice", "content", "message", "text",
                               "result", "output", "data"))
        if not deep:
            continue
        guard_src = _fn_scope(tree, src, n) or _strip(src)
        guard_src = guard_src.lower()
        # v1 searched the WHOLE file for "len(" / "try:". Any unrelated length
        # computation anywhere in the file silenced the rule.
        # v1 used bare ".get(", which `requests.get(` satisfies -- any remote
        # call looked like a guarded access.
        guarded = any(k in guard_src for k in RESP_GUARDS)
        if not guarded:
            hits.append({"line": n.lineno, "hit": seg.strip()[:56]})
    return hits[:4]
