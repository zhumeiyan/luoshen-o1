"""
evalguard rules — each rule traces back to a numbered entry in the
Luoshen Failure-Mode Canon (368 entries mined from 100+ real experiments).

Every rule carries:
  eg_id    : stable rule id
  canon    : source canon entry id(s) in the failure-mode database
  severity : blocker / warn / info
  title    : one-line English statement
"""
import ast
import re

RULES = []

def rule(eg_id, canon, severity, title, why):
    def deco(fn):
        fn.meta = dict(eg_id=eg_id, canon=canon, severity=severity,
                       title=title, why=why)
        RULES.append(fn)
        return fn
    return deco


def _code_only(src):
    """Strip comments and string literals WITHOUT destroying dotted names.

    Two real bugs lived here, both silent (canon #23):

    v1  `re` was not imported, so the fallback branch raised NameError.
    v2  tokens were joined with `" ".join(...)`, which turned `requests.get`
        into `requests . get`. Every dotted keyword in every rule silently
        stopped matching -- EG016 could never fire on any real remote call.
        Fixed by preserving token positions with `untokenize`, so the
        de-commented source keeps its original spacing.

    Canon #23 origin: scanning raw source lets a comment that *mentions*
    'baseline' satisfy a check meant to prove the code *computes* a baseline.
    """
    import io, tokenize
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except Exception:
        return re.sub(r'#[^\n]*', '', src)
    out = []
    for t in toks:
        if t.type in (tokenize.COMMENT, tokenize.STRING):
            out.append(tokenize.TokenInfo(t.type, ' ' * len(t.string),
                                          t.start, t.end, t.line))
        else:
            out.append(t)
    try:
        return tokenize.untokenize(out)
    except Exception:
        return "".join(t.string for t in out)


def _strings(tree):
    """Text of every string literal -- where *claims* live (canon #53)."""
    return " ".join(n.value.lower() for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str))


def _ternary_guarded(tree, src):
    """Divisions written as `x / d if d else fallback` ARE guarded (canon #145).

    Real code (TACT engine, line 161) reads:
        rec = 100*stat['tp'][a]/stat['gtot'][a] if stat['gtot'][a] else nan
    v1 only inspected assignments, so this correct code was flagged.
    """
    good = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.IfExp):
            continue
        try:
            body = (ast.get_source_segment(src, n.body) or "").lower()
            test = (ast.get_source_segment(src, n.test) or "").lower()
        except Exception:
            continue
        if "/" not in body or not test.strip():
            continue
        # the guard term names a variable/subscript that also appears in the divisor
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_'\[\]]*", test):
            if len(tok) >= 2 and tok in body:
                good.add(tok)
    return good


def _protected_names(tree):
    """Names whose assignment already guards against zero (canon #145).

    v1 only looked at the division expression itself, so a guard written one
    line earlier (`denom = max(n_pos, 1)`) was invisible -> false positive on
    correct code.
    """
    good = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            seg = ""
            try:
                seg = (ast.get_source_segment(_SRC[0], n.value) or "").lower()
            except Exception:
                seg = ""
            if any(k in seg for k in ("max(", "np.maximum", "eps", "1e-",
                                      "np.finfo", "+ 1", "+1", " or ")):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        good.add(t.id)
    return good


_SRC = [""]


