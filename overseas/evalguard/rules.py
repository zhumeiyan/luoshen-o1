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


def _has_word(low_src, *words):
    """Word-boundary keyword test (exp129).

    v1-v2 used bare substring `k in low`. That made "acc" match `accept`,
    `account`, `accent`; "fit" match `profit`, `fitting`; "curl" match
    `curly`. Scanning 34 real files from 9 authoritative eval frameworks
    (lm-eval-harness, openai/evals, helm, BIG-bench, ...) these substrings
    fired on utility modules that never report a metric. Substring matching
    is the same defect we diagnosed in the TACT engine (exp099).
    """
    # exp131: the boundary class included `_`, so snake_case compounds were
    # invisible -- `random_baseline` did NOT count as containing "baseline".
    # Well-named code was therefore the only code that failed this test:
    # EG002 fired on our own clean fixture precisely because we named the
    # variable properly. `_` is a separator in Python identifiers, not a
    # word character. (Substring protection is retained: `accept` still
    # fails, because `ept` follows the `acc`.)
    for w in words:
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])",
                     low_src):
            return True
    return False


NOISE_PATH = ("tests/", "test_", "conftest", "examples/", "docs/",
              "/docs", "sample", "demo")


def _is_noise_path(path, tree=None):
    """Test / example / docs modules are not evaluation scripts.

    exp129: 7 of 27 blockers on real corpora came from files that only
    *define* helpers or *test* them. A linter that blocks on those is
    unusable, however correct the rule is in principle.

    v1 of this filter keyed on the directory name alone, which also
    silenced every planted fixture (they live under tests/) -- it removed
    2 real positives for every 8 false ones. A benchmark runner that merely
    sits under tests/ is still an evaluation script; key on content.
    """
    q = str(path).replace("\\", "/").lower()
    base = q.rsplit("/", 1)[-1]
    if base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py":
        return True
    # exp130: corpus paths are flattened (`/` -> `_`), so `examples/scorer.py`
    # arrives as `examples_scorer.py` and slipped the `/examples/` test.
    if "examples_" in base or base.startswith("example_") or "_example" in base:
        return True
    if "examples/" in q or "/docs" in q or "/demo" in q or "sample" in q:
        return True
    if "/tests/" in q and tree is not None:
        looks = False
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                mod = getattr(n, "module", "") or ""
                nm = " ".join(a.name for a in n.names)
                if "pytest" in mod + nm or "unittest" in mod + nm:
                    looks = True
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and n.name.startswith("test"):
                looks = True
        return looks
    return False


def _emits_metric(tree, low_src):
    """True if the module actually outputs a metric, not just computes it."""
    if _has_word(low_src, "print", "logging", "logger", "write", "save",
                 "dump", "report", "csv", "stdout", "stderr", "wandb",
                 "tensorboard", "输出", "报告"):
        return True
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            nm = getattr(f, "attr", None) or getattr(f, "id", None)
            if nm and nm.lower() in ("print", "dump", "dumpjson", "writerow",
                                     "to_csv", "log", "info", "warning",
                                     "save", "write"):
                return True
    return False




def _derives_rules(tree, low_src):
    """True only if the module *induces* something from data (exp129).

    v1-v2 matched the substring "fit", which is inside `profit`, `fitting`,
    `default`. Every standard benchmark runner in openai/simple-evals was
    flagged as "fitting and evaluating on the same corpus" -- reading a
    fixed benchmark split is not fitting.
    """
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            nm = (getattr(f, "attr", None) or getattr(f, "id", None) or "").lower()
            if nm in ("fit", "fit_transform", "induce", "derive", "learn_rules",
                      "extract_rules", "train_test_split"):
                return True
    return _has_word(low_src, "induce", "derive", "归纳", "fit_transform")


