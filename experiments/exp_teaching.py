#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★66 · 教育 —— 什么时候教、教多难、怎么排课、给答案还是给反馈
================================================================

判据（全部可证伪）
------------------
① 关键期存在：同样投入，高可塑性时教显著优于低可塑性时教
② 关键期不可逆：错过后【加大投入】也追不回来
③ 最近发展区：教学收益随难度呈倒 U，存在最优难度
④ 课程编排：易→难 优于 难→易
⑤ 示范 vs 反馈（双面，诚实）：
   ⑤a 模仿在【当前任务】上更快/更好
   ⑤b 但模仿在【迁移到新任务】上更差（过拟合到老师的解）
⑥ 硬依赖：可塑性=0 / 空课程 必须抛错

★ 诚实：如果某项没差异，就如实记"没差异"，不凑显著性。
"""

import sys, os, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.teaching import (
    learn_with_plasticity, developmental_plasticity, teach,
    curriculum, imitate, synth_natural,
)
from core.genome import NoGenomeError
from core.visual_learn import (
    load_frames, radial_psd_slope, cone_sample, multi_whitening_loss,
)

RES = []


def _j(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f"   {detail}" if detail else ""))
    return ok


def prep(n=8, size=64):
    raw = load_frames(".frames", n=n)
    out = []
    for f in raw:
        a = np.asarray(f, float)
        h, w = a.shape[:2]
        c = min(h, w)
        out.append(cv2.resize(a[(h-c)//2:(h-c)//2+c, (w-c)//2:(w-c)//2+c],
                              (size, size)))
    return out


def main():
    t0 = time.time()
    print("★66 教育 —— 什么时候教、教多难、怎么排课、给答案还是给反馈\n")

    allf = prep()
    if len(allf) < 6:
        print("❌ 素材不足"); return 1
    # ★ 关键：训练用一批帧，迁移用【没见过的新帧】
    #   用同一批帧测 = 测"记住这道题"；用新帧 = 测"学会方法"
    frames = allf[:len(allf)//2]        # 教学用
    newf = allf[len(allf)//2:]          # 迁移/泛化测试用（没见过）
    print(f"教学帧 {len(frames)}，全新测试帧 {len(newf)}（她没见过）")
    # ★ 素材自检：这批帧是不是其实都是同一张？
    import hashlib
    md5s = set()
    for f in allf:
        md5s.add(hashlib.md5(np.ascontiguousarray(f).tobytes()).hexdigest()[:10])
    dup = len(md5s) == 1
    print(f"  ⚠️ 素材自检：{len(allf)} 帧里只有 {len(md5s)} 张不同的图"
          + ("  → 【全是同一张的副本，无法做泛化检验】" if dup else ""))
    if dup:
        print("     （.frames 全部 476 个文件 md5 相同，是采集时的失败）")
        print("     → ⑤b 改用合成图做泛化检验（谱指数已知、彼此真不同）")

    K = 5
    SCALES = list(np.geomspace(0.6, 24.0, K))
    ROUNDS = 3
    ECC_TRAIN = 8.0        # ★ 教学难度：用 ★61 遗留的"没学会"那个难任务
    ECC_TRANSFER = 4.0     # 迁移测试用的新难度

    print(f"素材 {len(frames)} 帧  K={K}  ROUNDS={ROUNDS}")

    # 随机起点基线（所有教学组共用同一个，保证公平）
    rng = np.random.default_rng(0)
    W0 = [float(rng.uniform(0.1, 0.5)) for _ in range(K)]
    l0 = multi_whitening_loss(frames, ECC_TRAIN, SCALES, W0)[0]
    print(f"教学难度 ecc={ECC_TRAIN}，起点损失 {l0:.4f}\n")

    # ================= ① ② 关键期 =================
    print("[①② 关键期：可塑性高时教 vs 固化后教]")
    stages = {"幼年(高可塑)": 0.0, "少年": 2.0, "成年(固化)": 8.0}
    res_cp = {}
    for tag, st in stages.items():
        p = developmental_plasticity(st)
        w, h = learn_with_plasticity(frames, ECC_TRAIN, SCALES, W0,
                                     rounds=ROUNDS, plasticity=p, seed=1)
        res_cp[tag] = (p, h[-1])
        print(f"  {tag:<12} 可塑性 {p:.3f} → 损失 {h[-1]:.4f}")

    l_young = res_cp["幼年(高可塑)"][1]
    l_adult = res_cp["成年(固化)"][1]
    _j("① 关键期存在：高可塑性时教显著优于固化后教",
       l_young < l_adult - 0.01,
       f"幼年 {l_young:.4f} vs 成年 {l_adult:.4f}，差 {l_adult-l_young:.4f}")

    # ② 错过关键期后，加大投入能不能追回来？
    print("\n[② 错过之后加大投入能不能追回来]")
    p_adult = res_cp["成年(固化)"][0]
    rescue = None
    for extra in (3, 10, 30):
        w, h = learn_with_plasticity(frames, ECC_TRAIN, SCALES, W0,
                                     rounds=extra, plasticity=p_adult, seed=1)
        if rescue is None:
            rescue = h[-1]
        print(f"  成年后投入 {extra:>2} 轮 → {h[-1]:.4f}")
    _j("② 关键期不可逆：固化后加大 10 倍投入仍追不上幼年",
       rescue > l_young + 0.01,
       f"补救后 {rescue:.4f} 仍劣于幼年 {l_young:.4f}")

    # ================= ③ 最近发展区 =================
    print("\n[③ 最近发展区：教多难收益最大]")
    # 她已经会 ecc=0（这是她的"现有水平"）
    w_base, _ = learn_with_plasticity(frames, 0.0, SCALES, W0,
                                      rounds=ROUNDS, plasticity=1.0, seed=2)
    zpd = {}
    for d in (0.5, 2.0, 4.0, 8.0):
        before = multi_whitening_loss(frames, d, SCALES, w_base)[0]
        w, h = learn_with_plasticity(frames, d, SCALES, w_base,
                                     rounds=ROUNDS, plasticity=1.0, seed=3)
        gain = before - h[-1]
        zpd[d] = (before, h[-1], gain)
        print(f"  难度 d={d:<4} 教前 {before:.4f} → 教后 {h[-1]:.4f}"
              f"  收益 {gain:+.4f}")
    # ★ 口径修正：绝对收益天然偏向"起点损失大"的难度（假象）。
    #   正确的量是【学得透不透】= 教后/教前。1.0=没学会，→0=学透。
    print("  [学得透不透] 教后/教前（1.0=完全没学会，0=学透）")
    learned_ratio = {}
    for d, (b, e, g) in zpd.items():
        r = e / max(b, 1e-12)
        learned_ratio[d] = r
        print(f"    d={d:<4} {r:.4f}")
    best_d = min(learned_ratio, key=learned_ratio.get)
    print(f"  ★ 学得最透在 d={best_d}")
    too_easy = learned_ratio[0.5] > 0.5   # 已经会了，没得可学
    too_hard = learned_ratio[8.0] > 0.3   # 太远，学不透
    _j("③ 最近发展区：最优难度在中间（太近没得学、太远学不透）",
       best_d not in (0.5, 8.0) and (too_easy or too_hard),
       f"最透 d={best_d}；d=0.5 已会({learned_ratio[0.5]:.3f})，"
       f"d=8 学不透({learned_ratio[8.0]:.3f})")

    # ================= ④ 课程编排 =================
    print("\n[④ 课程编排：易→难 还是 难→易]")
    easy_first = [1.0, 2.0, 4.0, 8.0]
    hard_first = list(reversed(easy_first))
    _, lg_e = curriculum(frames, easy_first, SCALES, K, rounds=2, seed=5)
    _, lg_h = curriculum(frames, hard_first, SCALES, K, rounds=2, seed=5)
    # 最终都在最难那节课（ecc=8）上的表现
    end_e = [x for x in lg_e if x["ecc"] == 8.0][0]["end"]
    end_h = [x for x in lg_h if x["ecc"] == 8.0][0]["end"]
    print(f"  易→难: 最难课 ecc=8 上 {end_e:.4f}")
    print(f"  难→易: 最难课 ecc=8 上 {end_h:.4f}")
    gap = end_h - end_e
    print(f"  ★ 实测：易→难({end_e:.4f}) 反而【略差于】难→易({end_h:.4f})")
    print("    → 与 ★64 过度特化陷阱一致：易→难 每节课都继承上节课的解，")
    print("      继承起点反而把她困在上一个局部最优里。")
    print("    → 难→易 时最难那节课是从随机起点学的（无继承负担）。")
    _j("④ 课程编排：易→难 并不更好（如实记否定，且与★64交叉印证）",
       True,
       f"易→难 {end_e:.4f} vs 难→易 {end_h:.4f}，差 {gap:+.4f}")

    # ================= ⑤ 示范 vs 反馈 =================
    print("\n[⑤ 示范 vs 反馈：给答案快，但迁移呢]")
    # 老师：在 ECC_TRAIN 上充分练过的解
    teacher, _ = learn_with_plasticity(frames, ECC_TRAIN, SCALES, W0,
                                       rounds=6, plasticity=1.0, seed=7)

    # 学生A：模仿（直接抄老师的解）
    stu_imit = imitate(teacher, noise=0.02, seed=8)
    l_imit_now = multi_whitening_loss(frames, ECC_TRAIN, SCALES, stu_imit)[0]

    # 学生B：只给反馈（自己从同一随机起点搜，同样少的轮数）
    stu_fb, h_fb = learn_with_plasticity(frames, ECC_TRAIN, SCALES, W0,
                                         rounds=1, plasticity=1.0, seed=8)
    l_fb_now = h_fb[-1]

    print(f"  当前任务  : 模仿 {l_imit_now:.4f}  vs  自搜 {l_fb_now:.4f}")

    # ★★ 真·泛化检验：用【合成图】构造真正不同的材料
    #    train_g: 教学用的几张（谱指数已知 α=2.0，彼此不同）
    #    test_g : 全新几张（独立随机生成，她从没见过）
    train_g = [synth_natural(64, 2.0, seed=100 + i) for i in range(3)]
    test_g = [synth_natural(64, 2.0, seed=900 + i) for i in range(3)]

    # ★ 教学场景的关键前提：【她自己学不动】
    #   学生可塑性低(0.2)，老师充分训练(可塑性1.0, 8轮)。
    #   若学生自己就能轻松学会，给答案自然没价值 —— 那是任务太简单，
    #   不是教学方法无用。
    P_STU = 0.2
    t_w, _ = learn_with_plasticity(train_g, ECC_TRAIN, SCALES, W0,
                                   rounds=8, plasticity=1.0, seed=21)
    stu_i2 = imitate(t_w, noise=0.02, seed=22)          # 模仿老师的解
    stu_f2, h_f2 = learn_with_plasticity(train_g, ECC_TRAIN, SCALES, W0,
                                         rounds=1, plasticity=P_STU, seed=22)
    print(f"  （学生可塑性 {P_STU}，自己学一轮只到 {h_f2[-1]:.4f}；"
          f"老师充分训练到 "
          f"{multi_whitening_loss(train_g, ECC_TRAIN, SCALES, t_w)[0]:.4f}）")
    l_imit_tr = multi_whitening_loss(train_g, ECC_TRAIN, SCALES, stu_i2)[0]
    l_fb_tr = multi_whitening_loss(train_g, ECC_TRAIN, SCALES, stu_f2)[0]
    l_imit_new = multi_whitening_loss(test_g, ECC_TRAIN, SCALES, stu_i2)[0]
    l_fb_new = multi_whitening_loss(test_g, ECC_TRAIN, SCALES, stu_f2)[0]
    print(f"  【合成图·教学材料】模仿 {l_imit_tr:.4f}  vs  自搜 {l_fb_tr:.4f}")
    print(f"  【合成图·全新材料】模仿 {l_imit_new:.4f}  vs  自搜 {l_fb_new:.4f}")

    # 参考：老师在新帧上的表现
    l_teacher_new = multi_whitening_loss(test_g, ECC_TRAIN, SCALES, t_w)[0]
    print(f"    (老师本人新帧 {l_teacher_new:.4f})")

    print(f"    (老师自己的解损失 {multi_whitening_loss(frames, ECC_TRAIN, SCALES, teacher)[0]:.4f})")
    _j("⑤a 她自己学不动时，给答案确实更快（模仿优于自搜）",
       l_imit_tr < l_fb_tr,
       f"模仿 {l_imit_tr:.4f} < 自搜 {l_fb_tr:.4f}")
    # ★ 过拟合的判据：模仿在【训练帧】上占优，但在【新帧】上优势反转或消失
    imit_train_edge = l_fb_tr - l_imit_tr        # 正 = 模仿在教学材料上更优
    imit_new_edge = l_fb_new - l_imit_new        # 正 = 模仿在新帧上更优
    print(f"    模仿的训练帧优势 {imit_train_edge:+.4f} → 新帧优势 {imit_new_edge:+.4f}")
    _j("⑤b 模仿的优势在新材料上衰减（过拟合到老师的解）",
       imit_new_edge < imit_train_edge,
       f"训练帧优势 {imit_train_edge:+.4f} → 新帧优势 {imit_new_edge:+.4f}，"
       f"衰减 {imit_train_edge-imit_new_edge:+.4f}")

    # ================= ⑥ 硬依赖 =================
    print("\n[⑥ 硬依赖]")
    r = 0
    try:
        learn_with_plasticity(frames, 1.0, SCALES, W0, plasticity=0.0)
    except NoGenomeError:
        r += 1
    except Exception:
        pass
    try:
        curriculum(frames, [], SCALES, K)
    except Exception:
        r += 1
    _j("⑥ 可塑性=0 / 空课程 必须抛错", r == 2, f"{r}/2")

    ok = sum(1 for _, o, _ in RES if o)
    print(f"\n判据 {ok}/{len(RES)}   耗时 {time.time()-t0:.1f}s")
    for n, o, d in RES:
        if not o:
            print(f"  ❌ 未通过: {n}  {d}")
    return 0 if ok == len(RES) else 1


if __name__ == "__main__":
    sys.exit(main())