def _walk_calls(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            yield n

def _dotted(n):
    if isinstance(n, ast.Attribute):
        try: return _dotted(n.value) + "." + n.attr
        except Exception: return n.attr
    if isinstance(n, ast.Name):
        return n.id
    return ""

def _has_seed(tree):
    # v1 only matched `.seed()` calls -> false positive on `random.Random(SEED)`
    # and `np.random.default_rng(SEED)`, which are themselves seeded constructors.
    for c in _walk_calls(tree):
        d = _dotted(c.func)
        if d.endswith(("seed", "manual_seed", "set_seed")):
            return True
        if d.endswith(("Random", "default_rng", "Generator")) and c.args:
            return True
    return False

def _imports(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names: out.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            if n.module: out.add(n.module.split(".")[0])
    return out

def _uses_stochastic(tree):
    for c in _walk_calls(tree):
        d = _dotted(c.func)
        if d.split(".")[0] in ("random", "np", "numpy", "torch", "tf", "jax", "faker"):
            if any(k in d for k in ("rand", "shuffle", "choice", "sample", "uniform",
                                    "normal", "randn", "permutation", "bernoulli")):
                return True
    return False


@rule("EG001", [141, 23], "warn",
      "Stochastic API used without any seed call",
      "Unseeded randomness makes the reported number unreproducible; a single "
      "re-run can move the metric more than the effect you are claiming.")
def eg001(tree, src, path):
    if _uses_stochastic(tree) and not _has_seed(tree):
        for c in _walk_calls(tree):
            d = _dotted(c.func)
            if d.split(".")[0] in ("random", "np", "numpy", "torch"):
                return [{"line": c.lineno, "hit": d}]
    return []


@rule("EG002", [140], "blocker",
      "Accuracy/recall reported with no random baseline",
      "A recall of 0.95 is meaningless if random guessing already gives 0.90. "
      "Canon #140: report net gain over baseline, not raw rate.")
def eg002(tree, src, path):
    low = _code_only(src).lower()
    reports = any(k in low for k in ("accuracy", "acc", "recall", "precision",
                                     "f1", "hit_rate", "命中", "准确率"))
    baseline = any(k in low for k in ("baseline", "random_base", "chance",
                                      "基线", "随机基线", "null_model"))
    if reports and not baseline:
        return [{"line": 1, "hit": "metric reported, no baseline symbol found"}]
    return []


@rule("EG003", [142], "warn",
      "Decision threshold hard-coded as a magic number",
      "Canon #142: net discriminative power is an inverted-U in the threshold. "
      "A single hard-coded value hides the peak and can miss it entirely.")
def eg003(tree, src, path):
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            for c in n.comparators:
                if isinstance(c, ast.Constant) and isinstance(c.value, (int, float)):
                    v = c.value
                    if 0.0 < v < 1.0 and v not in (0.5,):
                        hits.append({"line": n.lineno, "hit": f"threshold {v}"})
                        break
    seen = set()
    return [h for h in hits if not (h["line"] in seen or seen.add(h["line"]))][:5]


@rule("EG004", [43], "warn",
      "Clustering / threshold sweep absent: single cut-off only",
      "Canon #43: cluster count is threshold-sensitive. One cut-off is a snapshot, "
      "not a result; sweep and report the curve.")
def eg004(tree, src, path):
    """Flag a single hard-coded cluster count.

    Bug fixed: v1 tested `"for" in src` / `"range" in src`, which any unrelated
    loop in the file satisfied — the rule never fired. Correct version inspects
    the call's own keyword argument."""
    calls = {}
    for c in _walk_calls(tree):
        d = _dotted(c.func)
        if any(k in d for k in ("KMeans", "DBSCAN", "Agglomerative",
                                "SpectralClustering", "cluster")):
            calls.setdefault(d, []).append(c)
    for d, cs in calls.items():
        if len(cs) > 1:
            continue                      # called repeatedly => likely a sweep
        for kw in cs[0].keywords:
            if kw.arg in ("n_clusters", "eps", "min_samples", "k") \
               and isinstance(kw.value, ast.Constant):
                return [{"line": cs[0].lineno,
                         "hit": f"{d}({kw.arg}={kw.value.value!r}) single literal cut-off"}]
    return []


@rule("EG005", [145, 35], "warn",
      "Division without denominator guard",
      "Canon #35/#145: a denominator that can hit zero either crashes or silently "
      "produces a constant-zero metric — the metric dies before the experiment does.")
def eg005(tree, src, path):
    hits = []
    prot = _protected_names(tree)
    tern = _ternary_guarded(tree, src)
    ifexps = [n for n in ast.walk(tree) if isinstance(n, ast.IfExp)]
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            seg = ast.get_source_segment(src, n) or ""
            segl = seg.lower()          # v1 missed `+ EPS` (uppercase)
            # NB: `len(` is NOT a guard -- len(x) can be 0. (v1 wrongly
            # treated it as one and missed every real case.)
            guarded = any(k in segl for k in ("+ 1", "+1", "max(", "eps", " or ",
                                              "1e-", "np.finfo", "if ", "np.maximum"))
            if not guarded and isinstance(n.right, ast.Name) and n.right.id in prot:
                guarded = True          # guard lives at the assignment, one line up
            if not guarded:
                # v2: `x / d if d else nan` IS guarded. Real TACT engine code
                # reads `100*tp/gtot if gtot else nan`; v1 flagged it because
                # the Div node's own source stops before ` if `.
                div = ast.get_source_segment(src, n.right) or ""
                for ie in ifexps:
                    if not any(x is n for x in ast.walk(ie)):
                        continue
                    t = ast.get_source_segment(src, ie.test) or ""
                    if div and div in t.replace(" ", "").replace(
                            t, t) or (div and div.replace(" ", "") in
                                      t.replace(" ", "")):
                        guarded = True
                        break
                if not guarded and div and any(
                        tok in tern for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", div)):
                    guarded = True
            if not guarded:
                hits.append({"line": n.lineno, "hit": seg[:60]})
    return hits[:5]


@rule("EG006", [23], "blocker",
      "Bare or silent except (swallows the failure it should report)",
      "Canon #23: the most frequent failure in this corpus is a variable that is "
      "silently never used. A silent except turns a real error into a clean run.")
def eg006(tree, src, path):
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler):
            body = n.body
            silent = (len(body) == 0 or
                      (len(body) == 1 and isinstance(body[0], ast.Pass)) or
                      (len(body) == 1 and isinstance(body[0], ast.Expr)
                       and isinstance(body[0].value, ast.Constant)))
            if silent or (n.type is None):
                hits.append({"line": n.lineno, "hit": "bare/silent except"})
    return hits


@rule("EG007", [53], "warn",
      "Claims a result is saved/archived with no write call",
      "Canon #53: claiming 'archived' without verifying the bytes hit disk is an "
      "empty delivery. Log string is not evidence.")
def eg007(tree, src, path):
    """Claim-of-persistence lives in *strings* (log/print text), while the
    evidence of a write lives in code. v1 stripped strings and therefore
    never saw the claim; v2 reads each side from where it actually lives."""
    strs = " ".join(n.value.lower() for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str))
    low = _code_only(src).lower()
    claims = any(k in strs for k in ("saved", "archived", "已保存", "已归档", "dumped"))
    writes = any(k in low for k in ("open(", ".write(", "json.dump", "to_csv",
                                    "np.save", "torch.save", "shutil.copy"))
    if claims and not writes:
        return [{"line": 1, "hit": "claims persistence, no write call found"}]
    return []


@rule("EG008", [139], "blocker",
      "Evaluating recall on the same corpus the rules were derived from",
      "Canon #139: a taxonomy induced from a corpus scores ~1.0 on that corpus by "
      "construction. Use leave-one-out or a held-out set.")
def eg008(tree, src, path):
    low = _code_only(src).lower()
    strs = _strings(tree)
    derives = any(k in low for k in ("fit", "induce", "derive", "extract", "归纳"))
    evals = any(k in low for k in ("recall", "accuracy", "score", "命中")) \
             or any(k in strs for k in ("recall", "accuracy", "score", "命中"))
    held = any(k in low for k in ("held_out", "holdout", "loo", "leave_one",
                                  "test_set", "held-out", "cross_val"))
    if derives and evals and not held:
        return [{"line": 1, "hit": "fit+evaluate on same data, no held-out"}]
    return []


@rule("EG009", [23], "warn",
      "Assigned variable never used (silent dead variable)",
      "Canon #23: a variable that is assigned and never read makes the intervention "
      "a no-op — the experiment then compares a condition against itself.")
def eg009(tree, src, path):
    assigned, used = {}, set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    assigned[t.id] = n.lineno
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            used.add(n.id)
        elif isinstance(n, ast.Attribute):
            pass
    fn = {n.name for n in ast.walk(tree)
          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return [{"line": ln, "hit": f"`{k}` assigned, never read"}
            for k, ln in assigned.items()
            if k not in used and not k.startswith("_") and k not in fn
            and not k.isupper()][:6]        # UPPER_CASE = module constant/export


@rule("EG010", [147, 148], "info",
      "Single metric drives the conclusion; no second independent measure",
      "Canon: every single statistic has a structural blind spot (e.g. MSE is "
      "invariant to frame order). Pair each claim with a metric blind to a "
      "different failure mode.")
def eg010(tree, src, path):
    low = _code_only(src).lower()
    n_metrics = sum(1 for k in ("accuracy", "recall", "precision", "f1", "mse",
                                "loss", "score", "kappa", "corr")
                    if k in low)
    if n_metrics == 1:
        return [{"line": 1, "hit": f"only one metric family present"}]
    return []


# ---------------------------------------------------------------- v0.2 -----
# Added after v0.1 shipped: 6 more rules drawn from canon entries that were
# listed as actionable but had no executable check yet.
# Each one is paired with a fixture in tests/ (planted / clean control).


def _loops(tree):
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.AsyncFor, ast.While)):
            yield n


