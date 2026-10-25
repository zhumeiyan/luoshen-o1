"""Strict / loose labels for the 24 real findings, exp133.

Rule applied (same as exp131, so the numbers are comparable):
  strict  would a reviewer opening EXACTLY that line accept that this code
          has the defect the rule names?  Doubt -> FP.
  loose   does the rule's claim hold somewhere in the file? (The standard
          that let v0.3.0 ship.)

kind is the rule's own declaration from evalguard/spec.py:
  present  the accused thing exists  -> a line can show it
  absent   the accused thing is MISSING -> no line can show an absence

That last distinction is the point of this file. Scoring an absent rule
with the strict standard is not a harsh test, it is an impossible one.
"""
import json
import pathlib

# (file, eg, line, strict, loose, why)
ROWS = [
    ("EleutherAI__lm-evaluation-harness__lm_eval_evaluator.py", "EG002", 613,
     0, 1, "loop header over acc; the absence of a baseline is not visible "
           "on any line"),
    ("UKGovernmentBEIS__inspect_ai__examples_scorer.py", "EGP06", 70,
     0, 1, "`success, _ = run()` is not a metric report; also an examples/ file"),
    ("UKGovernmentBEIS__inspect_ai__examples_scorer.py", "EGP06", 64,
     0, 1, "`return score` - examples file, no spread anywhere (true) but the "
           "line shows nothing"),
    ("allenai__olmes__oe_eval_run_eval.py", "EG011", 715,
     1, 1, "pinned to the actual `continue`; the loop does skip and does "
           "aggregate"),
    ("allenai__olmes__oe_eval_run_eval.py", "EG011", 860,
     1, 1, "`continue` inside the prediction loop"),
    ("allenai__olmes__oe_eval_run_eval.py", "EGP06", 1044,
     0, 1, "loading a score, not reporting one"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EG005", 43,
     1, 1, "`count / len(samples)` - len can be 0"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EG005", 78,
     0, 0, "denominator is a sum of exp(); strictly positive unless empty"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EG005", 119,
     1, 1, "`total_brier_score / count` - count can be 0"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EG005", 244,
     1, 1, "`weighted_log_prob / len(samples)`"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EG005", 264,
     1, 1, "`weighted_prob / len(samples)`"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EG012", 198,
     0, 1, "assignment to bucket_accuracy; no positive control is an absence"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EGP08", 465,
     0, 1, "an assert, but the line does not show it only guards success"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EGP09", 313,
     0, 1, "`all([sum(...) == ...])` is not the collapse to a mean"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EGP09", 321,
     0, 1, "computes f1, does not collapse a per-sample list to a mean"),
    ("google__BIG-bench__bigbench_api_task_metrics.py", "EGP09", 417,
     1, 1, "`results['bleurt'] = np.mean(results_list)` - the collapse itself"),
    ("google__BIG-bench__bigbench_evaluate_task.py", "EGP06", 253,
     0, 1, "ScoreData construction, not a reported metric"),
    ("openai__simple-evals__drop_eval.py", "EG012", 129,
     0, 1, "f1 with a zero guard; positive control is an absence"),
    ("openai__simple-evals__drop_eval.py", "EGP06", 106,
     0, 1, "np.zeros allocation"),
    ("openai__simple-evals__drop_eval.py", "EGP09", 170,
     1, 1, "`f1 = np.mean(f1_per_bag)` - the collapse itself"),
    ("stanford-crfm__helm__scripts_heim_human_eval.py", "EG011", 190,
     1, 1, "`continue` skipping non-Batch csv files"),
    ("stanford-crfm__helm__scripts_heim_human_eval.py", "EG016", 275,
     0, 0, "MISLABELLED: the rule fired on the missing TIMESTAMP, but its "
           "title accuses a missing REACHABILITY re-test -- and the next "
           "line is `if response.status_code != 200: raise`, so reachability "
           "IS tested. Two trigger conditions share a title naming one."),
    ("stanford-crfm__helm__scripts_heim_human_eval.py", "EGP06", 213,
     0, 1, "`correct_answer = choice` - unrelated assignment"),
    ("stanford-crfm__helm__scripts_heim_human_eval.py", "EGP09", 235,
     1, 1, "`statistics.fmean(...)` over human annotations - the collapse"),
]

KIND = {"EG002": "absent", "EG005": "present", "EG011": "present",
        "EG012": "absent", "EG016": "present", "EGP06": "absent",
        "EGP08": "present", "EGP09": "present"}


def main():
    out = [dict(file=f, eg=eg, line=ln, kind=KIND.get(eg, "?"),
                strict=s, loose=l, why=w) for f, eg, ln, s, l, w in ROWS]
    p = pathlib.Path(__file__).with_name("labels133.json")
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    n = len(out)
    st = sum(r["strict"] for r in out)
    lo = sum(r["loose"] for r in out)
    print(f"findings {n}   strict TP {st} = {st/n:.1%}   "
          f"loose TP {lo} = {lo/n:.1%}")
    print()
    print(f"{'kind':9s} {'n':>3s} {'strictTP':>9s} {'rate':>7s}")
    for k in ("present", "absent"):
        sub = [r for r in out if r["kind"] == k]
        t = sum(r["strict"] for r in sub)
        print(f"{k:9s} {len(sub):3d} {t:9d} {t/max(len(sub),1):7.1%}")
    print()
    print("--- strict FP among PRESENT rules (real, fixable) ---")
    for r in out:
        if r["kind"] == "present" and r["strict"] == 0:
            print(f"  {r['eg']:6s} L{r['line']:<5} {r['why'][:66]}")


if __name__ == "__main__":
    main()
