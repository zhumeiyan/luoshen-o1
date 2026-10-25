"""PLANTED fixture -- contains exactly 10 seeded defects, one per PRO rule.

This file is intentionally broken. It is the positive control for the PRO
pack: every EGP rule must fire here at least once.
"""
import json, random, requests


def score_all(items, labels):

    good = []
    # EGP01: bare except + continue inside the scoring loop
    for it in items:
        try:
            good.append(call_model(it))
        except Exception:
            continue

    # EGP02: threshold picked by looking at the evaluation labels
    best = max(range(10), key=lambda t: sum(
        (call_model(x) > t / 10) == y for x, y in zip(items, labels)))

    # EGP03: five separate significance tests, no correction
    from scipy.stats import ttest_ind
    pvals = [ttest_ind(good[i::2], good[1::2]).pvalue for i in range(5)]

    # EGP04: judge A vs B, A always presented first
    wins = sum(judge(a, b) == "A" for a, b in pairs)

    # EGP05: same source loaded for train and for evaluation
    train = json.load(open("all.json"))
    test = json.load(open("all.json"))
    recall = sum(g in test for g in good) / len(test)

    # EGP06: one seed, one run, no spread
    random.seed(0)
    print("recall", recall, "wins", wins, "p", min(pvals))

    # EGP07: cache reused with no hash
    cached = json.load(open("cache.json"))

    # EGP09: mean over per-sample scores, no tail
    return sum(good) / len(good)


def fetch():
    # EGP10: deep index into a response with no shape check
    r = requests.get("https://api.example.com/v1/chat", timeout=30)
    return r.json()["choices"][0]["message"]["content"]


def check(x):
    assert x > 0
    return x


def call_model(x):
    return 1.0


def judge(a, b):
    return "A"


pairs = []
