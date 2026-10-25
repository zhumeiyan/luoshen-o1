"""Clean evaluation script — nothing should fire here."""
import json
import random

SEED = 20261020
THRESHOLD = 0.5


def majority_baseline(gold):
    counts = {}
    for g in gold:
        counts[g] = counts.get(g, 0) + 1
    return max(counts.values()) / len(gold)


def evaluate(preds, gold):
    random.seed(SEED)
    assert len(gold) > 0, "gold is empty"
    hit = sum(1 for p, g in zip(preds, gold) if p == g)
    acc = hit / len(gold)
    base = majority_baseline(gold)
    result = {"accuracy": acc, "baseline": base,
              "lift": acc - base, "n": len(gold), "hits": hit}
    with open("result.json", "w") as f:
        json.dump(result, f)
    return result


print(evaluate([1, 0, 1, 1], [1, 0, 0, 1]))
