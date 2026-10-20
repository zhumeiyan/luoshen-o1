import json

def evaluate(preds, gold):
    hit = sum(1 for p, g in zip(preds, gold) if p == g)
    acc = hit / len(gold)
    print(json.dumps({"accuracy": acc}))
    return acc

if __name__ == "__main__":
    evaluate([1, 0, 1, 1], [1, 0, 0, 1])
