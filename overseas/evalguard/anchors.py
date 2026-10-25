"""Semantic anchors — where a finding's *evidence* lives (exp132).

Why this module exists
----------------------
Before exp132 a rule made a **file-level** boolean decision (does the word
"baseline" occur anywhere in the de-commented source?) and then asked a
*separate* heuristic for a line number::

    ln = _metric_line(tree, src) or 1          # "first print() in the file"

The heuristic had no logical connection to the rule's own judgement, so it
picked whatever emit call happened to come first. In `lm_eval/evaluator.py`
that is `eval_logger.info("Setting verbosity to ...")`. A reader who opens
that line finds nothing to do with accuracy and throws away a finding that
is true at file level.

exp130 measured this: after forcing "line > 1", only **35.3%** of findings
were pinned to the code they accuse. 64.7% were pinned to something else.

The rule here: **a finding's line must come from the syntax node the rule
is actually talking about.** Not from a nearby emit call, not from line 1.

Two shapes of rule
------------------
present   The rule accuses a node that EXISTS (a division, a bare except,
          a remote call). Its line is `node.lineno`. Unambiguous.

absent    The rule accuses something that is MISSING (no baseline, no
          reachability re-test). There is no node to point at. exp130
          called these "legitimately cannot point at a symbol" and let them
          fall back to an anchor. That fallback was the bug: it used the
          nearest emit call, which is unrelated.

          The honest shape for an absent rule is:

              anchor  = the node that *carries the semantics under accusation*
                        (for EG016: the `requests.get(...)` call itself)
              proof   = the anchor's own source must contain the keyword the
                        rule keys on. If it does not, the anchor is not
                        evidence for this claim and the finding must be
                        reported at module level, not pinned anyway.

`resolve()` enforces the proof step. A rule that cannot prove its anchor
gets `kind="module"` and the CLI prints "(module)" rather than a line that
sends the reader to the wrong place.

A module-level finding is *worse* than a pinned one — that is the point.
We would rather report 3 weak findings honestly than 17 findings whose
lines are wrong.
"""
import ast
import re

METRIC_WORDS = ("accuracy", "acc", "recall", "precision", "f1", "hit_rate",
                "score", "bleu", "rouge", "pass@", "pass_at", "exact_match",
                "命中", "准确率")

REMOTE_CALLS = (("requests", ("get", "post", "put", "request", "head")),
                ("httpx", ("get", "post", "put", "request", "stream")),
                ("urllib.request", ("urlopen",)),
                ("http.client", ("HTTPConnection", "HTTPSConnection")),
                ("aiohttp", ("get", "post", "request")),
                ("socket", ("create_connection",)))


def _seg(src, node):
    try:
        return ast.get_source_segment(src, node) or ""
    except Exception:
        return ""


def _dotted(node):
    """`requests.get` -> "requests.get" ; `urlopen` -> "urlopen"."""
    f = getattr(node, "func", None)
    if f is None:
        return ""
    if isinstance(f, ast.Attribute):
        base = getattr(f.value, "id", "") or ""
        return (base + "." + f.attr).lower()
    return (getattr(f, "id", "") or "").lower()


def remote_calls(tree):
    """Every call node that performs a real remote request."""
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        d = _dotted(n)
        if not d:
            continue
        for mod, meths in REMOTE_CALLS:
            for m in meths:
                if d == (mod + "." + m).lower() or d == m:
                    if d == m and m not in ("urlopen", "create_connection",
                                            "HTTPConnection".lower(),
                                            "HTTPSConnection".lower()):
                        continue
                    out.append(n)
    # `curl` in a subprocess is also a remote channel
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            a = n.args
            if a and isinstance(a[0], ast.Constant) \
                    and isinstance(a[0].value, str) and "curl" in a[0].value:
                out.append(n)
    return out


def metric_calls(tree, src):
    """Call nodes that emit a value AND mention a metric word in their own
    source. `logger.info("GPU memory: ...")` is excluded because it names no
    metric — that exclusion is the whole point of exp132."""
    # exp132 v1 BUG, kept in the record: the emitter list contained `append`.
    # `acc["logged_samples"].append(example)` then qualified as "the statement
    # that reports the metric" and beat the true line `example.update(metrics)`
    # -- collecting a sample is not reporting a metric. That was the corpus's
    # only strict true positive (exp131 labels n=1) and v1 downgraded it.
    # Classifying by *call name* was the wrong axis: real code reports metrics
    # in ways no fixed list of method names covers. The stable signal is the
    # metric word; the call name only sets priority.
    EMIT = ("print", "info", "warning", "debug", "error", "log", "dump",
            "dumpjson", "writerow", "to_csv", "save", "write", "update",
            "report", "record", "emit")
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        seg = _seg(src, n).lower()
        if not any(w in seg for w in METRIC_WORDS):
            continue
        d = _dotted(n)
        rank = 0 if (d.split(".")[-1] if d else "") in EMIT else 1
        out.append((rank, n))
    out.sort(key=lambda t: (t[0], t[1].lineno))
    return [n for _, n in out]


def resolve(rule_id, nodes, src, key_words, host_kind):
    """Turn candidate evidence nodes into a pin decision.

    Returns (kind, line, hit_text) where kind is
      "node"    pinned to a proven evidence node
      "module"  the claim holds at file level but no node proves it

    `key_words` are the tokens the rule keys on. A node only qualifies as
    evidence if its own source segment contains one of them. This is the
    self-check that was missing: without it, any nearby call "works" as an
    anchor and the reader is sent to the wrong line.
    """
    best, best_seg = None, ""
    for n in nodes:
        seg = _seg(src, n)
        if not seg.strip():
            continue
        low = seg.lower()
        if key_words and not any(w in low for w in key_words):
            continue
        if best is None or n.lineno < best.lineno:
            best, best_seg = n, seg
    if best is not None:
        return ("node", best.lineno, best_seg.strip()[:70])
    # No node proves the claim. Fall back to *any* node of the host kind so
    # the reader at least lands on the relevant construct, but mark it
    # unproven; if there is none either, report at module level.
    if nodes:
        n = sorted(nodes, key=lambda x: x.lineno)[0]
        return ("module", None, _seg(src, n).strip()[:70])
    return ("module", None, f"file-level: {host_kind} present, "
                            f"no {' / '.join(key_words) or 'evidence'} in any "
                            f"single statement")
