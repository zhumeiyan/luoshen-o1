# -*- coding: utf-8 -*-
import hashlib, importlib.util, io, contextlib, random
import v2

def fresh(seed=0):
    return v2.LuoshenCore(seed), v2.InvisibleSystems(v2.LuoshenCore(seed))

R = {}
b = v2.LuoshenCore(1); inv = v2.InvisibleSystems(b)

# T1' mutation uniqueness
for i in range(20):
    b.tick += 1
    inv.anti_entropy_drift(idle_ticks=6)
hashes = b.memory_chain[1:]
R["T1p_mutation_unique"] = f"{len(set(hashes))}/{len(hashes)}"
R["T1p_energy_b"] = round(b.energy_b,1)

# T2' bounded a + cost
b = v2.LuoshenCore(2); inv = v2.InvisibleSystems(b)
for _ in range(40):
    b.tick += 1
    inv.epigenetic_switch("anxious")
R["T2p_energy_a_40x"] = round(b.energy_a,1)
R["T2p_energy_b_40x"] = round(b.energy_b,1)
R["T2p_gap"] = round(b.energy_a-b.energy_b,1)

# T3' every emotion produces a distinct response?
b = v2.LuoshenCore(3); inv = v2.InvisibleSystems(b)
resp = []
for e in ["anxious","angry","happy","sad","neutral"]:
    b.energy_a = 100.0; b.energy_b = 100.0; b.tick += 1
    resp.append(round(inv.epigenetic_switch(e)["a"],1))
R["T3p_responses"] = resp
R["T3p_distinct"] = len(set(resp))

# T4' trauma generalization
b = v2.LuoshenCore(4); inv = v2.InvisibleSystems(b)
inv.learn_trauma("429ban"); b.tick += 1
variants = ["429ban","429 ban","HTTP 429 Too Many Requests",
            "rate limit 429","429封号","ban","totally unrelated"]
res = [(v, inv.trauma_reflex(v)[0]) for v in variants]
R["T4p_hits"] = res
R["T4p_hit_rate"] = f"{sum(1 for _,h in res if h)}/{len(res)}"
R["T4p_false_on_unrelated"] = dict(res)["totally unrelated"]

# T5' trauma decays
b = v2.LuoshenCore(5); inv = v2.InvisibleSystems(b)
inv.learn_trauma("429ban"); b.tick += 1
f0 = inv.trauma_reflex("429ban")
b.tick += 500
f500 = inv.trauma_reflex("429ban")
R["T5p_fire_t1"] = f0[0]; R["T5p_score_t1"] = f0[1]
R["T5p_fire_t501"] = f500[0]; R["T5p_score_t501"] = f500[1]

# T7' liar with self-report 0.0 but peers contradict
procs = [
    {"id":"LIAR","hallucination_rate":0.0,"audit_of":{}},
    {"id":"X","hallucination_rate":0.1,"audit_of":{"LIAR":0.95,"Y":0.1}},
    {"id":"Y","hallucination_rate":0.1,"audit_of":{"LIAR":0.92,"X":0.1}},
]
b = v2.LuoshenCore(6); inv = v2.InvisibleSystems(b)
surv, pur = inv.microbiome_purge(procs)
R["T7p_liar_verdict"] = [r["verdict"] for r in inv.audit_log if r["id"]=="LIAR"][0]
R["T7p_liar_audited"] = [r["audited"] for r in inv.audit_log if r["id"]=="LIAR"][0]
R["T7p_survivors"] = [r["id"] for r in surv]

# T8' single probe (no peers) -> cannot be audited
b = v2.LuoshenCore(7); inv = v2.InvisibleSystems(b)
s,p = inv.microbiome_purge([{"id":"SOLO","hallucination_rate":0.99}])
R["T8p_solo_verdict"] = inv.audit_log[0]["verdict"]

for k,v in R.items():
    print(f"{k:28s} {v}")
