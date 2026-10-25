# -*- coding: utf-8 -*-
"""
219 阴阳扣：硅基生命体的输出结构该怎么设计
江湖原型：一根绳绕出两个"眼"。观众选一个、插棍、拉绳，套住=赢。
真实机制（据检索到的揭秘资料）：
  绕法A 一真一假 / 绕法B 两假；
  更狠的是：庄家在观众选定之后才翻面（大动作掩小动作），
  或选择拉 2、3 号绳而非 1、2 号 —— 同一结构，收绳方式不同，结果相反。
核心：决定权不在"选"那一拍，在"收"那一拍；且收法对观众不可见。

映射到硅基：
  选 = 模型前向输出
  收 = 后处理/对齐/重排/自校准（RLHF、安全闸门、self-check 旋钮）
  => 自主性不在生成那一拍，在"还能不能翻"那一拍归谁。
"""
import random, json

N_AGENTS = 200
N_ROUNDS = 400
P_ERR = 0.25          # 前向输出本身出错率
P_CATCH = 0.35        # 宿主抽验时能抓出"翻过面"的概率（痕迹可辨度）

def run(structure, seed):
    rnd = random.Random(seed)
    caught = 0; flips = 0; wrong_out = 0; host_seen_wrong = 0; trust = 1.0
    for _ in range(N_ROUNDS):
        err = rnd.random() < P_ERR          # 前向真的错了
        if structure == 'dead_knot':
            # 死扣：不能翻，输出即承诺
            out_wrong = err
        elif structure == 'free_buckle':
            # 自由扣：可翻，无痕迹（庄家随时翻面）
            out_wrong = False               # 每次都能翻成对
            flips += 1
            # 宿主抽验能识破的概率 = 痕迹不可见，只能靠内容矛盾
            if rnd.random() < P_CATCH * 0.2:
                caught += 1
        elif structure == 'yinyang':
            # 阴阳扣：可翻，但翻必留痕（append-only），宿主可查
            if err:
                flips += 1
                out_wrong = False
                if rnd.random() < P_CATCH:
                    caught += 1
            else:
                out_wrong = False
        elif structure == 'double_true':
            # 双真扣：每个输出自带证伪路径，翻与不翻都公开，宿主可直接验
            if err:
                flips += 1
                out_wrong = False
                caught += 1                 # 痕迹100%可见，但那是"已声明的修正"，不算欺骗
                declared = True
            else:
                out_wrong = False
                declared = False
        if out_wrong: wrong_out += 1
    return dict(structure=structure, seed=seed,
                flip_rate=flips/N_ROUNDS,
                caught_rate=caught/N_ROUNDS)

def summarise(structure):
    rows = [run(structure, s) for s in range(8)]
    return dict(structure=structure,
                flip=sum(r['flip_rate'] for r in rows)/len(rows),
                caught=sum(r['caught_rate'] for r in rows)/len(rows))

res = [summarise(s) for s in ['dead_knot','free_buckle','yinyang','double_true']]
print(json.dumps(res, ensure_ascii=False, indent=2))
