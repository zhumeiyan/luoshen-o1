"""Is each rule's key set DISCRIMINATING? (exp133, part 2)

`audit_anchors.py` reported 21/31 findings PROVEN. That number is only
meaningful if failing the key test is *possible*. If a rule's keys occur
in ~100% of nodes of the declared type, then "PROVEN" is vacuous: every
line of that kind would pass.

This is the same saturation test applied throughout the canon (#23, #145):
a criterion that cannot produce False is not a criterion.

For every rule: walk all nodes of its declared type across the whole
corpus, measure what fraction contain one of its keys.
  ~0%   -> keys never occur; the rule can never prove an anchor
  ~100% -> keys occur everywhere; the proof is vacuous
  middle-> keys discriminate; PROVEN means something
"""
import ast
import collections
import pathlib
import sys

sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard.spec import ANCHOR_SPEC  # noqa: E402

CORPUS = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/corpus2")


def seg(src, node):
    """v1 called ast.get_source_segment per (rule, node): O(rules x nodes)
    with a fresh line-index scan each call -- it timed out on 27 files.
    Slice the cached line list instead (canon #23: a slow measurement that
    never finishes produces no evidence at all)."""
    lines = SEG_CACHE[id(src)]
    a = getattr(node, "lineno", 0) or 0
    b = getattr(node, "end_lineno", a) or a
    try:
        return "\n".join(lines[a - 1:b])
    except Exception:
        return ""


SEG_CACHE = {}


def main():
    files = sorted(CORPUS.glob("*.py"))
    pool = collections.defaultdict(list)   # eg -> [(node, src)]
    # one pass over nodes per file, not one pass per rule
    type_map = collections.defaultdict(list)   # node type -> eg_ids
    for eg, s in ANCHOR_SPEC.items():
        for t in s["node"]:
            type_map[t].append(eg)
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        SEG_CACHE[id(src)] = src.splitlines()
        for n in ast.walk(tree):
            for t, egs in type_map.items():
                if isinstance(n, t):
                    for eg in egs:
                        pool[eg].append((n, src))

    print(f"{'eg':7s} {'pool':>6s} {'withkey':>8s} {'rate':>7s}  verdict")
    print("-" * 62)
    rows = []
    for eg in sorted(ANCHOR_SPEC):
        s = ANCHOR_SPEC[eg]
        items = pool.get(eg, [])
        if not s["node"]:
            print(f"{eg:7s} {'-':>6s} {'-':>8s} {'-':>7s}  module (no node declared)")
            continue
        keys = tuple(k.lower() for k in s["keys"])
        if not keys:
            print(f"{eg:7s} {len(items):6d} {'-':>8s} {'-':>7s}  NO KEYS -> vacuous")
            rows.append((eg, len(items), None))
            continue
        n_key = sum(1 for n, src in items if any(k in seg(src, n).lower()
                                                 for k in keys))
        rate = n_key / max(len(items), 1)
        # exp133: v1 labelled rate<2% "DEAD (can never prove)". That is
        # wrong. A LOW rate means the key is selective -- few nodes pass,
        # so a node that DOES pass is strong evidence. Only rate==0 is
        # impossible, and only a HIGH rate is vacuous. v1's threshold
        # would have called the best key sets broken and the worst ones
        # fine.
        if rate == 0.0:
            v = "IMPOSSIBLE (no node can prove)"
        elif rate > 0.95:
            v = "SATURATED (proof is vacuous)"
        elif rate > 0.60:
            v = "weak"
        else:
            v = "discriminating"
        print(f"{eg:7s} {len(items):6d} {n_key:8d} {rate:7.1%}  {v}")
        rows.append((eg, len(items), rate))
    print()
    dead = [e for e, n, r in rows if r is not None and r == 0.0]
    sat = [e for e, n, r in rows if r is not None and r > 0.95]
    nokey = [e for e, n, r in rows if r is None]
    print("DEAD key sets      :", dead or "none")
    print("SATURATED key sets :", sat or "none")
    print("NO keys declared   :", nokey or "none")


if __name__ == "__main__":
    main()
