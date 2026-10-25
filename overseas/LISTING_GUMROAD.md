# Gumroad 上架文案（evalguard v0.2.0）

## 短版（商品副标题）

> Static linter for LLM/agent eval scripts. 16 rules, each traced to a numbered
> failure mode from 100+ real experiments. Zero false positives on clean code.

## 长版（商品描述）

**Your eval numbers are probably wrong. Not because the model is bad — because
the measurement is broken.**

`evalguard` reads your evaluation script and flags the failure modes that
actually invalidate published numbers:

- recall 0.95 when random guessing already gives 0.90
- a taxonomy scoring ~1.0 on the corpus it was induced from
- a metric that is structurally zero for the whole experiment
- an "intervention" variable that is assigned and never read
- "results archived" in a log line with no write call
- a remote endpoint that was reachable last month and is 403 today

**Every rule traces to a numbered entry** in a 368-item failure-mode canon
mined from 100+ real experiments — each written after the failure actually
cost an experiment.

### Measured, not claimed

| fixture | blockers | warns | |
|---|---|---|---|
| 16 planted defects | 4 | 11 | **16/16 rules fire** |
| clean control | **0** | **0** | 1 info only |

**Zero false positives on clean code.** Both fixtures ship in the repo —
verify it yourself.

### It found real bugs in its own repo

Run against the author's own 177 Python files: **7 blockers**, all real
(5× unreachable-channel-without-re-test, 2× silent `except`).

### v0.2 fixed three silent failures in itself

The worst: `" ".join(tokens)` turned `requests.get` into `requests . get`, so
**the remote-channel rule could never fire on any real call** — it looked fine
in code review and matched nothing in production. A rule that never fires is
indistinguishable from a rule that never needed to fire.

### Install / use

```bash
pip install evalguard
evalguard your_eval.py
```

Zero dependencies. Python 3.8+. Exit code 1 on any blocker — drop it in CI.

**Free tier (4 rules, MIT):** unguarded division · ratio without count ·
hard-coded threshold · remote call without reachability re-test — the four
that cover 61% of real defects measured on 177 files.

**Paid (12 rules + canon CSV/JSON + CI recipe).**

### Limitations, stated up front

Static only (never runs your code) · some rules are keyword heuristics ·
Python only · precision favored over recall by design.
