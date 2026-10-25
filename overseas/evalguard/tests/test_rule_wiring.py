"""Structural self-check: every rule decorator must name the function below it.

Why this test exists
--------------------
exp138 found a live bug of this exact shape in production code. The
`@rule("EG005", ...)` decorator sat at line 403; two helper functions were
later inserted between it and the real `def eg005` at line 470. Python
applies a decorator to whatever function definition comes next, so the
decorator bound to `_pathlike_names` instead.

The consequences were quiet and severe at the same time:

  * `_pathlike_names` was registered into RULES carrying EG005's meta
  * the real `eg005` was never registered and never ran
  * every scan called the helper with (tree, src, path) -> TypeError
  * cli's per-rule except downgrades a crashing rule to severity "info",
    so EG005 reported "rule error: ..." for a whole release and nobody
    saw it as an outage

A unit test of eg005's behaviour would not have caught this, because
eg005 was never reached through the public path. Only a structural check
that reads the source can. That is what this file is.

It also asserts the inverse: no rule function is left undecorated, which
is the same failure seen from the other side (a rule that silently does
not exist).
"""
import ast
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
# runnable both as a pytest module and as `python3 tests/test_rule_wiring.py`
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))


def _scan_module(fname, decorator_names):
    """Yield (eg_id, decorator_line, func_name, func_line) for each decorated def."""
    src = HERE.joinpath(fname).read_text(encoding="utf-8")
    tree = ast.parse(src)
    out = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for d in node.decorator_list:
            if not (isinstance(d, ast.Call)
                    and getattr(d.func, "id", "") in decorator_names):
                continue
            if not (d.args and isinstance(d.args[0], ast.Constant)):
                continue
            out.append((d.args[0].value, node.name, node.lineno))
    return out


def _expected_name(eg_id):
    """EG005 -> eg005, EGP01 -> egp01. Lowercased, no other change."""
    return eg_id.lower().replace("eg", "eg", 1)


def test_decorator_binds_the_named_function():
    """The decorator must sit immediately above the function it names."""
    bad = []
    for fname, decs in (("rules.py", {"rule"}), ("pro_rules.py", {"prule"})):
        for eg_id, func_name, lineno in _scan_module(fname, decs):
            if func_name != eg_id.lower():
                bad.append(f"{fname}:{lineno}  {eg_id} decorates "
                           f"def {func_name}(), expected def {eg_id.lower()}()")
    assert not bad, "decorator bound to the wrong function:\n  " + "\n  ".join(bad)


def test_every_rule_function_is_decorated():
    """No eg0xx/egpxx function may be left unregistered."""
    undecorated = []
    for fname, decs in (("rules.py", {"rule"}), ("pro_rules.py", {"prule"})):
        src = HERE.joinpath(fname).read_text(encoding="utf-8")
        tree = ast.parse(src)
        decorated = {n.name for n in tree.body
                     if isinstance(n, ast.FunctionDef)
                     and any(isinstance(d, ast.Call)
                             and getattr(d.func, "id", "") in decs
                             for d in n.decorator_list)}
        for n in tree.body:
            if not isinstance(n, ast.FunctionDef):
                continue
            if (n.name.startswith("eg") and n.name[2:3].isdigit()
                    and n.name not in decorated):
                undecorated.append(f"{fname}:{n.lineno} def {n.name}()")
    assert not undecorated, ("rule functions never registered:\n  "
                             + "\n  ".join(undecorated))


def test_registered_rules_are_callable_with_three_args():
    """The signature cli actually uses. Catches a helper registered by accident."""
    from evalguard.rules import RULES
    from evalguard.pro_rules import PRO_RULES
    for fn in list(RULES) + list(PRO_RULES):
        code = fn.__code__
        n = code.co_argcount
        assert n == 3, (f"{fn.meta.get('eg_id')} -> {fn.__name__} takes "
                        f"{n} args, cli calls it with 3 (tree, src, path)")


def test_no_duplicate_eg_ids():
    from evalguard.rules import RULES
    from evalguard.pro_rules import PRO_RULES
    seen, dupes = set(), []
    for fn in list(RULES) + list(PRO_RULES):
        eid = fn.meta.get("eg_id")
        if eid in seen:
            dupes.append(eid)
        seen.add(eid)
    assert not dupes, f"duplicate eg_id registered: {dupes}"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            fails += 1
            print(f"  FAIL  {name}\n        {e}")
    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILED'}")
    sys.exit(1 if fails else 0)