def _loop_body_src(loop, src):
    return " ".join((ast.get_source_segment(src, b) or "")
                    for b in loop.body)


@rule("EG011", [419], "warn",
      "Condition can skip cases, but results are compared as group rates",
      "Canon #419: whenever a condition can skip (continue/return early), group "
      "rates are computed on different denominators. Compare paired differences "
      "on the common surviving subset, not rates across unequal sets.")
def eg011(tree, src, path):
    low = _code_only(src).lower()
    skips = any(k in low for k in ("continue", "skip", "skipped", "continue_"))
    if not skips:
        return []
    agg = any(k in low for k in ("mean(", "np.mean", "sum(", "len(", "average",
                                 "recall", "accuracy", "hit_rate"))
    paired = any(k in low for k in ("paired", "pair_diff", "common", "subset",
                                    "diff(", "np.diff", "配对", "共同存活",
                                    "intersection", "matched"))
    if agg and not paired:
        return [{"line": 1, "hit": "skip present + group-rate aggregation, no paired diff"}]
    return []


@rule("EG012", [424, 140], "warn",
      "Identification accuracy reported without a positive-control anchor",
      "Canon #424: an identification metric is only meaningful if the positive "
      "control can reach 1.0 and the negative control sits at chance level. "
      "Without both, 0.8 is uninterpretable.")
