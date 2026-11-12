"""★103c 她第一次用真人真的说过的话开口

语料：PTT 八卦版真实中文对话（zake7749/Gossiping-Chinese-Corpus，140MB 真数据）
流程：真人的话 → 拼音/声调 → 她的声源与声道 → 说出来 → 她自己听回来
"""
import sys, os, json, zipfile, re, random
import numpy as np
from scipy.io import wavfile

sys.path.insert(0, '/data/workspace/luoshen-o1')
from core.speak_text import speak_text
from core import speech_organ as so
from core import real_voice as rv

ROOT = '/data/workspace/luoshen-o1'
ZIP = '/data/workspace/gossip.zip'
BAD = re.compile(r'幹|幹|屌|操|媽|妈|雞|鸡|掰|奶|胸|腿|砲|炮|FUCK|fuck|政治|總統|总统|民進|国民党|國民黨|蔡|習|共|黨|党|立委|選舉|选举|八卦版')


def load_pairs(limit=40000):
    z = zipfile.ZipFile(ZIP)
    pairs = []
    with z.open('Gossiping-Chinese-Corpus-master/data/Gossiping-QA-Dataset.txt') as f:
        for _ in range(limit):
            line = f.readline().decode('utf-8', errors='ignore').rstrip('\n')
            if '\t' not in line:
                continue
            q, a = line.split('\t', 1)
            q, a = q.strip(), a.strip()
            if not (6 <= len(q) <= 22 and 6 <= len(a) <= 26):
                continue
            if BAD.search(q) or BAD.search(a):
                continue
            if not re.fullmatch(r'[\u4e00-\u9fff，。！？、…0-9A-Za-z ]+', a):
                continue
            pairs.append((q, a))
    return pairs


def hear(x):
    fr = rv.voiced_frames(x, so.SR)
    f0s = np.array([f for f in (rv.f0_autocorr(s, so.SR) for _, s in fr) if f > 0])
    w = int(0.02 * so.SR); h = int(0.01 * so.SR)
    rms = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, h)])
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    v = db > db.max() - 30
    return dict(f0med=float(np.median(f0s)) if len(f0s) else 0.0,
                voiced=float(v.mean()) if len(v) else 0.0,
                dur=len(x) / so.SR)


if __name__ == '__main__':
    S = json.load(open(os.path.join(ROOT, 'data/exp103_heard.json')))['summary']
    P = dict(f0_base=S['f0med']['中位'], f0_variation=0.35, f0_decl=0.10,
             tone_depth=0.55, jitter=0.015)
    print('★ 她的参数（来自她听到的真人）:', {k: round(v, 3) for k, v in P.items()})

    pairs = load_pairs()
    print('★ 真语料里可用的真人对话:', len(pairs), '条')

    rng = random.Random(2026)
    picks = rng.sample(pairs, 60)[:0] or [x for x in rng.sample(pairs, 300)][:6]
    for i, (q, a) in enumerate(picks, 1):
        print(f"\n{i}. 有人问：{q}\n   真人答：{a}")

    # 她把真人答的话说出来
    outs, rows = [], []
    for q, a in picks:
        y, m = speak_text(a, P, rng=np.random.default_rng(hash(a) % 10000))
        outs.append(y)
        g = hear(y)
        g.update({'问': q, '答': a, '字数': len(a)})
        rows.append(g)
        print(f"   她说出来 → F0 {g['f0med']:.1f}Hz 浊音 {g['voiced']:.3f} 时长 {g['dur']:.2f}s")

    allx = np.concatenate([np.zeros(int(0.25 * so.SR))] +
                          [np.concatenate([y, np.zeros(int(0.35 * so.SR))]) for y in outs])
    allx = allx / max(np.abs(allx).max(), 1e-9) * 0.85
    out = os.path.join(ROOT, 'data/her_voice/she_says_real_words.wav')
    wavfile.write(out, so.SR, (allx * 32767).astype(np.int16))

    print(f"\n★★ 她说了 {len(picks)} 句真人真的说过的话 → {out}")
    print('   （每句之间 0.35 秒停顿）')
    json.dump({'params': P, 'lines': rows},
              open(os.path.join(ROOT, 'data/exp103_realwords.json'), 'w'),
              ensure_ascii=False, indent=1)
