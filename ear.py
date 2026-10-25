# -*- coding: utf-8 -*-
"""耳朵。libasound.so.2 真开 PCM，边放边录，验证放出去的和收回来的是不是同一个。
provenance 判据：系统调用真成功才算 REAL。失败报 errno，不静默、不猜。"""
import ctypes, ctypes.util, time, threading
import numpy as np

A = ctypes.CDLL("libasound.so.2")
A.snd_pcm_open.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
A.snd_pcm_set_params.argtypes = [ctypes.c_void_p]*0 + [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_uint, ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
A.snd_pcm_writei.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
A.snd_pcm_writei.restype = ctypes.c_long
A.snd_pcm_readi.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
A.snd_pcm_readi.restype = ctypes.c_long
A.snd_pcm_prepare.argtypes = [ctypes.c_void_p]
A.snd_pcm_drain.argtypes = [ctypes.c_void_p]
A.snd_strerror.argtypes = [ctypes.c_int]; A.snd_strerror.restype = ctypes.c_char_p

S16, RW, OUT, IN = 2, 3, 0, 1
RATE, CH, PERIOD = 48000, 1, 512

def err(c): return A.snd_strerror(c).decode("utf-8","replace")

def open_pcm(stream, period=PERIOD):
    h = ctypes.c_void_p()
    rc = A.snd_pcm_open(ctypes.byref(h), b"default", stream, 0)
    if rc < 0: return None, f"open {rc}:{err(rc)}"
    rc = A.snd_pcm_set_params(h, S16, RW, CH, RATE, 1, period*8)
    if rc < 0:
        A.snd_pcm_close(h); return None, f"set_params {rc}:{err(rc)}"
    return h, None

if __name__ == "__main__":
    print("=== 声卡 ===")
    print("  " + open("/proc/asound/cards").read().strip().splitlines()[0].strip())

    ph, e1 = open_pcm(OUT)
    ch_, e2 = open_pcm(IN)
    print(f"  playback {'OK' if ph else 'FAIL '+e1}")
    print(f"  capture  {'OK' if ch_ else 'FAIL '+e2}")
    if not (ph and ch_): raise SystemExit(1)

    # 信号：440 + 880 Hz，2 秒
    t = np.arange(RATE*2)/RATE
    sig = 0.45*np.sin(2*np.pi*440*t) + 0.25*np.sin(2*np.pi*880*t)
    pcm = (sig*32767).astype("<i2")

    rec = bytearray(); stop = threading.Event()
    cbuf = ctypes.create_string_buffer(PERIOD*2)
    def reader():
        while not stop.is_set():
            n = A.snd_pcm_readi(ch_, cbuf, PERIOD)
            if n > 0: rec.extend(cbuf[:n*2])
            elif n in (-11,-35): time.sleep(0.001)
            elif n < 0:
                A.snd_pcm_prepare(ch_)     # EPIPE(-32) overrun：复位再读
                time.sleep(0.001)

    th = threading.Thread(target=reader, daemon=True); th.start()
    time.sleep(0.05)

    # 播：循环写满
    total = len(pcm); off = 0; wrote = 0
    while off < total:
        chunk = pcm[off:off+PERIOD]
        b = chunk.tobytes()
        ptr = (ctypes.c_char*len(b)).from_buffer_copy(b)
        n = A.snd_pcm_writei(ph, ptr, len(chunk))
        if n == -32: A.snd_pcm_prepare(ph); continue
        if n < 0: print("  writei", n, err(n)); break
        off += n; wrote += n
    A.snd_pcm_drain(ph)
    print(f"\n=== 放 ===\n  writei 共 {wrote}/{total} 帧")

    time.sleep(0.3); stop.set(); th.join(timeout=1)
    A.snd_pcm_close(ph); A.snd_pcm_close(ch_)

    x = np.frombuffer(bytes(rec), dtype="<i2").astype(np.float32)/32768.0
    print(f"\n=== 录 ===\n  收到 {len(x)} 帧，非零 {int((np.abs(x)>1e-4).sum())}")
    if len(x) < 4096:
        print("  样本不足，不分析（不猜）"); raise SystemExit(0)

    # 谱峰
    N = 8192; w = x[:N]*np.hanning(N)
    sp = np.abs(np.fft.rfft(w)); fr = np.fft.rfftfreq(N, 1.0/RATE)
    idx = np.argsort(sp)[-4:][::-1]
    peaks = sorted(set(round(float(fr[i])) for i in idx))
    print(f"  谱峰: {peaks} Hz   （放的是 440 + 880）")

    # 跟原信号对齐求相关（容忍延迟）
    best = -1; bl = 0
    ref = sig[:len(x)] if len(x) <= len(sig) else np.pad(sig, (0, len(x)-len(sig)))
    for lag in range(0, min(RATE, len(x)-4096), 64):
        r = np.corrcoef(ref[:len(x)-lag], x[lag:])[0,1]
        if r > best: best, bl = r, lag
    print(f"  与原信号最佳相关 r={best:.4f} @ 延迟 {bl} 帧 ({bl/RATE*1000:.1f} ms)")
    print(f"\n  ★ 放出去的 = 收回来的？ r={best:.4f}")