def eg012(tree, src, path):
    low = _code_only(src).lower()
    ident = any(k in low for k in ("accuracy", "acc", "recall", "top1",
                                   "identification", "分类", "识别"))
    if not ident:
        return []
    pos = any(k in low for k in ("positive_control", "pos_control", "sanity",
                                 "upper_bound", "ceiling_check", "阳性对照"))
    neg = any(k in low for k in ("baseline", "chance", "random_base", "null_model",
                                 "shuffle_control", "基线", "随机基线"))
    if not (pos and neg):
        miss = []
        if not pos: miss.append("positive control")
        if not neg: miss.append("chance-level baseline")
        return [{"line": 1, "hit": "missing " + " + ".join(miss)}]
    return []


@rule("EG013", [40], "warn",
      "Ratio metric reported without its numerator count and denominator",
      "Canon #40: a rate of 0.07 built on 3 events is not the same claim as "
      "0.07 built on 3000. Report the absolute count next to every ratio.")
def eg013(tree, src, path):
    low = _code_only(src).lower()
    ratio = any(k in low for k in ("rate", "ratio", "recall", "precision",
                                   "proportion", "pct", "percent"))
    if not ratio:
        return []
    absolute = any(k in low for k in ("count", "n_total", "ntotal", "num_",
                                      "n_", "total", "支持度", "绝对数", "support"))
    denom = any(k in low for k in ("denominator", "denom", "分母", "/ n",
                                   "/n", "size", "n_samples"))
    if not (absolute and denom):
        return [{"line": 1, "hit": "ratio present, absolute count/denominator not both reported"}]
    return []


