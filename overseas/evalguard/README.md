# evalguard

**Static linter for LLM / agent evaluation scripts.**

Every rule traces to a numbered entry in a **368-item failure-mode canon** —
entries mined from 100+ real experiments, each one written after the failure
actually cost an experiment. Not style preference. Not opinion.

```
$ evalguard my_eval.py

[BLOCK] EG002  canon #140  Accuracy/recall reported with no random baseline
[BLOCK] EG016  canon #377  External channel used with no reachability re-test
[WARN ] EG011  canon #419  Cases can skip, but results compared as group rates
[WARN ] EG013  canon #40   Ratio reported without numerator count + denominator

4 blocker · 11 warn · 1 info
```

Exit code is `1` when any **blocker** fires — drop it into CI.

---

## Why this exists

Most published agent-eval numbers are not wrong because the model is bad.
They are wrong because the *measurement* is broken in a way nobody checks for:

| symptom | what it actually was |
|---|---|
| recall 0.95 | random guessing already gave 0.90 |
| taxonomy scores ~1.0 | scored on the corpus it was induced from |
| every condition compares equal | the metric was structurally zero all along |
| "intervention works" | the intervention variable was never read |
| results archived | a log line said so; nothing was written |
| channel works | it was reachable last month, it is 403 today |

Each row in this table cost a real experiment. Each is now a rule.

## Install

Zero dependencies. Python 3.8+.

```bash
pip install evalguard
# or, no install at all:
git clone https://github.com/zhumeiyan/evalguard && cd evalguard
python3 -m evalguard your_eval.py
```

## Usage

```bash
evalguard path/to/eval.py        # single file
evalguard src/                   # directory (recursive *.py)
evalguard src/ --format json     # machine-readable, for CI
evalguard src/ --severity warn   # suppress info-level advice
```

## Rules (16)

| ID | Sev | Canon | Catches |
|----|-----|-------|---------|
| EG002 | blocker | #140 | metric reported with no chance-level baseline |
| EG006 | blocker | #23 | bare/silent `except` — error swallowed, run looks clean |
| EG008 | blocker | #139 | recall measured on the corpus the rules came from |
| EG016 | blocker | #377,#378 | remote call with no status re-check or timestamp |
| EG001 | warn | #141 | `random.*` / `np.random` with no seed anywhere |
| EG003 | warn | #142 | decision threshold hard-coded, no sweep |
| EG004 | warn | #43 | single hard-coded cluster cut-off, no sweep |
| EG005 | warn | #145,#35 | division with an unguarded denominator |
| EG007 | warn | #53 | "saved / archived" claimed in a log line, no write call |
| EG009 | warn | #23 | assigned-never-read variable (dead intervention) |
| EG011 | warn | #419 | cases can skip, results still compared as group rates |
| EG012 | warn | #424 | no positive control / no chance-level anchor |
| EG013 | warn | #40 | ratio reported without absolute count and denominator |
| EG014 | warn | #125 | value named `fixed`/`const` regenerated inside the loop |
| EG015 | warn | #421 | multi-axis system reported as one aggregate score |
| EG010 | info | #147 | one metric family carries the whole conclusion |

## Measured behaviour

Validated against two fixtures, both shipped in `tests/`:

| fixture | blockers | warns | verdict |
|---|---|---|---|
| `planted_eval.py` (16 planted defects) | 4 | 11 | **16 / 16 rules fire** |
| `clean_eval.py` (written to satisfy every rule) | **0** | **0** | 1 info only |

**Zero false positives on clean code.** A linter that fires on every file is a
linter nobody runs. Both fixtures are in the repo — verify it yourself.

`python3 tests/run_tests.py` → 6/6 (zero-dependency runner; pytest not required).

## Honest numbers: run against its own author's code

```
core/    3 files   0 blocker   3 warn    (1.00 warn/file)
tools/  15 files   7 blocker   8 warn    (0.53 warn/file)
```

The tool is not clean on the repo it came from. The 7 blockers are 5× EG016
(remote calls without a status re-check) and 2× EG006 (silent `except`) —
**both real defects in experiment scripts, not lint noise.** Reported as-is.

## Bugs this tool found in itself (v0.2)

Three silent failures, all caught by scanning the canon against the rules:

1. **`re` was never imported.** The comment-stripping fallback raised
   `NameError` instead of working. (canon #23)
2. **`" ".join(tokens)` destroyed every dotted name.** `requests.get` became
   `requests . get`, so **EG016 could never fire on any real remote call**,
   and every `np.mean` / `json.dump` keyword was dead. The rule looked fine
   in code review and matched nothing in production. Fixed by preserving
   token positions with `tokenize.untokenize`.
3. **Guards written one line earlier were invisible.** `denom = max(n, 1)`
   then `tp / denom` was flagged as unguarded — a false positive on correct
   code. Fixed by resolving the denominator at its assignment site.

Bug 2 is the important one: **a rule that never fires is indistinguishable
from a rule that never needed to fire.** Both look like a clean run.

## Where the canon came from

368 entries. Each carries the experiment that produced it, the measured
number, and — where one exists — an actionable criterion. 144 are
directly actionable; 16 of those are executable as static rules today.
The canon ships free under CC BY 4.0 in `../canon/`.

## Limitations (stated up front)

- **Static only.** It reads source, never runs it. It cannot know whether a
  metric is *numerically* zero, only that nothing checks.
- **Heuristic keyword matching on some rules** (EG002, EG007, EG011–EG016).
  They look for evidence of the right practice, not proof of it.
- **Python only.** No JS / notebook support yet.
- **Precision over recall by design.** A missed defect costs you a re-run;
  a false alarm costs you the tool.

## License

MIT for this tool. The failure-mode canon is CC BY 4.0, attribution KLameng.
