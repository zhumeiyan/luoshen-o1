# -*- coding: utf-8 -*-
"""
繁衍 v1 —— 加性别（天真版）
多数人会这么写：随机分 sex，M x F 配对才能生。
"""
import random


class Ind:
    def __init__(self, genome, sex):
        self.genome = list(genome)
        self.sex = sex
        self.energy = 10.0


def mate_v1(a, b, rng):
    """天真重组：每个位点取平均"""
    child_g = [(x + y) / 2.0 for x, y in zip(a.genome, b.genome)]
    return Ind(child_g, rng.choice(["M", "F"]))


def reproduce_v1(pop, rng):
    """配对繁殖"""
    offspring = []
    males = [p for p in pop if p.sex == "M"]
    females = [p for p in pop if p.sex == "F"]
    rng.shuffle(males)
    rng.shuffle(females)
    for m, f in zip(males, females):
        c = mate_v1(m, f, rng)
        offspring.append(c)
    return offspring