@rule("EG014", [125], "warn",
      "Value named 'fixed'/'constant' is regenerated inside the loop",
      "Canon #125: anything declared constant across conditions must be "
      "generated once outside the loop and passed in explicitly. Regenerating "
      "it per-iteration silently makes the conditions incomparable.")
def eg014(tree, src, path):
    hits = []
    for loop in _loops(tree):
        body = _loop_body_src(loop, src)
        for n in ast.walk(loop):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and any(
                            k in t.id.lower() for k in ("fixed", "const", "shared",
                                                        "common", "global_seed")):
                        if any(k in body.lower() for k in ("random", "rand",
                                                           "shuffle", "choice",
                                                           "sample", "uniform")):
                            hits.append({"line": n.lineno,
                                         "hit": f"`{t.id}` regenerated inside loop"})
    return hits[:5]


@rule("EG015", [421], "warn",
      "Multi-axis system reported as one aggregate score",
      "Canon #421: axes are not interchangeable. An overall recall of 0.86 can "
      "hide one axis at 0.50. Report every axis separately.")
def eg015(tree, src, path):
    low = _code_only(src).lower()
    axes = 0
    for grp in (("axis", "axes"), ("l_axis", "m_axis", "p_axis"),
                ("dim1", "dim2"), ("轴",)):
        if any(k in low for k in grp):
            axes += 1
    per_axis = any(k in low for k in ("per_axis", "by_axis", "each_axis",
                                      "for axis", "分轴", "各轴"))
    agg_only = any(k in low for k in ("overall", "aggregate", "total_score",
                                      "macro", "总体", "综合"))
    if axes >= 1 and agg_only and not per_axis:
        return [{"line": 1, "hit": "aggregate score reported without per-axis breakdown"}]
    return []


@rule("EG016", [377, 378], "blocker",
      "Conclusion depends on an external channel with no reachability re-test",
      "Canon #377/#378: a channel that was reachable last month can be 403 "
      "today. Any claim that depends on a remote endpoint must re-measure "
      "reachability at run time and stamp it.")
def eg016(tree, src, path):
    low = _code_only(src).lower()
    # v1 (and v0.2) included bare ".get(", which every dict `.get(k, d)` call
    # satisfies -- a file with no network access at all was flagged as making
    # remote calls (confirmed false positive on the TACT engine).
    remote = any(k in low for k in ("requests.get", "requests.post",
                                    "requests.put", "requests.request",
                                    "urlopen", "httpx", "urllib",
                                    "http.client", "aiohttp", "curl",
                                    "socket.create_connection"))
    if not remote:
        return []
    checked = any(k in low for k in ("status_code", "raise_for_status",
                                     ".ok", "reachable", "reachability",
                                     "timeout=", "可达性", "probe"))
    stamped = any(k in low for k in ("timestamp", "asctime", "utcnow", "time.time",
                                     "datetime.now", "时间戳"))
    if not checked or not stamped:
        miss = []
        if not checked: miss.append("status check")
        if not stamped: miss.append("timestamp")
        return [{"line": 1, "hit": "remote call without " + " + ".join(miss)}]
    return []
