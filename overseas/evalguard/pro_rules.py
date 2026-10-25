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
    from .rules import _code_only as _strip, _silent_documented
except ImportError:  # direct module load
    from rules import _code_only as _strip, _silent_documented

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



# Roots that can plausibly hold a *model response* (exp129).
# v1-v2 accepted ANY subscript whose text contained data/result/output/text.
# On real corpora that matched `result_dict[column][k]` (lm-eval-harness),
# `req["request"]["context"]` (olmes), `sample["target_scores"][choice]`
# (BIG-bench) -- all internal data structures, none of them a model
# response. 14 of 27 blockers on authoritative eval frameworks were these.
RESP_ROOTS = ("resp", "response", "res", "r", "out", "output", "completion",
              "completions", "choice", "choices", "message", "content",
              "answer", "pred", "prediction", "generated", "reply", "payload",
              "body", "json_resp", "api_resp", "chat_response")


def _ann_nodes(tree):
    """Every node that lives inside a type annotation."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.AnnAssign, ast.arg, ast.FunctionDef,
                          ast.AsyncFunctionDef)):
            tgt = getattr(n, "annotation", None) or getattr(n, "returns", None)
            if tgt is not None:
                out += [x for x in ast.walk(tgt)]
    return {id(x) for x in out}


def _root_name(node):
    while isinstance(node, (ast.Subscript, ast.Attribute, ast.Call)):
        node = node.value if not isinstance(node, ast.Call) else node.func
    return getattr(node, "id", "") if isinstance(node, ast.Name) else ""


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
def _handler_records(h):
    """True if the handler leaves a trace before exiting (exp129).

    `except Exception as e: logger.error(f"Failed ... {e}"); return` was
    reported as silent. It is not: the failure is logged and the caller is
    told. Only *unrecorded* removal corrupts the score.
    """
    for st in ast.walk(h):
        if isinstance(st, ast.Call):
            f = st.func
            nm = ((getattr(f, "attr", None) or getattr(f, "id", None) or "") +
                  (getattr(f, "value", None) and getattr(f.value, "id", "") or "")).lower()
            if any(k in nm for k in ("log", "error", "warn", "print",
                                     "exception", "critical")):
                return True
    return False



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
    """Only unrecorded drops *inside a scoring loop* corrupt the score.

    exp129: two of three EGP01 blockers on authoritative frameworks were
    `except Exception: pass` in CLI plumbing (not in any loop) and a
    handler that logged the error before returning. Neither drops a sample.
    """
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Try):
            in_loop = any(n in ast.walk(L) for L in _body_loops(tree))
            if not in_loop:
                continue
            for h in n.handlers:
                if not _handler_has_silencer(h):
                    continue
                if _handler_records(h):
                    continue
                if _silent_documented(src, h, n):
                    continue
                hits.append({"line": h.lineno or n.lineno,
                             "hit": "silent handler inside scoring loop"})
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
    """exp130: `max(len(gold), len(predicted))` inside `np.zeros([...])`
    in openai/simple-evals drop_eval.py was reported as "threshold tuned on
    test labels". It is an array allocation. Hungarian matching
    (`linear_sum_assignment`) in the same file is alignment, not selection.
    Both are excluded here; the remaining hits must localise to a line.
    """
    from . import context
    idx = context.build(src, path)
    hits = []
    for n in _calls(tree):
        d = _dotted(n.func).lower()
        if not any(k in d for k in ("argmax", "max", "min", "best", "argmin")):
            continue
        if idx is not None and idx.in_alloc(n):
            continue
        # alignment, not selection: an assignment solver picks a permutation
        if any(k in _strip(src).lower() for k in ("linear_sum_assignment",
                                                  "hungarian")):
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
    """exp130: this rule returned line 1 for every file that merely
    contained the word 'compare'. On the 27-file real corpus it fired on
    BIG-bench and lighteval files that do no pairwise judging at all.

    Two changes:
      1. require *both* sides of a pair to be named (a/b, cand*, resp*,
         left/right, model_a/model_b) -- 'compare' alone is not evidence;
      2. localise with the index. If no line can be shown, return [] --
         G-LINE (context.py): an unlocalisable finding is not a finding.
    """
    from . import context
    idx = context.build(src, path)
    if idx is None:
        return []
    low = _strip(src).lower()
    paired = (any(k in low for k in ("a_vs_b", "pairwise", "model_a", "model_b",
                                     "candidate_a", "candidate_b", "response_a",
                                     "response_b", "choice_a", "choice_b",
                                     "left", "right", "ab_ba", "both_orders"))
               or bool(re.search(r"\bjudge\w*\b", low)))
    if not paired:
        return []
    # exp130: the correctly-debiased fixture reports both orders as
    # `order_a` / `order_b`. v2 looked for the bare word "order" and was
    # dropped for matching unrelated prose; restoring it narrowly as a
    # both-orders pattern keeps the true negative.
    debias = any(k in low for k in ("swap", "reverse", "shuffle",
                                    "ab_ba", "both_orders", "position_bias",
                                    "order_bias", "顺序", "置换")) \
        or bool(re.search(r"(?i)order[_-]?(a|b)\b.*order[_-]?(b|a)\b", low)) \
        or bool(re.search(r"(?i)both\s+orders", low))
    if debias:
        return []
    # exp130: "judge"/"prefer"/"winner" alone matched `judge model` (model
    # unloading) and `"preferred_score": "exact_str_match"` (a metric name).
    # Require an explicit pair symbol before claiming pairwise judgement.
    ln = idx.locate("a_vs_b", "pairwise", "model_a", "candidate_a",
                    "response_a", "choice_a", "both_orders",
                    "re:\\bjudge\\s*\\(", "re:\\bcompare\\s*\\(")
    if ln is None:
        return []
    return [{"line": ln, "hit": "pairwise judgement with no order swap "
                                f"(scope: {idx.func_name(ln)})"}]


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
    # exp131: `reports_metric` was satisfied by the mere presence of
    # "print"/"report"/"result"/"logging"/"save" -- so a schema module, an
    # example file, a config warning, a batch-partitioning loop, a dict
    # unpacking and two logger lines were all flagged. 9/9 false positives.
    # "Reports a metric" must mean: a statement declares one.
    try:
        from .metrics import metric_stmts
    except ImportError:
        from metrics import metric_stmts
    if not metric_stmts(tree, src):
        return []
    # declaration-only modules never run a measurement
    if re.search(r"(?i)\b(typed|typeddict|namedtuple|dataclass|schema|protocol)\b",
                 low) and not re.search(r"(?i)\bdef\s+(run|main|eval|compute|"
                                        r"score|measure)\b", low):
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
        stmts = metric_stmts(tree, src)
        return [{"line": stmts[0].lineno,
                 "hit": "metric reported with no spread or repeat"}]
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
    # exp131: this fired on any file that had both an assert and a try
    # somewhere -- a batch-partitioning loop, an append of probs, two
    # logger lines. 4/4 false positives. "Assertions are unprotected" is
    # only a defect when the assertions ARE the validation surface: a
    # function whose job is to check something.
    hits = []
    for f in (n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        if not re.search(r"(?i)(valid|check|verify|sanity|assert|guard)", f.name):
            continue
        asserts = [a for a in ast.walk(f) if isinstance(a, ast.Assert)]
        if not asserts:
            continue
        # the function is the validation surface: an assert here that can
        # raise past the caller is the defect, try-protected or not
        tries = [t for t in ast.walk(f) if isinstance(t, ast.Try)]
        protected = False
        if tries:
            protected = any(any(a in list(ast.walk(t)) for t in tries)
                            for a in asserts)
        if not protected:
            hits.append({"line": asserts[0].lineno,
                         "hit": f"assert(s) in `{f.name}()` outside any try block"})
    return hits[:3]


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
    #
    # exp131: v2 was ALSO broken, silently. It called
    # `_fn_scope(tree, src, tree)` -- but `tree` is never a descendant of
    # any function, so it always returned None and fell back to the whole
    # file. The function-scope restriction had never taken effect.
    # Correct form: find each aggregation site, resolve ITS enclosing
    # function, and look for the tail inside that function only.
    try:
        from .metrics import metric_stmts
    except ImportError:
        from metrics import metric_stmts
    if not metric_stmts(tree, src):
        return []
    agg_names = (".mean", "np.mean", "mean(", "average", "/ len", "sum(")
    bad = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        seg = ast.get_source_segment(src, n) or ""
        if not any(k in seg.lower() for k in agg_names):
            continue
        scope = _fn_scope(tree, src, n)
        if scope is None:
            continue
        sc = scope.lower()
        if any(k in sc for k in tail_tokens):
            continue
        bad.append({"line": n.lineno,
                    "hit": f"mean over samples in `{_encl_name(tree, n)}` "
                           f"with no tail statistic"})
    if not bad:
        # aggregation via plain operators, not a Call -> keep one file-level
        # verdict but pin it to the first metric statement, not line 1
        sc = _strip(src).lower()
        if any(k in sc for k in agg_names) and not any(
                k in sc for k in tail_tokens):
            stmts = metric_stmts(tree, src)
            return [{"line": stmts[0].lineno,
                     "hit": "mean over samples with no tail statistic"}]
        return []
    return bad[:3]


def _encl_name(tree, node):
    best, bl = None, -1
    for f in ast.walk(tree):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if f.lineno <= node.lineno <= (getattr(f, "end_lineno", None) or 10**9):
                if f.lineno > bl:
                    best, bl = f, f.lineno
    return best.name if best else "<module>"


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
    ann = _ann_nodes(tree)
    for n in ast.walk(tree):
        if not isinstance(n, ast.Subscript):
            continue
        if id(n) in ann:
            continue                      # Optional[List[Text]] is not an access
        if isinstance(n.slice, ast.Slice):
            continue                      # x[:-1] is a slice, not a deep index
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
        if _root_name(n).lower().strip("_") not in RESP_ROOTS:
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
