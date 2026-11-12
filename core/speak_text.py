import sys, os
"""★103c 让真人的话，从她的嘴里说出来

synthesize() 生成的是随机音节 —— 她有嘴，但没有一句是自己想说的。
这个模块把【真人真的说过的话】（汉字）转成拼音 → 元音/声调 → 她的声源与声道。

不新增物理，只复用 speech_organ 的共振器、声调形状与唇辐射。
"""
import re
import numpy as np
from scipy.signal import lfilter

from .speech_organ import SR, TONE_SHAPES, VOWELS, _reson, _win, \
    BREATH_DB, GLOTTAL_DB, NOISE_FLOOR_DB

# 拼音 → 元音（取韵腹）
_V = re.compile(r'(?:ai|ao|ei|ou|an|en|ang|eng|ong|in|ing|ia|ie|iu|iao|ian|iang|iong|ua|uo|uai|ui|uan|un|uang|ueng|ue|uan|ün|van|[aoeiuüv])')


def _vowel_of(py: str) -> str:
    """从拼音里取韵腹元音"""
    m = _V.search(py)
    if not m:
        return 'e'
    s = m.group(0)
    # 复合韵母取主要元音
    table = {
        'ai': 'a', 'ao': 'a', 'ei': 'e', 'ou': 'o', 'an': 'a', 'en': 'e',
        'ang': 'a', 'eng': 'e', 'ong': 'o', 'in': 'i', 'ing': 'i',
        'ia': 'a', 'ie': 'e', 'iu': 'o', 'iao': 'a', 'ian': 'a', 'iang': 'a',
        'iong': 'o', 'ua': 'a', 'uo': 'o', 'uai': 'a', 'ui': 'e', 'uan': 'a',
        'un': 'e', 'uang': 'a', 'ueng': 'e', 'ue': 'e', 'ün': 'i', 'van': 'a',
    }
    v = table.get(s, s)
    return v if v in VOWELS else 'e'


def text_to_syllables(text):
    """汉字 → [(元音, 声调), ...]，非汉字按标点变成停顿"""
    _PYLIB = '/data/workspace/luoshen-o1/.pylibs'
    if _PYLIB not in sys.path:
        sys.path.insert(0, _PYLIB)
    try:
        from pypinyin import lazy_pinyin, Style
    except ImportError:
        os.system('pip install -q --target=' + _PYLIB + ' pypinyin')
        if _PYLIB not in sys.path:
            sys.path.insert(0, _PYLIB)
        from pypinyin import lazy_pinyin, Style
    out = []
    for ch in text:
        if ch in '，。！？、；：,.!?;:…— 　':
            out.append(None)          # 停顿
            continue
        if not re.match(r'[\u4e00-\u9fff]', ch):
            continue
        py = lazy_pinyin(ch, style=Style.TONE3)[0]
        if not py:
            continue
        tone = int(py[-1]) if py[-1].isdigit() and py[-1] != '0' else 1
        body = py[:-1] if py[-1].isdigit() else py
        out.append((_vowel_of(body), max(1, min(4, tone))))
    return out


def speak_text(text, params, rng=None, syl_dur=0.18, pause_dur=0.12):
    """真人说过的一句话 → 她的波形"""
    rng = rng or np.random.default_rng(0)
    syls = text_to_syllables(text)
    if not syls:
        return np.zeros(int(SR * 0.3)), {}

    f0_base = float(params['f0_base'])
    var = float(params.get('f0_variation', 0.2))
    decl = float(params.get('f0_decl', 0.08))
    depth = float(params.get('tone_depth', 0.55))
    jit = float(params.get('jitter', 0.015))

    segs = [(syl_dur, s) for s in syls]
    n = int(sum(d if d else pause_dur for d, _ in segs) * SR) + SR // 2
    f0c = np.zeros(n)
    env = np.zeros(n)
    vseq = []
    t = 0.0
    for d, s in segs:
        s0 = int(t * SR)
        dur = pause_dur if d is None else d if s is not None else pause_dur
        s1 = min(int((t + dur) * SR), n)
        m = s1 - s0
        if m <= 0:
            t += dur
            continue
        if s is None:                       # 停顿
            env[s0:s1] = 0.0
            vseq.append(VOWELS['e'])
        else:
            vowel, tone = s
            base = f0_base * np.exp(var * rng.standard_normal() * 0.5)
            shape = np.interp(np.linspace(0, 1, m), np.linspace(0, 1, 4),
                              TONE_SHAPES[tone]) * depth
            if jit > 0:
                shape = shape + jit * 3.0 * rng.standard_normal(m)
            f0c[s0:s1] = base * np.exp(shape)
            env[s0:s1] = _win(m)
            vseq.append(VOWELS[vowel])
        t += dur

    voiced_mask = f0c > 0
    # ── 声源：脉冲串 ──
    src = np.zeros(n)
    if voiced_mask.any():
        inc = np.where(voiced_mask, f0c / SR, 0.0)
        phase = np.cumsum(inc)
        k = np.floor(phase)
        cross = np.where(np.diff(np.concatenate([[k[0]], k])) >= 1)[0]
        if len(cross) > 1:
            src[cross] = 1.0
            from scipy.signal import fftconvolve
            src = fftconvolve(src, np.hanning(61), mode='same')
    sv = float(np.sqrt((src[voiced_mask] ** 2).mean())) if voiced_mask.any() else 0.0
    src = src + sv * 10 ** (-GLOTTAL_DB / 20.0) * rng.standard_normal(n)

    # ── 声道 ──
    while len(vseq) < 2:
        vseq.append(VOWELS['e'])
    nv = len(vseq)
    xs = np.linspace(0, 1, nv)
    f1 = np.interp(np.linspace(0, 1, n), xs, [v[0] for v in vseq])
    f2 = np.interp(np.linspace(0, 1, n), xs, [v[1] for v in vseq])
    f3 = np.interp(np.linspace(0, 1, n), xs, [v[2] for v in vseq])
    y = np.zeros(n)
    nb = 8
    bs = n // nb
    for b in range(nb):
        s0 = b * bs
        s1 = n if b == nb - 1 else (b + 1) * bs
        y[s0:s1] = _reson(_reson(_reson(src[s0:s1], f1[s0], 80) * 0.9,
                                 f2[s0], 110) * 0.7, f3[s0], 160) * 0.5
    y = np.diff(y, prepend=0.0)                       # 唇辐射 +6dB/oct
    # 本底噪声
    sy = float(np.sqrt((y ** 2).mean()))
    y = y + sy * 10 ** (NOISE_FLOOR_DB / 20.0) * rng.standard_normal(n)
    y = y * env
    rms = np.sqrt((y ** 2).mean())
    if rms > 1e-8:
        y = y / rms * 0.098
    return y, {'f0_contour': f0c, 'voiced_mask': voiced_mask, 'n_syll': len(syls)}
