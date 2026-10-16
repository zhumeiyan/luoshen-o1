"""耳朵通路：声波 -> 话筒(换能器) -> wav -> FFT(耳蜗频率分析) -> 频谱向量"""
import numpy as np, wave, struct
sr=16000; dur=1.0
t=np.linspace(0,dur,int(sr*dur),endpoint=False)
# 一段"语音样"复合声：基频 220Hz + 三个泛音，模拟话筒收到的声音
sig=(0.6*np.sin(2*np.pi*220*t)+0.4*np.sin(2*np.pi*440*t)
     +0.3*np.sin(2*np.pi*880*t)+0.2*np.sin(2*np.pi*1320*t))
sig=(sig*32767*0.7).astype(np.int16)
with wave.open("/data/workspace/luoshen-o1/.sense/mic.wav","wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(sig.tobytes())
print("mic.wav written:", len(sig), "samples @", sr, "Hz")
# 话筒换能：FFT -> 频谱
x=sig.astype(float)/32768.0
X=np.abs(np.fft.rfft(x*np.hanning(len(x))))
f=np.fft.rfftfreq(len(x),1.0/sr)
idx=np.argsort(X)[::-1][:6]
peaks=sorted(round(float(f[i])) for i in idx)
print("耳蜗换能输出(频谱峰值 Hz):", peaks)
