def load(path):
    try:
        with open(path) as f:
            return [l.strip() for l in f]
    except:
        return []

rows = load("data.tsv")
print("loaded", len(rows))
