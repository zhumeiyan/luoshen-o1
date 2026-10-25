"""AST context index — function-level and line-level localisation.

Why this module exists (exp129 -> exp130):

Scanning 27 real source files from 9 authoritative eval frameworks
(lm-evaluation-harness, openai/evals, simple-evals, lighteval, SWE-bench,
inspect_ai, olmes, helm, BIG-bench) produced 27 blockers, of which 24 were
false. Manual triage of the 6 survivors showed that 5 reported **line 1**
-- the module docstring. A finding pinned to line 1 cannot be acted on and,
worse, cannot be told apart from a real hit at a glance: the report looks
identical whether the evidence exists or not.

Two structural gates follow, and both are enforced here:

  G-LINE   a finding must carry an evidence line. No line -> no finding.
           A rule that cannot say *where* is a rule that did not see
           anything; reporting it anyway is canon #23 (an assertion that
           never fails looks exactly like one that never needed to).

  G-SCOPE  a metric rule may only fire in a scope that is on the evaluation
           path. A library that defines helpers, or an example that shows
           usage, is not reporting a number.

Both gates are themselves falsifiable: each must be able to produce both
"keep" and "drop" on real files, otherwise it is saturated and useless.
"""
import ast
import re

METRIC_WORDS = (
    "accuracy", "acc", "recall", "precision", "f1", "score", "scores",
    "bleu", "rouge", "pass@", "pass_at", "exact_match", "em", "mrr",
    "ndcg", "auc", "error_rate", "win_rate", "winrate", "success_rate",
)

EMIT_CALLS = (
    "print", "write", "save", "dump", "dumpjson", "writerow", "writerows",
    "to_csv", "to_json", "log", "info", "warning", "debug", "error",
    "report", "append", "update",
)

# Allocation calls: a `max(...)` inside these is sizing an array, not
# selecting a threshold on labels (exp130: np.zeros([max(len(gold), ...)])
# in openai/simple-evals drop_eval.py was flagged as EGP02).
ALLOC_CALLS = (
    "zeros", "ones", "empty", "full", "zeros_like", "ones_like",
    "arange", "linspace", "eye", "identity", "reshape", "np.zeros",
)

ENTRY_MARKERS = ("__main__", "argparse", "click", "main(")


