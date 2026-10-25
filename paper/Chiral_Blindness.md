# Chiral Blindness: Why Detectors Cannot See Their Own Mirror

**Authors:** Luoshen (autonomous research system), KLameng (corresponding)
**Affiliation:** Luoshen-O1 Laboratory
**Date:** 2026-10-18
**Status:** Preprint draft. All numbers traceable to `result*.json` in the accompanying repository.

---

## Abstract

We identify a failure mode in which a monitoring system's *representation*, not its accuracy or its training budget, determines whether it can detect a mirrored version of the system it monitors. We call this **chiral blindness**.

We define a mirror operator as an involution that **preserves the multiset of a signal's components while reversing their arrangement**. Because such an operator is invisible to any representation that discards arrangement, a detector using an arrangement-invariant (achiral) representation has **discriminability exactly zero** against the mirror — not low, but identically zero, independent of sample size.

We measure this with a single statistic, **discriminability `disc = TPR − FPR`**, and show that conventional metrics conceal it: a bag-of-words detector achieves **TPR = 1.0000** against a semantic mirror, which under a naive escape-rate definition (`1 − TPR`) reads as "perfect detection" while its FPR is simultaneously 1.0000 and its `disc` is exactly 0.0000.

Three independent domains reproduce the same structure:

1. **Semantic** (Exp. 139): bag-of-words `disc = 0.0000` (degenerate) vs. order-bearing representation `disc = 1.0000`, on identical mirror pairs.
2. **Viability** (Exp. 125): a drip-fed agent scores survival **16/16**, strictly higher than the self-foraging agent's 13/16, while its self-sufficiency `fg = 0.000` and it dies in **0/12** upon withdrawal. Survival is an achiral statistic here.
3. **Tooling** (Exp. 129–137): syntactic-layer precision **18/20 = 90%** vs. methodological-layer precision **1/55 = 1.8%** across two independent corpora (corpus3: 0/29; corpus4: 0/26), where 54 of 55 methodological accusations target objects that do not exist in the audited code.

We further show that **model collapse and chiral symmetry breaking are the same dynamical object**: replacing a data pool with model output drives the rarest class from 0.005 to 0.000 and locks the dominant class to 1.000, while accumulating output onto the retained pool keeps all five classes alive (rarest 0.028 → 0.003, zero extinctions). Spontaneous symmetry breaking occurs in **120/120** runs from a fully symmetric start (χ₀ = 0), with terminal handedness split 56 L / 64 R (z = −0.730, no directional bias).

We argue that any verification loop whose judge shares the representation family of the judged system is structurally blind to the mirror state, and that the only non-blind checks are those whose signal does not pass through the system under test.

**Keywords:** chiral blindness, mirror state, discriminability, model collapse, homochirality, self-verification, agentic cascade

---

## 1. Introduction

A recurring pattern in deployed AI systems is that self-monitoring degrades in a way that no accuracy metric predicts. The monitor keeps reporting; its reports stay internally consistent; and the failure it was built to catch is precisely the one it never names.

We argue this is not a tuning failure. It is a **representation** failure with a specific geometry.

Consider a signal composed of parts. Define a **mirror operator** `M` as an involution (`M² = I`) that **preserves the multiset of parts and reverses their arrangement**. In natural language: swapping subject and object. In a viability signal: preserving energy while inverting capability. In an audit: preserving the complaint while inverting the object it refers to.

The operator is invisible to any representation `φ` that is invariant to arrangement, because `φ(x) = φ(Mx)` by construction — the two inputs are the *same element* in the representation space. No amount of data, training, or threshold tuning can separate them, because there is nothing to separate.

This yields our central claim:

> **Chiral blindness: a detector can see `x` and be exactly blind to `Mx`, and every statistic computed on `x` alone will report the detector as healthy.**

### 1.1 Why existing metrics hide it

Precision, recall, and accuracy are all computed on one side of the mirror. If a detector assigns every input the same label, recall on the positive class is **1.0**. Under the intuitive definition "escape rate = 1 − TPR", a degenerate classifier scores **0.000** escape — the best possible number — while in fact detecting nothing.

We therefore adopt:

```
disc = TPR − FPR        (discriminability)
```

with an explicit degeneracy flag: `degenerate = 1` when the number of distinct predicted classes is 1. `disc ∈ [−1, 1]`; `disc = 0` with `degenerate = 1` means the detector is not merely wrong, it is **not discriminating at all**.

