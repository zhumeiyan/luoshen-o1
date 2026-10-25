"""FIXTURE - deliberately broken. 16 planted defects, one per evalguard rule.
Not for execution; it exists to be linted."""
import random, json, requests

def run(conds, data):
    acc = []                                   # EG002 no baseline
    for c in conds:
        if len(data[c]) == 0:
            continue                           # EG011 skip
        r = random.random()                    # EG001 unseeded
        if r > 0.63:                           # EG003 magic threshold
            acc.append(len(data[c]) / sum(len(x) for x in data[c]))  # EG005 unguarded div
        else:
            acc.append(0)
    try:
        model.fit(data)                        # EG008 fit+eval same corpus
    except Exception:
        pass                                   # EG006 silent except
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=4)                  # EG004 single cut-off
    dead_var = len(acc)                        # EG009 assigned never read
    print("results archived")                  # EG007 claims save, no write
    hit_rate = sum(acc) / len(acc)             # EG013 ratio, no count
    print(f"accuracy={hit_rate}")              # EG012 no pos/chance control
    overall = sum(acc) / len(acc)              # EG015 aggregate, no per-axis
    resp = requests.get("https://example.com/api")   # EG016 no status/timestamp
    return {"overall": overall}


def second_broken_block(conds, axis_scores):
    """Second planted block: EG014 + EG015 defects."""
    for c in conds:
        fixed_ref = random.choice(conds)          # EG014 'fixed' regenerated in loop
        total_score = sum(axis_scores[c]) / max(len(axis_scores[c]), 1)
    return {"overall": total_score}               # EG015 aggregate, no per-axis
