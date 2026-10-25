"""Explicit anchor declarations — what syntax each rule ACCUSES (exp133).

Why this file exists
--------------------
exp130 measured: only 35.3% of findings were pinned to the code they
accuse. exp132 fixed two rules (EG002, EG016) by giving them semantic
anchors and proved each anchor against its own source.

But 20 of 22 findings still got their line from a pre-exp130 heuristic.
The reason is structural: **nothing in the codebase states what a rule is
talking about.** Each rule computes a file-level boolean and then picks a
line by whatever local variable happened to be in scope. There is no
declaration to check the line against, so "is this line the right one?" is
not a question the code can even ask.

So: declare it. Every rule now states

    node   the AST node types that constitute evidence for the claim
    keys   tokens that must occur in that node's OWN source segment
    kind   present  -> the accused thing exists; pointing at it is exact
           absent   -> the accused thing is MISSING (no baseline, no
                       re-test). There is no node. The anchor is the node
                       that carries the semantics under accusation and it
                       must still prove itself with `keys`.
           module   -> claim is about the whole file; no honest pin exists.
                       Pinning these to line 1 is the lie exp130 caught.

The declaration is a CLAIM, not a fact. `audit_anchors.py` checks every
finding against it. A rule whose findings keep failing its own spec is
either mis-declared or mis-implemented; either way it is now visible.
"""
import ast

METRIC_WORDS = ("accuracy", "acc", "recall", "precision", "f1", "hit_rate",
                "score", "bleu", "rouge", "pass@", "pass_at", "exact_match",
                "命中", "准确率")

REMOTE_TOKENS = ("requests.", "httpx.", "urlopen", "http.client", "aiohttp",
                 "socket.", "curl", "client.chat", "openai", ".create(")

STOCH_TOKENS = ("random.", "np.random", "numpy.random", "torch.", "shuffle",
                "randint", "randperm", "sample(")


def _n(*types):
    return tuple(types)


# eg_id -> dict(node=..., keys=..., kind=..., note=...)
ANCHOR_SPEC = {
    # EG000 is not a rule. It is the marker cli.py emits when it downgrades
    # findings in demo/example files and for SyntaxError. Declaring it keeps
    # it out of the "NO_SPEC" bucket, which would otherwise be read as a
    # rule that failed to declare -- a category error.
    "EG000": dict(kind="module", node=(), keys=(),
                  note="cli downgrade marker / SyntaxError, not a rule"),
    # ---------------------------------------------------------- core rules
    "EG001": dict(kind="present", node=_n(ast.Call), keys=STOCH_TOKENS,
                  note="the stochastic call itself"),
    "EG002": dict(kind="absent", node=_n(ast.Call), keys=METRIC_WORDS,
                  note="the statement that reports the metric; there is no "
                       "'missing baseline' node to point at"),
    "EG003": dict(kind="present", node=_n(ast.Compare, ast.Constant, ast.Assign),
                  keys=(), note="the comparison/constant holding the magic number"),
    "EG004": dict(kind="present", node=_n(ast.Call), keys=(),
                  note="the call site that applies the single cut-off"),
    "EG005": dict(kind="present", node=_n(ast.BinOp), keys=("/", "//"),
                  note="the division itself"),
    "EG006": dict(kind="present", node=_n(ast.ExceptHandler, ast.Try),
                  keys=("except",), note="the handler that swallows"),
    "EG007": dict(kind="module", node=(), keys=(),
                  note="absence of any write call; no node exists"),
    "EG008": dict(kind="module", node=(), keys=(),
                  note="absence of a held-out split; no node exists"),
    "EG009": dict(kind="present", node=_n(ast.Assign, ast.AnnAssign, ast.Name),
                  keys=(), note="the assignment whose target is never read"),
    "EG010": dict(kind="module", node=(), keys=(),
                  note="absence of a second metric family; no node exists"),
    "EG011": dict(kind="present", node=_n(ast.Continue, ast.Break, ast.If),
                  # exp133: declared twice, both times wrong, both times
                  # usefully wrong.
                  #  v1 node=For/While/If keys=("for ","while ","if ") ->
                  #      554/554 of those nodes contain a key: vacuous.
                  #  v2 same node, keys tightened to skipping words ->
                  #      the proof then read the loop's WHOLE body, so a
                  #      pin on the header passed via a `continue` below.
                  #  v3: the implementation now pins the skip statement
                  #      itself (exp133 fix), so the declared node is the
                  #      skip statement. A declaration that disagrees with
                  #      the implementation is the thing this file exists
                  #      to make visible -- it reported WRONG_NODE 3/3
                  #      the moment the implementation moved.
                  keys=("continue", "break", "skip", "return", "next("),
                  note="the statement that skips a case"),
    "EG012": dict(kind="absent", node=_n(ast.Call, ast.Assign, ast.Name,
                                         ast.Attribute),
                  keys=METRIC_WORDS,
                  note="the identification metric; positive control is absent"),
    "EG013": dict(kind="present", node=_n(ast.BinOp, ast.Call),
                  keys=METRIC_WORDS + ("/",), note="the ratio expression"),
    "EG014": dict(kind="present", node=_n(ast.Assign, ast.Name, ast.Call),
                  keys=("fixed", "const", "static", "seed", "base"),
                  note="the name that claims constancy"),
    "EG015": dict(kind="module", node=(), keys=(),
                  note="absence of a per-axis breakdown; no node exists"),
    "EG016": dict(kind="present", node=_n(ast.Call), keys=REMOTE_TOKENS,
                  note="the remote call whose reachability is never re-tested"),

    # ------------------------------------------------------------ pro rules
    "EGP01": dict(kind="present", node=_n(ast.Try, ast.ExceptHandler, ast.If),
                  keys=("except", "continue", "skip", "drop"),
                  note="the construct that drops failed samples"),
    "EGP02": dict(kind="present", node=_n(ast.Call, ast.Assign),
                  keys=(), note="the fit/threshold call"),
    "EGP03": dict(kind="module", node=(), keys=(),
                  note="absence of a correction call; no node exists"),
    "EGP04": dict(kind="absent", node=_n(ast.Call, ast.Assign),
                  keys=("judge", "compare", "pair", "order", "score", "vote"),
                  note="the pairwise judgement; the order swap is absent"),
    "EGP05": dict(kind="module", node=(), keys=(),
                  note="absence of a split; no node exists"),
    "EGP06": dict(kind="absent", node=_n(ast.Call, ast.Assign, ast.Name),
                  keys=METRIC_WORDS,
                  note="the reported metric; the repeat/spread is absent"),
    "EGP07": dict(kind="present", node=_n(ast.Call), keys=("load", "cache",
                  "read", "open", "json"), note="the unhashed cache load"),
    "EGP08": dict(kind="present", node=_n(ast.Assert), keys=("assert",),
                  note="the assertion that only guards the success path"),
    "EGP09": dict(kind="absent", node=_n(ast.Call, ast.Assign),
                  keys=("mean", "average", "np.mean", "sum(", "/"),
                  note="the collapse to a mean; the tail is absent"),
    "EGP10": dict(kind="present", node=_n(ast.Subscript, ast.Assign),
                  keys=("[", "response", "choices", "message", "content"),
                  note="the indexing into the model response"),
}


def spec_for(eg_id):
    return ANCHOR_SPEC.get(eg_id)


def describe(eg_id):
    s = spec_for(eg_id)
    if s is None:
        return f"{eg_id}: NO SPEC DECLARED"
    names = ",".join(t.__name__ for t in s["node"]) or "-"
    return f"{eg_id}: {s['kind']:7s} node={names:24s} keys={len(s['keys'])}"