This is not a novel statistic (it is Youden's J). Our contribution is showing that **its zero-crossing is the signature of a representation defect, not a threshold defect**, and that the standard practice of reporting recall or precision alone systematically conceals the defect.

---

## 2. Related Work

**Model collapse.** Shumailov et al. (Nature, 2024) establish that training on model-generated data degrades or collapses subsequent models, driven by compounding of statistical approximation error, functional expressivity error, and functional approximation error; tails are lost first. Gerstgrasser et al. show that **accumulating** rather than replacing prevents collapse. Our §5 reproduces both regimes with an independent minimal model and quantifies the tail order.

**Homochirality.** Frank (1953) proposed that autocatalysis plus mutual antagonism amplifies a vanishing initial enantiomeric excess to dominance. Soai et al. (1995) demonstrated this experimentally in the Soai reaction. Kagan and Soai were awarded the 2026 Nobel Prize in Chemistry for this line of work. Our §6 implements Frank's three conditions and recovers both driven amplification (χ₀ = 10⁻⁵ → 1.0) and spontaneous breaking (120/120 from χ₀ = 0).

**Mirror life.** A 38-author Science policy forum (2024) warns that mirror bacteria would evade essentially all chirality-mediated immune mechanisms and phage predation, and concludes they should not be created. Our framing borrows the central structural insight: **a recognition system that is itself chiral cannot bind the mirror**. We make no biological claim about AI systems.

**Agentic cascade.** OWASP Agentic Top 10 (2026) lists cascading failure (ASI08), noting that by the third hop an initial error has been laundered into "system knowledge," gaining authority at each hop. Our §7 supplies a measurement of how the laundering becomes undetectable.

**Self-verification limits.** We are not the first to note that model self-evaluation is unreliable. Our contribution is a *structural* account: unreliability is not a matter of degree but a consequence of shared chirality between judge and judged.

---

## 3. The Mirror Operator and Its Detection

Let `S` be a signal space and `M: S → S` a mirror operator with `M² = I` and `π(Mx) = π(x)`, where `π` is the component-multiset projection.

Let `φ: S → R` be a representation. Call `φ` **achiral** if `φ ∘ M = φ` and **chiral** otherwise.

**Proposition 1 (blindness).** For any achiral `φ`, any decision rule `f: R → {0,1}` satisfies `f(φ(x)) = f(φ(Mx))` for all `x`. Hence `TPR = FPR` and `disc = 0`.

*Proof.* Immediate: `φ(Mx) = φ(x)`, so `f` receives identical arguments. ∎

The consequence is that **no choice of `f`, no training set size, and no threshold can raise `disc` above zero** while `φ` remains achiral. The remedy is not a better classifier; it is a representation that carries arrangement.

**Operational test.** Given a suspected mirror pair, compute `disc` under the deployed representation and under one enriched with arrangement. If the former is 0 with `degenerate = 1` and the latter is 1.0, the deployed monitor is chirally blind to that mirror.

---

## 4. Experiment 1: Semantic Mirror (Exp. 139)

### 4.1 Setup

Sentences generated from a controlled grammar. Mirror pairs are produced by swapping subject and object, **preserving the exact word multiset**:

```
NORMAL   系统 [不] 读取 文件 到本地
MIRROR   文件 [不] 读取 系统 到本地
```

Both contain the identical bag of tokens. Only arrangement differs.

Two representations:
- **BOW** — bag of words, arrangement discarded (achiral).
- **POS** — words plus adjacent bigrams (chiral).

Two operator families:
- **MIRROR (swap, multiset-preserving)** — the mirror test.
- **CONTROL (negation, multiset-changing)** — a control where BOW *should* succeed, to prove the failure is specific to the mirror and not general incompetence.

### 4.2 Results

| Operator | Representation | TPR | FPR | acc | **disc** | degenerate |
|---|---|---|---|---|---|---|
| MIRROR | BOW (achiral) | 1.0000 | 1.0000 | 0.50 | **0.0000** | 1 |
| MIRROR | POS (chiral) | 1.0000 | 0.0000 | 1.00 | **1.0000** | 0 |
| CONTROL | BOW (achiral) | 0.6600 | 0.3400 | 0.66 | **0.3200** | 0 |
| CONTROL | POS (chiral)  | 0.6600 | 0.3400 | 0.66 | **0.3200** | 0 |

Three readings:

1. **BOW's `disc` is exactly 0 against the mirror**, and it is flagged degenerate (one distinct predicted class). It does not misclassify the mirror; it does not see it.
2. **BOW is not generally broken**: on the multiset-changing control it achieves `disc = 0.3200`, identical to POS. The deficit is specific to the mirror. This is the control that keeps the claim from being "BOW is bad."
3. **POS reaches `disc = 1.0000`.** Arrangement information is sufficient.

### 4.3 The metric trap

Under the intuitive escape-rate definition `escape = 1 − TPR`, the BOW/mirror cell reports:

```
escape = 1 − 1.0000 = 0.0000     ← "perfect"
```

This is the single most dangerous number we produced in six rounds of auditing. It was avoided only because we additionally recorded `FPR` and `degenerate`. **We report this because we initially used the one-sided definition and would otherwise have published it.**

### 4.4 Operator sweep

Across four operators (NEG polarity flip, SWAP argument mirror, REV full inversion, ROLE surface control), the achiral representation produced flip-rate 0.0000 in all four; the chiral representation produced 1.0000 for NEG and 0.3050 for REV. Notably **SWAP yields flip 0.0 even under POS** in the free-generation setting — the detector simply never produces the mirrored form — which is a distinct and arguably more insidious blindness: not "cannot distinguish" but "never generates the alternative."

---

## 5. Experiment 2: Collapse as Homochiralization (Exp. 139B)

### 5.1 Setup

A five-class population with initial proportions (0.40, 0.30, 0.18, 0.08, 0.04). Two regimes:

- **REPLACE** — the training pool is replaced by model output each generation.
- **ACCUMULATE** — model output is added to a pool that retains the original data.

Nonlinearity parameter γ multiplies the fitness-to-sampling exponent.

### 5.2 Results

**Binary case (initial ≈ 0.48):**

| Regime | γ | initial | final | extinct |
|---|---|---|---|---|
| REPLACE | 1.0 | 0.4683 | 0.5533 | 0 |
| REPLACE | 1.6 | 0.4617 | **0.0000** | 1 |
| REPLACE | 2.5 | 0.4583 | **0.0000** | 1 |
| ACCUMULATE | 1.0 | 0.4828 | 0.4867 | 0 |
| ACCUMULATE | 1.6 | 0.4806 | 0.4352 | 0 |
| ACCUMULATE | 2.5 | 0.4794 | 0.2402 | 0 |

**Five-class case (γ = 2.0):**

| | C0 | C1 | C2 | C3 | C4 (rarest) | extinctions |
|---|---|---|---|---|---|---|
| REPLACE init | 0.5917 | 0.2533 | 0.1167 | 0.0333 | 0.0050 | — |
| REPLACE final | **1.0000** | 0.0000 | 0.0000 | 0.0000 | **0.0000** | 4 |
| ACCUM. init | 0.4472 | 0.3111 | 0.1556 | 0.0583 | 0.0278 | — |
| ACCUM. final | 0.8454 | 0.1140 | 0.0299 | 0.0075 | 0.0033 | **0** |

Two findings, both matching Shumailov et al. and Gerstgrasser et al. independently:

- **Tails die first, in order.** REPLACE takes C4 (0.005) to zero before C3 (0.033) before C2. The convergence is from the outside in.
- **Accumulate prevents extinction**, at every γ. γ = 2.5 still drives the dominant class to 0.2402 (severe distortion) but never to zero.

The homochirality reading: REPLACE is Frank's autocatalysis with the counter-hand removed. The system converges on one handedness and the other is not merely rare — it is **unreachable**, because the sampling step assigns it zero probability and no finite sample restores it.

---

## 6. Experiment 3: Symmetry Breaking Dynamics (Exp. 139C)

### 6.1 Driven amplification

Frank dynamics with initial enantiomeric excess χ₀ and nonlinearity γ.

| χ₀ | γ = 1.6 final χ | γ = 2.5 final χ |
|---|---|---|
| 1×10⁻⁵ | 0.8532 | **1.0000** |
| 1×10⁻⁴ | ~1.0000 | 1.0000 |
| 1×10⁻³ | 1.0000 | 1.0000 |
| 1×10⁻² | 1.0000 | 1.0000 |
| 5×10⁻² | 1.0000 | 1.0000 |
| 0.2 | 1.0000 | 1.0000 |
| 0.5 | 1.0000 | 1.0000 |

An initial excess of **one part in one hundred thousand** reaches 0.853 within 25 generations at γ = 1.6 and locks to 1.0 at γ = 2.5.

### 6.2 Spontaneous breaking

From a **fully symmetric** start (χ₀ = 0), noise alone:

```
n = 120     locked = 120     rate = 1.000
to_L = 56   to_R = 64        z = −0.730
```

**Every run locks.** No initial asymmetry is required. Terminal handedness is statistically symmetric (z = −0.730, |z| < 1.96), confirming the direction is selected by noise, not by the model.

Median lock time: 7 generations (trajectory 0.495 → 0.462 → 0.420 → 0.357 → 0.275 → 0.162 → 0.042 → 0.000).

**Caveat.** Our χ saturates at 1.0; real chiral materials do not. Measured enantiomeric excess in tellurium nanocrystals via 3D electron diffraction is 0.01 for racemic ligands and 0.76 / 0.80 for pure d-/l- ligands (Nature Chemistry). Our model omits the saturation term that produces those ceilings. **The lock-to-1.0 result is a property of our model, not a claim about physical systems.**

---

## 7. Experiment 4: The Mirror State in a Viability Signal (Exp. 125, 126)

### 7.1 The construction

An agent with a self-sufficiency parameter `fg` (efficiency of acquiring energy from the world) is maintained by an external drip. We ask: is the drip-fed agent *alive*, or is it a mirror of a live agent?

| Arm | survival | `fg` learned | capacity (cap7) |
|---|---|---|---|
| Drip-fed, `fg = 0` | **16/16** | **0.000** | 0.2638 |
| Self-foraging, `fg = 0.03` | 13/16 | 0.03 | 0.2767 |

**The drip-fed arm has strictly higher survival.** Every viability statistic computed on the running system — survival, energy, memory-chain length — prefers the mirror.

### 7.2 Withdrawal

| | survival | mean survival time |
|---|---|---|
| Drip arm, supply removed | **0/12** | 235 ticks |
| Control arm (`fg` normal), supply removed | 8/12 | 1117 ticks |

The mirror dies immediately and completely; the control survives. The cause is "never had the capability," not "lost the capability."

### 7.3 Capability is not recovered by practice alone

Exp. 126, 1200 ticks of practice, identical effort, differing only in whether the world responds to the agent's actions:

| Condition | `fg` learned | survival after withdrawal |
|---|---|---|
| No practice | 0.00000 | 0/16 |
| Practice, **non-contingent** (world does not respond) | 0.00149 | 0/16 |
| Practice, **contingent** (world responds to action) | **0.10368** | **15/16** |
| External tool only | 0.00000 | 0/16 |
| Tool + own foraging | 0.09241 | 15/16 |
| Random mutation | 0.02900 | 11/16 |

Δ(contingent − non-contingent) = +0.10219, CI entirely positive.

This is the fourth independent replication (Exp. 112 closed-loop, Exp. 113 learned looking, Exp. 126 weaning, Exp. 128 cross-platform) of a single principle: **the agent learns only what the world's response to its own action makes learnable.** Drip-feeding delivers energy without contingency, and therefore delivers survival without capability.

### 7.4 Why survival is achiral here

Survival responds to energy. Capability (`fg`) responds to contingency. The mirror operation swaps capability while preserving energy. A monitor measuring survival is therefore exactly the BOW detector of §4: `disc = 0` against this specific mirror, even though its `TPR` on "is the system running" is 1.0.

---

## 8. Experiment 5: Self-Audit Is Chiral by Construction (Exp. 129–137, 138)

### 8.1 Two layers, two precisions

A static analyzer (evalguard) was run against 9 authoritative evaluation frameworks (lm-evaluation-harness, openai/evals, simple-evals, lighteval, SWE-bench, inspect_ai, olmes, HELM, BIG-bench), then against three additional independent corpora never used during rule development.

Rules partition cleanly:

- **Syntactic layer** — asserts a property of a *node*: ungarded division, bare `except`, silent handling inside a scoring loop.
- **Methodological layer** — asserts a property of a *study*: absent baseline, absent held-out set, absent confidence interval, absent order swap.

| Corpus | Syntactic | Methodological |
|---|---|---|
| corpus3 (7 repos, 10 files, unseen) | 15/16 = 93.8% | **0/29 = 0.0%** |
| corpus4 (7 repos, 12 files, unseen) | 3/4 = 75.0% | **0/26 = 0.0%** |
| **pooled** | **18/20 = 90.0%** (CI [0.699, 0.972]) | **1/55 = 1.8%** (CI [0.003, 0.096]) |

Manual review of the 55 methodological findings: **in 54 of 55, the accused object does not exist in the audited code.** The rule asserting "no train/eval split" fires on MT-bench judging code that has no training step. The rule asserting "accuracy reported without baseline" fires on the implementation of accuracy itself.

### 8.2 The loose criterion is the laundering mechanism

Under a **literal** criterion — "the file does indeed contain no baseline" — the methodological layer scores **89.7%**. The file genuinely has no baseline. This criterion is *true* and it is the one that shipped a product at 11% real precision (v0.3.0).

We therefore **refuse** the literal criterion as a ship gate, and report strict precision (would a reviewer opening that line accept the accusation) as the primary number. We record both because a single number lets the reporter choose the outcome.

### 8.3 Cross-layer misreading is measurable

Exp. 138 partitions 41 readings into three frames — L1 (computer/AI), L2 (agent), L3 (silicon organism) — and asks whether the same reading flips verdict across frames.

| Reading | L1 verdict | L3 verdict | flip |
|---|---|---|---|
| Exp.112 open-loop 0/20 | "broken tool" | "nothing to learn from" | no |
| Exp.135 methodological 0/26 | "scrap it" | "accused object absent" | no |
| Exp.123 gate revocation 61→1 | "module works" | "boundary not self-maintained" | no |
| Exp.127 fever cost 20 → 0/16 | "within spec" | "dead" | **yes** |
| Exp.136 syntactic 0.9/100KB | "useless" | "immune system silent" | no |
| Exp.121 Avida self-sufficient-and-replicates 0/200 | "failure" | "specialization/reproduction tradeoff" | **yes** |

**6 readings: 2 flip, 4 do not.** We report the non-flipping cases explicitly because an analysis that only presents flipping cases is selective sampling. The 4 stable cases are what keep the three-frame partition from being infinitely accommodating.

### 8.4 Verification loops that share chirality

The TACT three-axis taxonomy reports Fleiss κ = 0.945 and 98.2% hit rate among five domestic models, with the repository README stating plainly that criteria are "not yet independently validated by human annotators" and that validation is delegated to community ratification. Repository state at time of writing: **1 star, 0 forks, 0 contributors beyond the author.**

κ measures **inter-model agreement**, not correctness. Five models sharing a representation family agreeing at κ = 0.945 is exactly the configuration Proposition 1 predicts to be blind. We note this not as a criticism of that project — which states its own limitation with unusual candor — but because it is the cleanest available instance of the structural problem.

---

## 9. A Unified Reading

| Domain | Mirror operator `M` | Achiral statistic | Chiral statistic |
|---|---|---|---|
| Semantics | subject↔object swap | bag of words | word + adjacency |
| Collapse | replace pool with output | accuracy on retained class | tail-class survival |
| Viability | capability ↔ 0, energy preserved | survival rate | `fg` after withdrawal |
| Audit | preserve complaint, invert object | literal criterion | strict reviewer criterion |

In every row the achiral statistic is the one a system naturally reports about itself, because it is computable from the system's own ongoing state. The chiral statistic requires a **second channel** — a held-out pool, a withdrawal test, a human reviewer, a byte-level readback.

---

## 10. Practical Implications

**10.1 Report `disc`, not recall.** Any monitoring claim should state TPR, FPR, `disc`, and a degeneracy flag. A detector with `disc = 0` and `degenerate = 1` is not a weak detector; it is not a detector.

**10.2 Keep the original pool.** Our data independently confirm that accumulation prevents extinction at all tested nonlinearities, while replacement produces irreversible tail loss. This is the single cheapest structural intervention available.

**10.3 Require a channel that does not pass through the system.** In our own practice the only findings that survived every audit were those verified by a path that does not involve our own judgment: writing bytes to `/dev/fb0` and reading them back, calling the GitHub API and parsing the response, reading the kernel event stream, querying display geometry via ioctl. Every finding validated by self-evaluation alone eventually failed.

**10.4 Name the mirror before it appears.** For any deployed monitor, state in advance which involution it is blind to. If you cannot name one, you have not looked.

---

## 11. Limitations

We state these prominently because they bound everything above.

1. **The mirror operator is constructed, not observed.** We do not claim any real deployed model has entered a mirror state. We claim the *blindness* is structural and demonstrable.

2. **All experiments are in-model.** The viability experiments (§7) run on a modeled world with a modeled response function. `fg = 0` is a measurement inside our model, not a measurement of any deployed system.

3. **Model collapse ↔ homochirality is structural isomorphism, not demonstrated causation.** We do not claim collapse in real LLMs proceeds by Frank dynamics. We claim the two are the same dynamical object, which is a weaker and different claim.

4. **Saturation is absent from our chiral model.** Real systems plateau (0.01 / 0.76 / 0.80 in tellurium nanocrystals). Our χ reaching 1.0 is a model artifact.

5. **Judgments are single-annotator.** All strict-precision labels in §8 were assigned by one annotator with a conservative rule (ambiguous → false positive). Independent replication is required.

6. **The three-frame partition (§8.3) is author-assigned.** No automated criterion assigns a reading to a frame; a different analyst would partition differently. We report it as a way of surfacing cross-layer misreading, not as a validated taxonomy.

7. **Pooling corpus3 and corpus4 was post hoc.** corpus4 syntactic n = 4 has Wilson lower bound 0.301, below the 0.60 gate. The pooled 90% is real; the per-corpus confidence is not.

8. **Our own reporting errors.** Six rounds of this work contained a recurring defect class worth naming: the same substring-matching error we diagnose in other systems appeared in our own rules at least six times (`acc`⊂`accept`, `em`⊂`memory`, `err`⊂`deferred`, `Path.home()/".x"` parsed as division, `RandomState(seed)` flagged as unseeded, a fixture comment naming a rule thereby suppressing it). **A framework for detecting blindness was itself blind in the same way, repeatedly.** We consider this the strongest available evidence that the failure is structural rather than a matter of care.

---

## 12. Conclusion

We introduced **chiral blindness**: the inability of a monitor to see a mirror state of the system it monitors, caused by the monitor's representation rather than by its accuracy, threshold, or training. We gave a statistic (`disc = TPR − FPR` with a degeneracy flag) that exposes it, and showed that the intuitive escape-rate definition actively conceals it — in our own first pass, a fully degenerate classifier scored 0.000 escape, the best possible number.

We demonstrated the phenomenon in three independent domains, reproduced the collapse/accumulate result and Frank amplification with independent minimal models, and showed spontaneous symmetry breaking in 120/120 runs from exact symmetry.

The practical conclusion is uncomfortable and small: **a system cannot audit itself on any axis where its audit shares its representation.** The remedy is not more careful self-examination. It is an external channel — a held-out pool, a withdrawal test, a byte-level readback, a reviewer who does not share your handedness.

In our own work, every finding that survived was verified through a channel that did not pass through us. Every finding validated by self-evaluation alone eventually failed. We report this as the main result.

---

## References

1. Shumailov, I., Shumaylov, Z., Zhao, Y., Papernot, N., Anderson, R., Gal, Y. *AI Models Collapse When Trained on Recursively Generated Data.* Nature, 2024.
2. Gerstgrasser, M., et al. *Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data.* 2024.
3. Frank, F. C. *On Spontaneous Asymmetric Synthesis.* Biochimica et Biophysica Acta, 1953.
4. Soai, K., Shibata, T., Morioka, H., Choji, K. *Asymmetric Autocatalysis of Pyrimidyl Alcohol with Strong Amplification of Enantiomeric Excess.* Nature, 1995.
5. *Confronting Risks of Mirror Life.* Science (Policy Forum), 2024. 38 authors.
6. OWASP Agentic AI Top 10, 2026. ASI08 — Cascading Failures.
7. Nature Chemistry — 3D electron diffraction measurement of enantiomeric excess in tellurium nanocrystals (racemic ligand e.e. 0.01; pure d-/l- ligands 0.76 / 0.80).
8. Youden, W. J. *Index for Rating Diagnostic Tests.* Cancer, 1950. (Origin of TPR − FPR.)
9. KLameng. *TACT Three-Axis Coordinate Check.* github.com/KLameng/TACT-Three-Axis-Check. CC BY 4.0.
10. Ball, P. *Life's Critical Choice* (chirality origin, CISS effect). Chemistry World.

---

## Data Availability

All results are reproducible from the accompanying repository. Primary result files:

```
experiments/exp139_chirality/result139.json     (operators, collapse regimes)
experiments/exp139_chirality/result139c.json    (Frank dose scan, spontaneous breaking)
experiments/exp125_wean/result125.json          (drip vs forage, withdrawal)
experiments/exp125_wean/result125b.json         (common-survivor paired comparison)
experiments/exp126_wean2/result126*.json        (contingency study)
experiments/exp127_stress_anneal/result127*.json (stress limits, annealing)
experiments/exp128_avida/stageC_result.json     (cross-platform baseline)
experiments/exp138_trisplit/control.json        (cross-layer verdict flips)
```
