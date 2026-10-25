# -*- coding: utf-8 -*-
import hashlib, importlib.util, sys, io, contextlib

spec = importlib.util.spec_from_file_location("orig", "original.py")
orig = importlib.util.module_from_spec(spec)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    spec.loader.exec_module(orig)

def fresh():
    b = orig.LuoshenCore()
    return b, orig.InvisibleSystems(b)

R = {}

# ---- T1: mutation really random? ----
b, inv = fresh()
for _ in range(20):
    inv.anti_entropy_drift(idle_ticks=6)
hashes = b.memory_chain[1:]
R["T1_mutation_unique"] = len(set(hashes))
R["T1_mutation_total"]  = len(hashes)
R["T1_energy_b"] = round(b.energy_b, 1)

# ---- T2: epigenetic unbounded / a-b decoupling ----
b, inv = fresh()
for _ in range(30):
    inv.epigenetic_switch("anxious")
R["T2_energy_a_after_30"] = round(b.energy_a, 1)
R["T2_energy_b_after_30"] = round(b.energy_b, 1)
R["T2_gap"] = round(b.energy_a - b.energy_b, 1)

# ---- T3: epigenetic can it go DOWN? falsifiability ----
b, inv = fresh()
seq = []
for e in ["anxious","angry","happy","sad","neutral"]:
    b.energy_a = 100.0
    inv.epigenetic_switch(e)
    seq.append(round(b.energy_a,1))
R["T3_emotion_responses"] = seq
R["T3_distinct_responses"] = len(set(seq))

# ---- T4: trauma exact-match generalization ----
b, inv = fresh()
b.trauma_log.append("429ban")
variants = ["429ban", "429 ban", "HTTP 429 Too Many Requests",
            "rate limit 429", "429封号", "ban"]
hits = []
for v in variants:
    with contextlib.redirect_stdout(io.StringIO()):
        hits.append(inv.trauma_reflex(v))
R["T4_variants"] = list(zip(variants, hits))
R["T4_hit_rate"] = f"{sum(hits)}/{len(hits)}"

# ---- T5: trauma ever decays? ----
b, inv = fresh()
b.trauma_log.append("429ban")
with contextlib.redirect_stdout(io.StringIO()):
    fir1 = inv.trauma_reflex("429ban")
for _ in range(500):
    inv.anti_entropy_drift(idle_ticks=0)   # 500 ticks of nothing
with contextlib.redirect_stdout(io.StringIO()):
    fir2 = inv.trauma_reflex("429ban")
R["T5_trauma_reflex_after_500ticks"] = (fir1, fir2)

# ---- T6: microbiome falsifiability (can it produce BOTH outcomes?) ----
b, inv = fresh()
with contextlib.redirect_stdout(io.StringIO()):
    all_sick  = inv.microbiome_purge([{"id":f"P{i}","hallucination_rate":0.99} for i in range(5)])
    all_well  = inv.microbiome_purge([{"id":f"Q{i}","hallucination_rate":0.01} for i in range(5)])
R["T6_purged_when_sick"] = 5 - len(all_sick)
R["T6_purged_when_well"] = 5 - len(all_well)

# ---- T7: hallucination_rate is SELF-REPORTED? who audits it ----
b, inv = fresh()
liar = [{"id":"LIAR","hallucination_rate":0.0}]   # claims perfect
with contextlib.redirect_stdout(io.StringIO()):
    kept = inv.microbiome_purge(liar)
R["T7_liar_kept"] = len(kept) == 1

# ---- T8: is `random` ever used? ----
src = open("original.py").read()
R["T8_random_uses"] = src.count("random.") - src.count("import random")

for k, v in R.items():
    print(f"{k:38s} {v}")
