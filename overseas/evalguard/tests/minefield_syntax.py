"""Syntax-layer minefield (exp134).

Why a separate fixture: the existing minefields plant METHODOLOGY bugs --
no baseline, no held-out, no spread. So "recall 12/12" was measured only on
the rule class that exp134 showed does not generalise. It could never have
caught a regression in the syntax rules.

PLANTED (4 syntax defects, one per shipped rule):
  score_a  L15  unguarded division
  score_b  L21  bare except
  score_c  L31  silent handler inside scoring loop
  score_c  L32  unguarded division
  pairwise L37  no order swap

exp134 NOTE: the first version of this file carried inline comments naming
each rule ("# EG006: bare except"). EG006 reads the author's annotation
around the handler to decide the swallow is deliberate, so the comment that
DESCRIBED the planted bug is what silenced the rule that should catch it.
Four occurrences of that same failure mode are already in the canon (#23).
Comments here therefore describe intent, never rule ids.
"""
def score_a(preds, golds):
    hits = sum(1 for p, g in zip(preds, golds) if p == g)
    return hits / len(golds)

def score_b(preds, golds):
    try:
        return sum(preds) / len(golds)
    except:
        pass

def score_c(items):
    total, ok = 0, 0
    for it in items:
        try:
            ok += 1 if it["gold"] == it["pred"] else 0
            total += 1
        except:
            pass
    return ok / total

def pairwise_judge(judge, a, b):
    return judge(a, b)