def _metric_line(tree, src):
    """Line where a metric is actually emitted (exp129).

    v1-v2 always reported line 1, which made every finding look like it
    pointed at the module docstring -- unactionable and, worse, impossible
    to tell apart from a real hit at a glance.
    """
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nm = (getattr(f, "attr", None) or getattr(f, "id", None) or "").lower()
        if nm in ("print", "dump", "dumpjson", "writerow", "to_csv", "save",
                  "write", "info", "warning", "log"):
            return n.lineno
    return None



def _silent_documented(src, handler, host_try=None):
    """True if the author said why silence is safe (exp129, tightened exp138).

    AST source segments drop trailing comments: for
    `pass  # this is not a critical failure` the handler segment ends at
    `pass`, so a `"#" in segment` test silently never fired -- the fix
    looked applied and was not. Read raw lines instead, and also look one
    line above the `try` (documented fallback: `# To run hf-oldstyle ...`).

    exp138: reading raw lines introduced the opposite bug, and it was worse
    because it was invisible. The test became `if "#" in line`, i.e. ANY
    comment anywhere in the handler exempts it. Our own fixture stopped
    reporting EG006 purely because the fixture annotated the defect with
    `# EG006 silent except` -- the annotation of a bug silently cured it.
    A linter whose warnings can be turned off by writing a comment is a
    linter with an off switch, and nobody has to justify using it.

    So the comment now has to actually say the silence is safe. That is a
    weaker guarantee than understanding it (no keyword list can), but it
    restores the property that matters: the exemption has to be claimed,
    not merely adjacent.
    """
    lines = src.split("\n")
    lo = handler.lineno - 1
    hi = getattr(handler, "end_lineno", None) or handler.lineno
    for k in range(lo, min(hi + 1, len(lines))):
        if _says_safe(lines[k]):
            return True
    if host_try is not None:
        k = host_try.lineno - 2
        if 0 <= k < len(lines) and _says_safe(lines[k]):
            return True
    return False


# Words that constitute a claim that swallowing the exception is fine.
# Deliberately narrow: a marker label like "# EG006" or "# TODO" must NOT
# exempt, or the rule is opt-out. "not critical" is included because it is
# the exact phrase that appeared in the authoritative corpus and was
# adjudicated as a true negative.
_EXEMPT = ("safe", "safely", "intentional", "intentionally", "deliberate",
           "deliberately", "expected", "okay", "ok to", "fine to", "harmless",
           "non-critical", "noncritical", "not critical", "not a critical",
           "best effort", "best-effort", "fallback", "fall back", "tolerate",
           "tolerated", "acceptable", "by design", "no need", "ignore",
           "ignored", "unimportant", "does not matter", "doesn't matter",
           "无关", "可忽略", "无妨", "预期", "有意", "安全", "不影响")


def _says_safe(line):
    """Does this line's comment actually claim the silence is safe?"""
    if "#" not in line:
        return False
    comment = line.split("#", 1)[1].lower()
    return any(w in comment for w in _EXEMPT)


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
    reports = _has_word(low, "accuracy", "acc", "recall", "precision",
                        "f1", "hit_rate", "命中", "准确率")
    baseline = _has_word(low, "baseline", "random_base", "chance",
                         "基线", "随机基线", "null_model")
    if not (reports and not baseline):
        return []
    if _is_noise_path(path, tree):
        return []
    if not _emits_metric(tree, low):
        return []
    # exp132: the anchor must be an emit call that *names a metric*.
    #
    # exp130 pinned this to the first emit call in the file, which in
    # lm_eval/evaluator.py is `eval_logger.info("Setting verbosity...")` and
    # in olmes is `logger.info(f"GPU memory: ...")`. Both are emit calls;
    # neither is about accuracy. That is why only 35.3% of findings landed
    # on the code they accuse.
    #
    # EG002 is an ABSENT rule -- there is no "missing baseline" node to
    # point at -- so its anchor is the node that carries the semantics under
    # accusation: the statement that reports the metric. `resolve()` then
    # requires the anchor's own source to name a metric; if no such
    # statement exists the finding is reported at module level rather than
    # pinned to an unrelated line.
    try:
        from . import anchors
    except ImportError:
        import anchors
    nodes = anchors.metric_calls(tree, src)
    kind, ln, seg = anchors.resolve("EG002", nodes, src,
                                    list(anchors.METRIC_WORDS),
                                    "metric reported")
    if kind == "module" and not nodes:
        return []
    return [{"line": ln, "kind": kind,
             "hit": (seg or "metric reported") + " — no baseline symbol found"}]


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


