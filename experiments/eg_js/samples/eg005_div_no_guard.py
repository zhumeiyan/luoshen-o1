def macro_f1(tp, fp, fn):
    prec = tp / (tp + fp)
    rec = tp / (tp + fn)
    return 2 * prec * rec / (prec + rec)

print(macro_f1(3, 0, 1))
