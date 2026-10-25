"""Rule classes (exp134) — WHY this file exists.

exp129-133 were all spent fixing one question: is the finding pinned to the
right line? On an independent corpus (exp134, 7 repos never used before)
that question turned out to be the wrong one. Splitting the findings by
rule instead of by pin gave a much cleaner separation:

    syntax rules       EG005 EG006 EGP01 EGP04   15/16 strict true = 93.8%
    methodology rules  everything else            1/29 strict true =  3.4%

A syntax rule asserts a property of a *node*: this division has no guard,
this except is bare, this handler is silent. The evidence is in the node,
a reviewer can confirm it in one look, and it generalises to code nobody
has ever shown us.

A methodology rule asserts a property of a *study*: no baseline, no
held-out set, no spread, no order swap. On real code these fired on metric
libraries and framework plumbing, where the object under accusation does
not exist. The claim was literally true (loose 89.7%) and practically
false (strict 3.4%).

We already learned this once: exp131 showed the loose standard is exactly
what let v0.3.0 ship at 11% precision. So methodology rules are NOT
shipped. They remain available behind METHODOLOGY_ON for research use and
are excluded from the ship gate.
"""
SYNTAX = {"EG005", "EG006", "EGP01"}
# EGP04 scored 1/1 strict on exp134, but n=1. Promoting a rule into the
# shipped set on one sample is over-fitting to that sample; it stays
# experimental until a third corpus gives it a real denominator.
EXPERIMENTAL_1_OF_1 = {"EGP04"}
METHODOLOGY_ON = [False]

def cls_of(eg_id):
    return "syntax" if eg_id in SYNTAX else "methodology"

def shipped(eg_id):
    """Is this rule part of the sellable product?"""
    return cls_of(eg_id) == "syntax" or METHODOLOGY_ON[0]
