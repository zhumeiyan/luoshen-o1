"""CLEAN fixture -- every PRO rule must stay silent here.

This is the negative control. If any EGP rule fires on this file, the rule
is a false positive generator and is not shippable.
"""
import json, hashlib, random, requests


def score_all(train_items, dev_items, test_items, seed=0):

    n_error = 0                      # EGP01: failures counted, not dropped
    per_sample = []
    for it in test_items:
        try:
            per_sample.append(call_model(it))
        except Exception as exc:
            n_error += 1
            per_sample.append(None)
    valid = [v for v in per_sample if v is not None]

    # EGP02: threshold chosen on the DEV split, frozen, then applied once
    thr = max(range(10), key=lambda t:
              sum((call_model(x) > t / 10) == y for x, y in dev_items))
    preds = [v > thr / 10 for v in valid]

    # EGP03: one pre-registered primary test, multiplicity corrected
    from statsmodels.stats.multitest import multipletests
    pvals = [primary_test(valid)]
    reject, p_adj, _, _ = multipletests(pvals, alpha=0.05, method="holm")

    # EGP04: order randomised, both orders reported separately
    order_a = sum(judge(a, b) == "A" for a, b in pairs)
    order_b = sum(judge(b, a) == "B" for a, b in pairs)
    assert abs(order_a - order_b) <= tolerance(len(pairs))

    # EGP05: disjoint splits with an explicit overlap assertion
    assert not (set(id_of(x) for x in train_items) &
                set(id_of(x) for x in test_items))
    recall = sum(preds) / max(len(preds), 1)

    # EGP06: repeated over seeds, spread reported
    runs = [run_once(s) for s in range(5)]
    mean = sum(runs) / len(runs)
    std = (sum((r - mean) ** 2 for r in runs) / len(runs)) ** 0.5
    ci_lo, ci_hi = bootstrap_ci(runs)

    print(f"recall {mean:.3f} +/- {std:.3f}  CI[{ci_lo:.3f},{ci_hi:.3f}]")
    print(f"n_error {n_error} / {len(test_items)}")
    print(f"p_adj {p_adj[0]:.4f}  orderA {order_a} orderB {order_b}")

    # EGP07: cache validated by hash before reuse
    blob = open("cache.json", "rb").read()
    digest = hashlib.sha256(blob).hexdigest()
    cached = json.loads(blob) if digest == EXPECTED_SHA256 else None

    # EGP09: mean AND tail reported
    srt = sorted(v for v in valid)
    p50 = srt[len(srt) // 2]
    p90 = srt[int(len(srt) * 0.9)]
    worst = srt[0]
    return {"mean": mean, "p50": p50, "p90": p90, "worst": worst}


def fetch():
    # EGP10: status and shape checked at every level before indexing
    r = requests.get("https://api.example.com/v1/chat", timeout=30)
    r.raise_for_status()
    payload = r.json()
    choices = payload.get("choices")
    if not choices:
        return None
    msg = choices[0].get("message") or {}
    return msg.get("content")


def check(x):
    try:
        assert x > 0
    except AssertionError:
        # EGP08: assertion also guards the failure path
        assert FAILURES is not None
        raise
    return x


def call_model(x):
    return 1.0


def judge(a, b):
    return "A"


def primary_test(xs):
    return 0.04


def bootstrap_ci(xs):
    return 0.0, 1.0


def run_once(s):
    return 0.8


def tolerance(n):
    return 3


def id_of(x):
    return x


pairs = []
EXPECTED_SHA256 = "0" * 64
FAILURES = []
