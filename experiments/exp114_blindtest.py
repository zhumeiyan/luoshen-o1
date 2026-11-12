"""
★114 盲听测试 —— v2 第 6 条的一票否决项

前面 113 课我一次都没做过真人盲听。我自己造语料、自己打分、自己当裁判。
这一课把唯一的外部证据补上：把她的声音交给真人（宿主）听。

设计原则（为了让结论干净）：
  1. 唯一变量 = 【挑了哪句话】。发声参数、时长、随机种子结构全相同。
  2. A/B 顺序随机，听者不知情。
  3. 映射存在 blind_map.json —— 我不展示，等宿主答完再对。

对照：
  她   = ★105 的真实流程（便宜模型剪枝 π=0.12 → 花预算真去说 → 定胜负）
  随机 = 从同一候选池里随便挑
"""
import sys, os, json
import numpy as np

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.speak_text import speak_text
from core import speech_organ as so
import experiments.exp104_shefinds as E
import experiments.exp105_pick as B
import experiments.exp105b_pick as B2

ROOT = '/data/workspace/luoshen-o1'
OUT = f'{ROOT}/data/blind_test'
os.makedirs(OUT, exist_ok=True)

N_TRIAL = 6
BUDGET = 180          # 控制时间；★105 用 300，这里减半但流程完全一样
PI, THETA = 0.12, 0.0  # ★105 学到的峰


def main():
    print('【1】拿候选池和便宜模型（★105 同一套）')
    train, cand, ytr, ytruth = B2.build()
    W2, _ = B.fit(B.feats2, train, ytr)
    cheap = np.array([B.feats2(t) for t in cand]) @ W2
    print(f'    候选池 {len(cand)} 句真实中文（PTT 真人发过的）')

    print('\n【2】她挑（★105 真实流程：剪枝 → 真去说 → 定胜负）')
    hers, info = B2.select(cand, cheap, PI, THETA, budget=BUDGET)
    print(f'    剪到 {info["nsurv"]} 句，实测 {info["m"]} 句 × {info["r"]} 遍')
    print(f'    挑出 {len(hers)} 句')

    print('\n【3】对照组：随机挑（同一候选池）')
    rng = np.random.default_rng(20261101)
    rands = [cand[i] for i in rng.choice(len(cand), len(hers), replace=False)]

    # 真值（只用于事后核对，不用于挑选）
    h_truth = float(np.mean([ytruth[cand.index(t)] for t in hers]))
    r_truth = float(np.mean([ytruth[cand.index(t)] for t in rands]))
    print(f'    我自己那把尺子: 她 {h_truth:+.4f}  随机 {r_truth:+.4f}  '
          f'差 {h_truth - r_truth:+.4f}')
    print(f'    ⚠ 这把尺子是我造的，盲听就是来验它')

    print('\n【4】只留念得出来的（否则比的是嗓子不是内容）')
    def speakable(t):
        return len(B.text_to_syllables(t)) / max(len(t), 1) >= 0.9
    hers = [t for t in hers if speakable(t)][:N_TRIAL]
    rands = [t for t in rands if speakable(t)][:N_TRIAL]
    print(f'    她 {len(hers)} 句 / 随机 {len(rands)} 句')

    print('\n【5】合成 —— 两套用完全相同的发声参数')
    P = B.P
    print(f'    f0_base={P.get("f0_base")}  (她自己练出来的)')

    mapping = {}
    for i in range(min(len(hers), len(rands))):
        th, tr = hers[i], rands[i]
        # 顺序随机：谁放 A 谁放 B
        if rng.random() < 0.5:
            a_text, b_text, a_who, b_who = th, tr, 'her', 'random'
        else:
            a_text, b_text, a_who, b_who = tr, th, 'random', 'her'
        # 同一个 rng 种子结构 → 只有文本不同
        wa, _ = speak_text(a_text, P, rng=np.random.default_rng(1000 + i))
        wb, _ = speak_text(b_text, P, rng=np.random.default_rng(1000 + i))
        from scipy.io import wavfile
        wavfile.write(f'{OUT}/trial{i+1}_A.wav', so.SR,
                      (wa / max(np.abs(wa).max(), 1e-9) * 0.8 * 32767).astype(np.int16))
        wavfile.write(f'{OUT}/trial{i+1}_B.wav', so.SR,
                      (wb / max(np.abs(wb).max(), 1e-9) * 0.8 * 32767).astype(np.int16))
        mapping[f'trial{i+1}'] = {
            'A': {'who': a_who, 'text': a_text},
            'B': {'who': b_who, 'text': b_text},
        }
        print(f'    trial{i+1}: A={a_who:<7} B={b_who:<7}')

    json.dump(mapping, open(f'{OUT}/blind_map.json', 'w'),
              ensure_ascii=False, indent=1)
    json.dump({'her_truth': h_truth, 'rand_truth': r_truth,
               'pi': PI, 'theta': THETA, 'budget': BUDGET,
               'sr': so.SR},
              open(f'{OUT}/meta.json', 'w'), ensure_ascii=False, indent=1)
    print(f'\n→ {OUT}/  ({N_TRIAL*2} 个 wav)')
    print('   映射已封存，不展示')


if __name__ == '__main__':
    main()