# exp138: the @rule decorator for EG005 used to sit HERE, directly above
# `_pathlike_names`. Two helpers were then inserted between the decorator
# and the real `def eg005` further down, so for one release the decorator
# was attached to the helper: `_pathlike_names` got registered into RULES
# and given EG005's meta, while the actual eg005 was never registered and
# never ran. Every EG005 finding in that window was the TypeError the
# helper raised when cli called it with (tree, src, path) -- reported as
# severity "info", which is why it never looked like an outage.
# A decorator and the function it names must not be separated by anything.
def _pathlike_names(tree, src):
    """exp137: names whose value is a filesystem path.

    exp130 added a keyword filter (`path|dir|folder|root|base` in the left
    operand) and exp136 hand-excluded pathlib joins while adjudicating.
    Neither was a fix: on corpus5, 11 of 31 F_small findings were still
    path joins, because the path variables were called `exp`, `carry`,
    `HERE`, `FLAVORS`, `helper_target`, `source`. A keyword filter can only
    ever match names somebody anticipated. So walk the assignments instead.
    """
    out = set()
    PATHY = ("Path(", "PurePath(", "os.path.join", "pathlib", ".resolve()",
             ".parent", ".expanduser", "Path.home", "tempfile", "mkdtemp")
    def src_of(n):
        try:
            return ast.get_source_segment(src, n) or ""
        except Exception:
            return ""
    # two passes so chains like  a = Path(x); b = a / "y"  resolve
    for _ in range(2):
        for n in ast.walk(tree):
            if not isinstance(n, (ast.Assign, ast.AnnAssign)):
                continue
            val = n.value
            tgt = n.targets[0] if isinstance(n, ast.Assign) else n.target
            if val is None or tgt is None:
                continue
            s = src_of(val)
            ok = False
            if any(k in s for k in PATHY):
                ok = True
            elif isinstance(val, ast.Name) and val.id in out:
                ok = True
            elif isinstance(val, ast.BinOp) and isinstance(val.op, ast.Div):
                ok = _is_pathlike(val, out, src_of)
            elif isinstance(val, ast.Attribute) and val.attr.lower().endswith(
                    ("path", "dir", "folder", "root", "base")):
                ok = True
            if ok:
                for t in ast.walk(tgt):
                    if isinstance(t, ast.Name):
                        out.add(t.id)
    return out


def _is_pathlike(node, names, src_of):
    if isinstance(node, ast.Name):
        return node.id in names
    if isinstance(node, ast.Attribute):
        return node.attr.lower().endswith(
            ("path", "dir", "folder", "root", "base")) or _is_pathlike(node.value, names, src_of)
    if isinstance(node, ast.Call):
        return "Path(" in src_of(node) or "Path(" in src_of(node.func)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        l = _is_pathlike(node.left, names, src_of)
        r = (isinstance(node.right, ast.Constant) and isinstance(node.right.value, str)) \
            or _is_pathlike(node.right, names, src_of)
        return l or r
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return False
    return False


@rule("EG005", [145, 35], "warn",
      "Division without denominator guard",
      "Canon #35/#145: a denominator that can hit zero either crashes or silently "
      "produces a constant-zero metric — the metric dies before the experiment does.")