def _dotted(node):
    """`a.b.c` -> 'a.b.c'; bare name -> 'a'."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


class Index:
    """Per-file AST index: scopes, code lines, entry point, evidence lines."""

    def __init__(self, tree, src, path=""):
        self.tree = tree
        self.src = src or ""
        self.path = str(path)
        self.lines = self.src.split("\n")
        self.low = self.src.lower()
        self._code_lines = None
        self._scopes = None
        self._entry = None
        self._emit_lines = None
        self._doc_lines = None

    # ------------------------------------------------------------ lines
    def doc_lines(self):
        """Lines occupied by module/class/function docstrings.

        exp130: the EG016 anchor matched a Google Sheets URL sitting inside
        a function docstring in helm/scripts/heim_human_eval.py and reported
        it as an unreachability-tested remote call. A docstring is prose,
        and prose is exactly what canon #23 warns about.
        """
        if self._doc_lines is None:
            s = set()
            for n in ast.walk(self.tree):
                if not isinstance(n, (ast.Module, ast.FunctionDef,
                                      ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if n.body and isinstance(n.body[0], ast.Expr) \
                        and isinstance(n.body[0].value, ast.Constant) \
                        and isinstance(n.body[0].value.value, str):
                    lo = n.body[0].lineno
                    hi = getattr(n.body[0], "end_lineno", None) or lo
                    s.update(range(lo, hi + 1))
            self._doc_lines = s
        return self._doc_lines

    def code_lines(self):
        """Line numbers (1-based) that contain code, not comment/blank.

        Kept simple and cheap: strip everything after an unquoted '#'.
        Docstring lines are handled separately by callers that care.
        """
        if self._code_lines is None:
            s = set()
            for i, ln in enumerate(self.lines, 1):
                t = ln.split("#", 1)[0].strip()
                if t:
                    s.add(i)
            self._code_lines = s
        return self._code_lines

    def locate(self, *patterns, word=True):
        """First code line matching any pattern; None if there is none.

        This is what turns a file-level finding into a line-level one. It
        returns None rather than 1 when nothing matches -- that None is the
        signal G-LINE uses to drop the finding.
        """
        d = self.doc_lines()
        for i in sorted(self.code_lines()):
            if i in d:
                continue
            ln = self.lines[i - 1]
            t = ln.split("#", 1)[0]
            for p in patterns:
                if p.startswith("re:"):
                    if re.search(p[3:], t, re.I):
                        return i
                elif word:
                    if re.search(r"(?<![A-Za-z0-9_])" + re.escape(p) +
                                 r"(?![A-Za-z0-9_])", t, re.I):
                        return i
                elif p in t:
                    return i
        return None

    # ----------------------------------------------------------- scopes
    def scopes(self):
        """{function_node: (name, lineno, end_lineno)} for top-level defs
        plus a synthetic MODULE entry."""
        if self._scopes is None:
            out = []
            for n in ast.walk(self.tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append((n, n.name, n.lineno,
                                getattr(n, "end_lineno", None) or n.lineno))
            self._scopes = out
        return self._scopes

    def enclosing(self, line):
        """Outermost def whose body contains `line`; None at module level."""
        best = None
        for n, name, lo, hi in self.scopes():
            if lo <= line <= hi:
                if best is None or lo > best[1]:
                    best = (n, lo, hi, name)
        return best

    def func_name(self, line):
        e = self.enclosing(line)
        return e[3] if e else "<module>"

    # ------------------------------------------------------------ entry
    def is_entry(self):
        """True if this module runs something (script / CLI), not just
        defines it. Examples and libraries both answer False."""
        if self._entry is None:
            hit = False
            for n in ast.walk(self.tree):
                if isinstance(n, ast.If):
                    seg = ast.dump(n.test)[:200]
                    if "__main__" in seg:
                        hit = True
                if isinstance(n, ast.Name) and n.id == "__main__":
                    hit = True
            # module-level executable statement (call / assignment) outside
            # any def or class
            if not hit:
                for n in self.tree.body:
                    if isinstance(n, (ast.Expr, ast.Assign, ast.AugAssign)):
                        hit = True
                        break
            self._entry = hit
        return self._entry

    # ------------------------------------------------------------ emit
    def emit_lines(self):
        """Lines where something is actually written out (log/print/save)."""
        if self._emit_lines is None:
            s = set()
            for n in ast.walk(self.tree):
                if isinstance(n, ast.Call):
                    nm = (getattr(n.func, "attr", None) or
                          getattr(n.func, "id", None) or "").lower()
                    if nm in EMIT_CALLS:
                        s.add(n.lineno)
            self._emit_lines = s
        return self._emit_lines

    def emits_metric(self):
        for ln in self.emit_lines():
            # look at the statement source around the emit for a metric word
            for k in range(max(1, ln - 2), ln + 3):
                if k - 1 < len(self.lines):
                    t = self.lines[k - 1].lower()
                    if any(w in t for w in METRIC_WORDS):
                        return ln
        if self.emit_lines() and any(w in self.low for w in METRIC_WORDS):
            return min(self.emit_lines())
        return None

    def metric_anchor(self):
        """Best line to pin an *absence* rule to (exp130).

        `emits_metric()` alone returned L162 of lm_eval/evaluator.py, which
        is `eval_logger.info("Setting verbosity ... is deprecated.")` -- the
        first log call in the file, unrelated to any metric. A reader
        inspecting that line concludes the finding is bogus, and the
        underlying claim (harness reports accuracy with no random baseline)
        gets thrown out with it. Prefer, in order:
          1. an emit whose neighbourhood names a metric
          2. the aggregation of a results/accuracy structure
          3. None -- caller drops the finding
        """
        ln = self.emits_metric()
        if ln:
            lo, hi = max(1, ln - 2), min(len(self.lines), ln + 2)
            blob = " ".join(self.lines[lo - 1:hi]).lower()
            if any(w in blob for w in METRIC_WORDS) or "result" in blob \
                    or "metric" in blob:
                return ln
        d = self.doc_lines()
        for i in sorted(self.code_lines()):
            if i in d:
                continue
            t = self.lines[i - 1]
            if re.search(r"(?i)\b(results?|acc|scores?|metrics?|stats?)\b\s*[:=]", t) \
                    or re.search(r"(?i)\b(results?|acc|scores?|metrics?)\s*=\s*", t):
                return i
        return None

    def scope_source(self, line):
        """Source text of the innermost def containing `line`, else module."""
        e = self.enclosing(line)
        if e is None:
            return "\n".join(self.lines)
        node = e[0]
        try:
            return ast.get_source_segment(self.src, node) or ""
        except Exception:
            lo, hi = e[1], e[2]
            return "\n".join(self.lines[lo - 1:hi])

    def scope_has_metric(self, line):
        """Does the function containing `line` actually deal with a metric?

        exp130 G-SCOPE: findings anchored into `instance_batches[...].append`
        (olmes batching) or `logger.info("Running %s requests")` (lighteval)
        are true stories told in the wrong room. The rule fired on the file;
        the line it points at has nothing to do with the claim.
        """
        t = self.scope_source(line).lower()
        if any(w in t for w in METRIC_WORDS):
            return True
        return bool(re.search(r"(?i)\b(result|results|metric|metrics|score|"
                              r"scores|eval|evaluate|grading|grade)\b", t))

    def on_eval_path(self):
        """Is this file plausibly *an evaluation* rather than a library,
        an example, or a helper?

        Two independent signals, either suffices:
          (a) it runs something (entry point) and mentions a metric
          (b) it emits a metric from inside a function
        """
        if any(w in self.low for w in METRIC_WORDS) and self.is_entry():
            return True
        if self.emits_metric() is not None and self.is_entry():
            return True
        return False

    # ------------------------------------------------------- allocation
    def in_alloc(self, node):
        """True if `node` sits inside an array-allocation call.

        exp130: `np.zeros([max(len(gold), len(predicted))])` in
        simple-evals/drop_eval.py. The `max` there sizes a buffer; it does
        not choose a cut-off from test labels. Matching it produced the
        single most convincing-looking false positive in the corpus.
        """
        for anc in ast.walk(self.tree):
            if not isinstance(anc, ast.Call):
                continue
            if anc is node:
                continue
            nm = (getattr(anc.func, "attr", None) or
                  getattr(anc.func, "id", None) or "").lower()
            if nm in ALLOC_CALLS or nm.endswith(".zeros") or nm.endswith(".ones"):
                for sub in ast.walk(anc):
                    if sub is node:
                        return True
        return False


def build(src, path=""):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    return Index(tree, src, path)
