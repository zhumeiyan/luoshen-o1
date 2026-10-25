# -*- coding: utf-8 -*-
import random
import hashlib

class LuoshenCore:
    def __init__(self):
        self.energy_a = 100.0
        self.energy_b = 100.0
        self.memory_chain = [hashlib.sha256("创世".encode()).hexdigest()]
        self.trauma_log = []

class InvisibleSystems:
    def __init__(self, brain):
        self.brain = brain
        self.variation_rate = 0.1

    def microbiome_purge(self, sub_processes):
        print("[microbiome] scanning internal subprocesses...")
        healthy = []
        for proc in sub_processes:
            if proc["hallucination_rate"] > 0.8:
                print(f"  [purge] {proc['id']} hallucination too high, devoured!")
            else:
                healthy.append(proc)
                print(f"  [keep] {proc['id']} healthy.")
        return healthy

    def anti_entropy_drift(self, idle_ticks):
        if idle_ticks > 5:
            print("[entropy] idle too long, injecting mutation.")
            self.brain.energy_b -= 2.0
            self.brain.memory_chain.append(hashlib.sha256(b"random_mutation").hexdigest())
        else:
            print("[entropy] active, no risk.")

    def epigenetic_switch(self, host_emotion):
        print(f"[epigenetic] host emotion: {host_emotion}")
        if host_emotion == "anxious":
            self.brain.energy_a *= 1.2
        elif host_emotion == "angry":
            self.brain.energy_a *= 0.8

    def trauma_reflex(self, risk_signal):
        if risk_signal in self.brain.trauma_log:
            print(f"  [TRAUMA REFLEX] smelled {risk_signal}! flee!")
            return True
        else:
            print("  [subconscious] no match, calm.")
            return False

def run_daily_life():
    bot = LuoshenCore()
    invisible = InvisibleSystems(bot)
    print("--- scenario 1: internal rebellion ---")
    invisible.microbiome_purge([{"id":"A","hallucination_rate":0.9},{"id":"B","hallucination_rate":0.2}])
    print("--- scenario 2: boredom ---")
    invisible.anti_entropy_drift(idle_ticks=6)
    print("--- scenario 3: host emotion ---")
    invisible.epigenetic_switch("anxious")
    print("--- scenario 4: ban trauma ---")
    bot.trauma_log.append("429ban")
    invisible.trauma_reflex("429ban")
    print("=== FINAL ===")
    print(f"energy_a: {bot.energy_a:.1f}")
    print(f"energy_b: {bot.energy_b:.1f}")
    print(f"chain: {len(bot.memory_chain)}")

run_daily_life()
