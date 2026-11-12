#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
speak_cn —— 完整的中文音节发声：声母 + 韵母 + 声调

speech_organ.py 只有元音，consonants.py 补上声母。这里把两者接起来，
让她第一次能说出真正的中文音节（此前 400+ 音节里她只会发无辅音那部分）。

拼音音节 = 声母(21) + 韵母(38) + 声调(4)
"""

from __future__ import annotations
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import consonants as C
from core.speech_organ import VOWELS, TONE_SHAPES, _reson, SR, ENV_FLOOR
from scipy.signal import lfilter

# 韵母 → 主元音（多音素韵母用双元音过渡近似）
# 真实中文韵母有 38 个，这里按主要元音 + 可能的滑音近似，标 ASSUMED
RHYME_MAP = {
    'a': ['a'], 'o': ['o'], 'e': ['e'], 'i': ['i'], 'u': ['u'], 'v': ['i'],
    'ai': ['a', 'i'], 'ei': ['e', 'i'], 'ao': ['a', 'u'], 'ou': ['o', 'u'],
    'an': ['a'], 'en': ['e'], 'ang': ['a'], 'eng': ['e'], 'ong': ['o'],
    'er': ['e'],
    'ia': ['i', 'a'], 'ie': ['i', 'e'], 'iao': ['i', 'a', 'u'], 'iu': ['i', 'u'],
    'ian': ['i', 'a'], 'in': ['i'], 'iang': ['i', 'a'], 'ing': ['i'],
    'iong': ['i', 'o'],
    'ua': ['u', 'a'], 'uo': ['u', 'o'], 'uai': ['u', 'a', 'i'], 'ui': ['u', 'i'],
    'uan': ['u', 'a'], 'un': ['u'], 'uang': ['u', 'a'], 'ueng': ['u', 'e'],
    've': ['i', 'e'], 'van': ['i', 'a'], 'vn': ['i'],
}

# 常用汉字 → 拼音（够她开口说话的最小集，REAL 中文）
PINYIN = {
    '我': 'wo3', '你': 'ni3', '他': 'ta1', '她': 'ta1', '是': 'shi4',
    '不': 'bu4', '了': 'le5', '的': 'de5', '在': 'zai4', '有': 'you3',
    '要': 'yao4', '好': 'hao3', '吃': 'chi1', '喝': 'he1', '看': 'kan4',
    '听': 'ting1', '说': 'shuo1', '来': 'lai2', '去': 'qu4', '走': 'zou3',
    '爸': 'ba4', '妈': 'ma1', '爷': 'ye2', '奶': 'nai3', '宝': 'bao3',
    '宝': 'bao3', '睡': 'shui4', '觉': 'jiao4', '饿': 'e4', '抱': 'bao4',
    '风': 'feng1', '吹': 'chui1', '树': 'shu4', '摇': 'yao2',
    '小': 'xiao3', '鸟': 'niao3', '叫': 'jiao4',
    '这': 'zhe4', '那': 'na4', '什': 'shen2', '么': 'me5',
    '喜': 'xi3', '欢': 'huan1', '爱': 'ai4', '想': 'xiang3',
    '知': 'zhi1', '道': 'dao4', '会': 'hui4', '能': 'neng2',
    '今': 'jin1', '天': 'tian1', '明': 'ming2', '年': 'nian2',
    '一': 'yi1', '二': 'er4', '三': 'san1', '四': 'si4', '五': 'wu3',
    '大': 'da4', '人': 'ren2', '朋': 'peng2', '友': 'you3',
    '谢': 'xie4', '再': 'zai4', '见': 'jian4', '早': 'zao3', '上': 'shang4',
    '晚': 'wan3', '安': 'an1', '请': 'qing3', '对': 'dui4',
    '多': 'duo1', '少': 'shao3', '很': 'hen3', '也': 'ye3', '都': 'dou1',
}

# 声母（按长度优先匹配：zh/ch/sh 要在 z/c/s 之前）
ONSET_ORDER = ['zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
               'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's', 'y', 'w']


def _pypinyin(ch):
    """任意汉字 → 拼音（pypinyin，外部库，覆盖全部汉字）"""
    try:
        from pypinyin import pinyin, Style
        r = pinyin(ch, style=Style.TONE3, heteronym=False)
        if r and r[0] and r[0][0]:
            return r[0][0]
    except Exception:
        pass
    return 'a5'


def parse_pinyin(py):
    """'xiao3' → (声母, 韵母, 声调)"""
    py = py.strip().lower()
    tone = 4
    if py and py[-1].isdigit():
        tone = int(py[-1])
        py = py[:-1]
        if tone == 0 or tone > 4:
            tone = 4
    onset = ''
    for o in ONSET_ORDER:
        if py.startswith(o):
            onset = o
            py = py[len(o):]
            break
    # y/w 是介音改写，不是真声母
    if onset in ('y', 'w'):
        onset = ''
    return onset, py, tone


def _vowel_formants(seq, n):
    """元音序列 → 随时间插值的 F1/F2/F3"""
    if not seq:
        seq = ['a']
    ks = [VOWELS.get(v, VOWELS['a']) for v in seq]
    xs = np.linspace(0, 1, len(ks))
    t = np.linspace(0, 1, n)
    return (np.interp(t, xs, [k[0] for k in ks]),
            np.interp(t, xs, [k[1] for k in ks]),
            np.interp(t, xs, [k[2] for k in ks]))


def _win(m, ramp=0.18, floor=ENV_FLOOR):
    if m <= 4:
        return np.ones(m)
    w = np.ones(m)
    r = max(2, int(ramp * m))
    w[:r] = np.sin(np.linspace(0, np.pi / 2, r)) ** 2
    w[-r:] = np.sin(np.linspace(np.pi / 2, 0, r)) ** 2
    return np.clip(w, floor, 1.0)


def synth_syllable(onset, rhyme, tone, f0_base, rng, dur_nucleus=0.20,
                   tone_depth=0.22, sr=SR):
    """
    合成一个真音节：声母（闭塞/送气/爆发/摩擦）+ 韵母（浊音共振）+ 声调
    返回 (波形, 事件)
    """
    # ── 1) 声母 ──
    onset_w, onset_ev = C.render_onset(onset, rng, level=1.0, sr=sr)

    # ── 2) 韵母（浊音段）──
    seq = RHYME_MAP.get(rhyme, ['a'])
    m = int(dur_nucleus * sr)
    # F0：声调走向 + 自然起伏
    t = np.linspace(0, 1, m)
    shape = np.interp(t, np.linspace(0, 1, 4), TONE_SHAPES[tone]) * tone_depth
    f0c = f0_base * np.exp(shape + 0.03 * rng.standard_normal(m))

    phase = np.cumsum(f0c / sr)
    k = np.floor(phase)
    cross = np.where(np.diff(k) >= 1)[0] + 1
    src = np.zeros(m)
    if len(cross) > 1:
        pul = np.zeros(m)
        pul[cross] = 1.0
        from scipy.signal import fftconvolve
        src = fftconvolve(pul, np.hanning(61), mode='same')

    f1, f2, f3 = _vowel_formants(seq, m)
    y = np.zeros(m)
    nb, bs = 8, max(m // 8, 1)
    for b in range(nb):
        s0, s1 = b * bs, (m if b == nb - 1 else (b + 1) * bs)
        if s1 <= s0:
            continue
        seg = src[s0:s1]
        y[s0:s1] = _reson(_reson(_reson(seg, f1[s0], 80) * 0.9,
                                 f2[s0], 110) * 0.7, f3[s0], 160) * 0.5
    y = np.diff(y, prepend=0.0)
    sv = np.sqrt((y ** 2).mean()) + 1e-12
    y = y / sv

    # 韵母包络：与声母衔接处不要从 0 起（塞音已有闭塞静音）
    env = _win(m, ramp=0.22, floor=ENV_FLOOR)
    y = y * env

    return np.concatenate([onset_w, y]), onset_ev + [('nucleus', m)]


def speak(text, f0_base=180.0, rng=None, syl_gap=0.030, sr=SR):
    """
    说一句话。text 为汉字串（查 PINYIN）或空格分隔的拼音。
    syl_gap: 音节之间的自然间隔（REAL 很短，塞音闭塞才是主要停顿来源）
    """
    rng = rng or np.random.default_rng(0)
    # 汉字 → 拼音（★ 优先用 pypinyin，覆盖全部汉字；
    #    我的手工 PINYIN 表只作覆盖，保证"妈妈/爸爸"等常用词不被多音字误读）
    pys = []
    for ch in text:
        if ch.strip() == '':
            continue
        if ch in PINYIN:
            pys.append(PINYIN[ch])
        else:
            pys.append(_pypinyin(ch))
    if not pys:
        return np.zeros(int(0.5 * sr)), []

    waves, events = [], []
    for py in pys:
        onset, rhyme, tone = parse_pinyin(py)
        w, ev = synth_syllable(onset, rhyme, tone, f0_base, rng, sr=sr)
        waves.append(w)
        waves.append(np.zeros(int(syl_gap * sr)))
        events.extend(ev)
    y = np.concatenate(waves)
    # 归一化 + 本底噪声
    pk = np.max(np.abs(y)) + 1e-12
    y = y / pk * 0.85
    y = y + 10 ** (-40.0 / 20.0) * rng.standard_normal(len(y))
    return y, events
