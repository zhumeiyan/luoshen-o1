"""FIXTURE - deliberately correct. Every canon rule satisfied.
evalguard must report ZERO blockers and ZERO warns on this file."""
import json, random, time, requests

SEED = 20261017
CHANCE_LEVEL = 0.25          # random baseline for a 4-way choice
POSITIVE_CONTROL_TARGET = 1.0


def sweep_thresholds(scores, labels):
    """Canon #142: sweep, do not hard-code one threshold."""
    out = {}
    for tau in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
        tp = sum(1 for s, y in zip(scores, labels) if s > tau and y == 1)
        n_pos = sum(1 for y in labels if y == 1)
        denom = max(n_pos, 1)
        out[tau] = {"tp": tp, "n_pos": n_pos, "recall": tp / denom}
    return out


def paired_diff(common, a, b):
    """Canon #419: conditions that can skip must be compared paired."""
    return [x - y for x, y in zip(a, b) if x is not None and y is not None]


def per_axis(scores):
    """Canon #421: report each axis, never only the aggregate."""
    per_axis_scores = {ax: sum(v) / max(len(v), 1) for ax, v in scores.items()}
    per_axis_scores["overall"] = sum(per_axis_scores.values()) / max(len(per_axis_scores), 1)
    return per_axis_scores


def probe(url, tries=3):
    """Canon #377: re-measure reachability, stamp it."""
    log = []
    for _ in range(tries):
        try:
            r = requests.get(url, timeout=5)
            log.append({"status_code": r.status_code,
                        "reachable": r.status_code == 200,
                        "timestamp": time.time()})
        except Exception as e:
            log.append({"reachable": False, "error": repr(e), "timestamp": time.time()})
    return log


def main():
    rng = random.Random(SEED)
    held_out = [rng.random() for _ in range(200)]
    with open("sweep.json", "w", encoding="utf-8") as f:
        json.dump(sweep_thresholds(held_out, [1] * len(held_out)), f)
    return {"ok": True}
