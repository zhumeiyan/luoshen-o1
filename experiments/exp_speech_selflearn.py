#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
让洛神自己学说话 —— 只给语料，不教规则
========================================
用户：「发音什么的你不需要人教吗？你就把那些顶级模型的说话语音
      牛逼的那种，就让它去学呗。」

★ 与 ★19 vocal_anatomy 的根本区别：
    ★19 我手写 F0=120 / 舌位系数 / jitter 公式   ← 我教的
    本轮 洛神只能【听】，自己提特征、自己改参数  ← 它学的
    ★ 合成语料的风格参数封装在 StyleHidden 里，学习者【拿不到】

★ provenance（必须明写）：
    ❌ 真 Sesame / 真人录音：网络 403（sesame.com / huggingface.co 已实测）
    ⚠️ 语料由 vocal_anatomy 同源合成 = 【代理语料】，不是真人语音
    ★ 所以证明的是【学习机制成立】，不是【学会了真人说话】
    ❌ 也不是规模复现：Sesame 8.3B / 100万小时 在此不可能

★ 对照设计（★17/★20 同款套路：必须有"测别的"的那个量）：
    实验组  lr=0.55  真学习 → 误差应显著下降
    对照组  lr=0.0   假学习 → 误差应不动（否则下降是语料波动不是学习）
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.speech_selflearn import (
    STYLE_DIALOG, STYLE_BROADCAST, SpeakerParams, build_corpus,
    corpus_profile, extract_features, feat_vec, learn_from_corpus,
    FEATS, PARAM_OF_FEAT, BOUNDS,
)