def eg005(tree, src, path):
    hits = []
    prot = _protected_names(tree)
    tern = _ternary_guarded(tree, src)
    ifexps = [n for n in ast.walk(tree) if isinstance(n, ast.IfExp)]
    try:
        from .metrics import guarded_div
    except ImportError:
        from metrics import guarded_div
    _pnames = _pathlike_names(tree, src)
    def _src_of(n):
        try:
            return ast.get_source_segment(src, n) or ""
        except Exception:
            return ""
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            # exp137: semantic path join detection replaces the exp130
            # keyword filter. `exp / folder.name`, `HERE / f"{NAME}.step"`,
            # `helper_target / "release" / manifest` are all path joins even
            # though none of those names contains `path` or `dir`.
            if _is_pathlike(n.left, _pnames, _src_of) or _is_pathlike(n, _pnames, _src_of):
                continue
            if isinstance(n.right, ast.Constant) and isinstance(n.right.value, str):
                continue
            _lsrc = ast.get_source_segment(src, n.left) or ""
            if re.search(r"(?i)(path|dir|folder|root|base)\b", _lsrc):
                continue
            # exp131: a non-zero literal denominator cannot be zero.
            # `t / 10` and `thr / 10` were reported on our own clean
            # fixture -- the clean fixture had never been run against the
            # PRO rules, so this had never surfaced.
            if isinstance(n.right, ast.Constant) and isinstance(
                    n.right.value, (int, float)) and n.right.value != 0:
                continue
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
            # exp131: three real guard shapes were still missed --
            #   `if not total: return 1`      (SWE-bench grading FP)
            #   `if not D: precision = 1.0`   (simple-evals drop_eval FP)
            # Both live in the enclosing function, not on the division line.
            if not guarded and guarded_div(tree, src, n):
                guarded = True
            if not guarded:
                hits.append({"line": n.lineno, "hit": seg[:60]})
    return hits[:5]


@rule("EG006", [23], "blocker",
      "Bare or silent except (swallows the failure it should report)",
      "Canon #23: the most frequent failure in this corpus is a variable that is "
      "silently never used. A silent except turns a real error into a clean run.")
def eg006(tree, src, path):
    """exp129: a silent except is only a defect when it hides a *result*.

    Three of the twelve remaining blockers on authoritative eval frameworks
    were `except ValueError: pass` inside an int-then-float fallback chain,
    and `except PermissionError: pass  # this is not a critical failure`.
    Both are deliberate control flow: the first is a documented fallback
    (a sibling `try` follows), the second is annotated in place.
    """
    hits = []
    tries = [n for n in ast.walk(tree) if isinstance(n, ast.Try)]
    for n in ast.walk(tree):
        if not isinstance(n, ast.ExceptHandler):
            continue
        body = n.body
        silent = (len(body) == 0 or
                  (len(body) == 1 and isinstance(body[0], ast.Pass)) or
                  (len(body) == 1 and isinstance(body[0], ast.Expr)
                   and isinstance(body[0].value, ast.Constant)))
        if not (silent or n.type is None):
            continue
        host = None
        for t in tries:
            for sub in ast.walk(t):
                if sub is n:
                    host = t; break
            if host is not None:
                break
        if _silent_documented(src, n, host):
            continue                       # author annotated why it is safe
        if host is not None:
            fn = None
            for f in ast.walk(tree):
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for sub in ast.walk(f):
                        if sub is host:
                            fn = f; break
                if fn is not None:
                    break
            if fn is not None:
                sib = sum(1 for x in ast.walk(fn) if isinstance(x, ast.Try))
                if sib >= 2 and n.type is not None:
                    continue               # documented fallback chain
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
    derives = _derives_rules(tree, low)
    evals = _has_word(low, "recall", "accuracy", "score", "命中") \
            or any(k in strs for k in ("recall", "accuracy", "score", "命中"))
    held = _has_word(low, "held_out", "holdout", "loo", "leave_one",
                     "test_set", "held-out", "cross_val")
    if derives and evals and not held:
        return [{"line": 1, "hit": "fit+evaluate on same data, no held-out"}]
    return []


@rule("EG009", [23], "warn",
      "Assigned variable never used (silent dead variable)",
      "Canon #23: a variable that is assigned and never read makes the intervention "
      "a no-op — the experiment then compares a condition against itself.")
