# exp136 — preregistered before running (2026-10-18)

## Question
exp135 found the gate is one-sided: six rounds gated on precision only.
Result: 90% precision, and 0.02-0.03 findings/KB on professional eval
frameworks (9 of 12 files silent). The 3 shipped rules are generic Python
syntax defects, not eval-specific ones. So the mute result may be a
*domain* artefact, not a rule-quality artefact.

## Hypothesis (H1)
On non-eval Python code the 3 shipped syntax rules fire at >= 0.05
findings/KB, i.e. >= 2x the eval-framework rate (0.024/KB, exp135).

## Hypothesis (H2)
Strict precision on the new domain still clears the ship gate: point
estimate >= 0.60. Wilson CI is reported and the gate FAILS if the lower
bound is below 0.60, regardless of the point estimate.

## Hypothesis (H3)
Recall on the syntax minefield does not regress: EG005 3/3, EG006 2/2,
EGP01 1/1, clean file 0.

## Corpus definition (fixed before fetch)
7 repositories never used in exp129-135, from non-eval domains
(web framework, HTTP client, scraping, task queue, CLI, downloader, API).
Per repo: drop paths matching eval|metric|benchmark|score|test|__init__|
vendor|contrib|example, then take 2 files at random with seed 136.
That exclusion is deliberate: these corpora exist to measure the tool on
code it was NOT tuned on, and eval-named files would blur the domain split.

## Judging
One judge (me), same rule as exp131+: doubtful counts as FP. Every finding
is quoted with source text and a reason. Both standards reported.