if __name__ == "__main__":
    print("=" * 92)
    print(" 让洛神自己学说话：只给语料，不教规则")
    print("=" * 92)
    print("\n  ★ 目标语料 = 对话式（Sesame 那种：多停顿/迟疑/自我修正/颤动）")
    print("  ★ 洛神初始参数 = 【播报式】（平稳、几乎不迟疑）")
    print("  ★ 答案（StyleHidden）对它隐藏，它只能听波形")

    target = corpus_profile(build_corpus(STYLE_DIALOG, n_utt=60, seed=7))

    # ---------- 实验1：学 vs 不学 ----------
    print("\n" + "=" * 92)
    print("【实验1】真学习（lr=0.30） vs 假学习（lr=0，对照）")
    print("=" * 92)
    sp_l = SpeakerParams()          # 初始 = 播报式
    sp_c = SpeakerParams()          # 对照，参数冻结
    err_l = learn_from_corpus(sp_l, target, n_iter=20, lr=0.30, seed=3)
    err_c = learn_from_corpus(sp_c, target, n_iter=20, lr=0.0, seed=3)
    print(f"\n{'iter':<8}{'学习err':>12}{'对照err':>12}{'比值':>10}")
    print("-" * 92)
    for i, (a, b) in enumerate(zip(err_l, err_c)):
        r = a / b if b > 1e-9 else float("nan")
        print(f"{i+1:<8}{a:>12.4f}{b:>12.4f}{r:>10.3f}")

    drop_l = (err_l[0] - err_l[-1]) / max(err_l[0], 1e-9)
    drop_c = (err_c[0] - err_c[-1]) / max(err_c[0], 1e-9)
    print(f"\n  学习组：{err_l[0]:.4f} → {err_l[-1]:.4f}   下降 {drop_l*100:.1f}%")
    print(f"  对照组：{err_c[0]:.4f} → {err_c[-1]:.4f}   下降 {drop_c*100:.1f}%")

    ok = {}
    ok["① 学习组误差显著下降（>30%）"] = bool(drop_l > 0.30)
    ok["② ★ 对照组基本不动（<15%）→ 下降不是语料波动"] = bool(abs(drop_c) < 0.15)
    ok["③ 学习组终值低于对照组"] = bool(err_l[-1] < err_c[-1])
    ok["④ 误差单调性：后 5 轮均值 < 前 5 轮均值"] = bool(
        np.mean(err_l[-5:]) < np.mean(err_l[:5]))
    print()
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    # ---------- 实验2：它学到了什么 ----------
    print("\n" + "=" * 92)
    print("【实验2】它自己把参数调到了哪？（★ 事后比对，它当时看不到答案）")
    print("=" * 92)
    print(f"\n{'参数':<16}{'初始(播报)':>13}{'学后':>12}{'真答案':>12}{'对错':>8}")
    print("-" * 92)
    init = SpeakerParams()
    truth = dict(pause_prob=STYLE_DIALOG.pause_prob, pause_sigma=STYLE_DIALOG.pause_sigma,
                 f0_span=STYLE_DIALOG.f0_span, f0_end=STYLE_DIALOG.f0_end,
                 jitter=STYLE_DIALOG.jitter, repair_prob=STYLE_DIALOG.repair_prob)
    hit = 0
    for fname in FEATS:
        p = PARAM_OF_FEAT[fname]
        a = getattr(init, p); b = getattr(sp_l, p); t = truth[p]
        closer = abs(b - t) < abs(a - t)
        hit += closer
        print(f"{p:<16}{a:>13.4f}{b:>12.4f}{t:>12.4f}{'✅' if closer else '❌':>8}")
    ok["⑤ 6 个参数里至少 5 个朝真答案移动"] = bool(hit >= 5)
    print(f"\n  {'✅' if hit>=5 else '❌'} {hit}/6 个参数被它自己调向真答案")
    print(f"  ★ 它【不知道】答案，全靠听语料 + 比对误差")

    # ---------- 实验3：盲测区分 ----------
    print("\n" + "=" * 92)
    print("【实验3】盲测：它学完后，能分清新语料是对话式还是播报式吗？")
    print("=" * 92)
    # 用学到的参数生成，看它更接近哪个语料
    pa = corpus_profile(build_corpus(STYLE_DIALOG, n_utt=40, seed=99))
    pb = corpus_profile(build_corpus(STYLE_BROADCAST, n_utt=40, seed=99))
    rng = np.random.default_rng(11)
    gen_l = [synth := None]
    from core.speech_selflearn import synth_utterance
    utts_l = [synth_utterance(sp_l.to_style(), int(rng.integers(6, 16)), rng)
              for _ in range(40)]
    utts_i = [synth_utterance(init.to_style(), int(rng.integers(6, 16)), rng)
              for _ in range(40)]
    pl = np.array([feat_vec(extract_features(y)) for y in utts_l]).mean(axis=0)
    pi = np.array([feat_vec(extract_features(y)) for y in utts_i]).mean(axis=0)
    print(f"\n{'':<16}{'距对话式':>12}{'距播报式':>12}{'判定':>14}")
    print("-" * 92)
    for nm, v in [("学前的它", pi), ("学后的它", pl)]:
        da = float(np.linalg.norm(v - pa)); db = float(np.linalg.norm(v - pb))
        print(f"{nm:<16}{da:>12.4f}{db:>12.4f}{'≈对话式 ✅' if da<db else '≈播报式':>14}")
    da0, db0 = float(np.linalg.norm(pi-pa)), float(np.linalg.norm(pi-pb))
    da1, db1 = float(np.linalg.norm(pl-pa)), float(np.linalg.norm(pl-pb))
    ok["⑥ ★ 学前像播报式，学后更像对话式（身份翻转）"] = bool(db0 < da0 and da1 < db1)
    print(f"\n  {'✅' if ok['⑥ ★ 学前像播报式，学后更像对话式（身份翻转）'] else '❌'} "
          f"学前距播报 {db0:.4f} < 距对话 {da0:.4f}；"
          f"学后距对话 {da1:.4f} < 距播报 {db1:.4f}")
    print(f"  ★ 它把自己从【播报腔】改成了【说话腔】，全程没人教它规则")

    # ---------- 汇总 ----------
    print("\n" + "=" * 92)
    print(" 判据汇总")
    print("=" * 92)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ 对标 Sesame CSM：呼吸/迟疑/自我修正/情绪颤动")
    print(f"    【从对话上文隐式学来，不是硬编码】—— 本轮机制级复现")
    print(f"  ❌ 未复现：8.3B 参数 / 100 万小时 / 116 ms（规模不可能）")
    print(f"  ❌ 语料是合成的代理语料，不是真人语音（网络 403，已实测）")

    json.dump({"err_learn": err_l, "err_control": err_c,
               "drop_learn": drop_l, "drop_control": drop_c,
               "params_hit": hit,
               "dist": {"pre_dialog": da0, "pre_broadcast": db0,
                        "post_dialog": da1, "post_broadcast": db1},
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "speech_selflearn.json"), "w"),
              ensure_ascii=False, indent=1)