def eg009(tree, src, path):
    assigned, used = {}, set()
    # exp131: two shapes were reported as dead that are not --
    #   * a TypedDict / class body field (it declares a schema, and the
    #     schema is exported)            [lm_eval result_schema FP]
    #   * `logger = logging.getLogger(__name__)` (module-level handle)
    #     [openai/evals evals_api.py FP]
    in_class = set()
    for c in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for sub in ast.walk(c):
            in_class.add(id(sub))
    log_names = {"logger", "log", "logging", "_log", "LOGGER"}
    schema_calls = {"typeddict", "namedtuple", "dataclass", "enum"}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            if id(n) in in_class:
                continue
            if isinstance(n.value, ast.Call):
                callee = _dotted(n.value.func).lower().split(".")[-1]
                if callee in schema_calls:
                    continue      # `EvalResults = TypedDict(...)` is a schema
            for t in n.targets:
                if isinstance(t, ast.Name):
                    if t.id.lower() in log_names:
                        continue
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
    # exp131: this was a FILE-level question ("does the word skip appear
    # anywhere AND the word mean anywhere") reported at line 1. On the real
    # corpus that produced 5 false positives pinned to dict literals,
    # count prints and batch partitioning. A file-level verdict cannot be
    # pinned to a line; it must be asked of a specific function that both
    # skips items and aggregates a metric.
    try:
        from .metrics import metric_stmts
    except ImportError:
        from metrics import metric_stmts
    stmts = metric_stmts(tree, src)
    if not stmts:
        return []
    hits = []
    # the skip and the aggregation must be in the SAME loop: a dispatcher
    # function that happens to contain both somewhere is not aggregating
    # over skipped items (olmes run_eval false positive, exp131).
    for loop in _loops(tree):
        body = ast.get_source_segment(src, loop) or ""
        low = _code_only(body).lower()
        if not any(k in low for k in ("continue", "skip", "skipped")):
            continue
        if not any(k in low for k in ("mean(", "np.mean", "sum(", "average",
                                      "recall", "accuracy", "hit_rate",
                                      "len(")):
            continue
        paired = any(k in low for k in ("paired", "pair_diff", "common",
                                        "subset", "diff(", "np.diff", "配对",
                                        "共同存活", "intersection", "matched"))
        if paired:
            continue
        # exp133: the pin was the loop HEADER. The accusation is not
        # "there is a loop" -- it is "this loop skips cases". All three
        # corpus hits pinned to `for ... in enumerate(...):` while the
        # `continue` sat 1-4 lines below. A reader sent to the header
        # sees an ordinary iteration and discards a true finding.
        # Point at the statement that actually skips.
        skip_ln = None
        for n in ast.walk(loop):
            if isinstance(n, (ast.Continue, ast.Break)):
                skip_ln = n.lineno
                break
            if isinstance(n, ast.Name) and n.id.lower() in (
                    "skip", "skipped", "skips"):
                skip_ln = n.lineno
                break
        hits.append({"line": skip_ln or loop.lineno,
                     "hit": "loop skips items and aggregates, no paired diff"
                            + ("" if skip_ln else " (skip not localised)")})
    return hits[:5]


@rule("EG012", [424, 140], "warn",
      "Identification accuracy reported without a positive-control anchor",
      "Canon #424: an identification metric is only meaningful if the positive "
      "control can reach 1.0 and the negative control sits at chance level. "
      "Without both, 0.8 is uninterpretable.")
def eg012(tree, src, path):
    # exp131: this fired on any file containing the substring "acc"
    # anywhere -- lm_eval's metrics-update helper, an example scorer, a
    # batch-partitioning loop, an append of probs, a logger line. 6/6
    # false positives. The check only makes sense against a statement
    # that actually declares an identification metric.
    try:
        from .metrics import metric_stmts
    except ImportError:
        from metrics import metric_stmts
    ident_words = ("accuracy", "acc", "recall", "top1", "top_1",
                   "identification", "识别", "分类")
    idents = [s for s in metric_stmts(tree, src)
              if any(w in s.name.lower() or w in s.seg.lower()
                     for w in ident_words)]
    if not idents:
        return []
    low = _code_only(src).lower()
    pos = any(k in low for k in ("positive_control", "pos_control", "sanity",
                                 "upper_bound", "ceiling_check", "阳性对照"))
    neg = any(k in low for k in ("baseline", "chance", "random_base", "null_model",
                                 "shuffle_control", "基线", "随机基线"))
    if pos and neg:
        return []
    miss = []
    if not pos: miss.append("positive control")
    if not neg: miss.append("chance-level baseline")
    return [{"line": idents[0].lineno,
             "hit": f"`{idents[0].name}` declared without " + " + ".join(miss)}]


@rule("EG013", [40], "warn",
      "Ratio metric reported without its numerator count and denominator",
      "Canon #40: a rate of 0.07 built on 3 events is not the same claim as "
      "0.07 built on 3000. Report the absolute count next to every ratio.")
def eg013(tree, src, path):
    # exp131: "rate"/"precision" appearing in an argparse help string or a
    # dataset-split argument satisfied this rule. A ratio claim must be an
    # ARITHMETIC expression, not a word.
    hits = []
    ratio_words = ("rate", "ratio", "recall", "precision", "proportion",
                   "pct", "percent")
    for n in ast.walk(tree):
        if not isinstance(n, ast.BinOp):
            continue
        if not isinstance(n.op, (ast.Div, ast.Mult)):
            continue
        seg = ast.get_source_segment(src, n) or ""
        # the ratio word may live on the assignment target
        # (`hit_rate = sum(acc) / len(acc)`), not in the expression itself
        tgt = ""
        for a in ast.walk(tree):
            if isinstance(a, ast.Assign) and any(x is n for x in ast.walk(a)):
                tgt = " ".join(t.id for t in a.targets
                               if isinstance(t, ast.Name))
                break
        blob = (seg + " " + tgt).lower()
        if not any(w in blob for w in ratio_words):
            continue
        # CLI help / flag context is not a ratio computation
        if isinstance(n.left, ast.Constant) and isinstance(n.left.value, str):
            continue
        if isinstance(n.right, ast.Constant) and isinstance(n.right.value, str):
            continue
        hits.append({"line": n.lineno, "hit": seg[:60]})
        break
    if not hits:
        return []
    low = _code_only(src).lower()
    absolute = any(k in low for k in ("count", "n_total", "ntotal", "num_",
                                      "n_", "total", "支持度", "绝对数", "support"))
    denom = any(k in low for k in ("denominator", "denom", "分母", "/ n",
                                   "/n", "size", "n_samples"))
    if not (absolute and denom):
        return [{"line": hits[0]["line"],
                 "hit": "ratio computed, absolute count/denominator not both reported"}]
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
    if _is_noise_path(path):
        return []
    # exp132: the remote channel must be an actual CALL NODE, not a string
    # that mentions one. exp130 flagged docstring URLs (`https://...` written
    # inside a docstring) as remote channels -- a URL in prose is not a
    # channel. Keying on the node makes that class of false positive vanish
    # without any text filter, and gives us the evidence node at once.
    try:
        from . import anchors
    except ImportError:
        import anchors
    nodes = anchors.remote_calls(tree)
    if not nodes:
        return []
    checked = any(k in low for k in ("status_code", "raise_for_status",
                                     "reachable", "reachability",
                                     "timeout=", "可达性", "probe")) \
              or _has_word(low, "ok")
    stamped = any(k in low for k in ("timestamp", "asctime", "utcnow", "time.time",
                                     "datetime.now", "时间戳"))
    if not checked or not stamped:
        miss = []
        if not checked: miss.append("status check")
        if not stamped: miss.append("timestamp")
        # The evidence node is the remote call itself -- that is the thing
        # whose reachability is never re-tested. NOT line 1, NOT the nearest
        # logger call.
        kind, ln, seg = anchors.resolve("EG016", nodes, src, [], "remote call")
        return [{"line": ln, "kind": kind,
                 "hit": (seg or "remote call") + " — no " + " + ".join(miss)}]
    return []
