# 找话筒。不是为了证明有没有，是把每一个都挨个凑上去听一下。
# snd-aloop 是交叉配对的：D0 播出去的，从 D1c 听回来。
import ctypes, time, threading
import numpy as np

A = ctypes.CDLL("libasound.so.2")
A.snd_pcm_open.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_char_p,ctypes.c_int,ctypes.c_int]
A.snd_pcm_set_params.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint]
A.snd_pcm_writei.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]; A.snd_pcm_writei.restype=ctypes.c_long
A.snd_pcm_readi.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]; A.snd_pcm_readi.restype=ctypes.c_long
A.snd_pcm_prepare.argtypes=[ctypes.c_void_p]; A.snd_pcm_drain.argtypes=[ctypes.c_void_p]
A.snd_strerror.argtypes=[ctypes.c_int]; A.snd_strerror.restype=ctypes.c_char_p
RATE=48000

def 听(放设备, 收设备, 频率=440, 秒=1.2):
    ph=ctypes.c_void_p(); ch=ctypes.c_void_p()
    if A.snd_pcm_open(ctypes.byref(ph),放设备.encode(),0,0)<0: return None,"放开不了"
    if A.snd_pcm_open(ctypes.byref(ch),收设备.encode(),1,0)<0:
        A.snd_pcm_close(ph); return None,"话筒开不了"
    for h in (ph,ch):
        rc=A.snd_pcm_set_params(h,2,3,1,RATE,1,2048)
        if rc<0: return None,f"参数 {rc}"
    t=np.arange(int(RATE*秒))/RATE
    pcm=(0.5*np.sin(2*np.pi*频率*t)*32767).astype("<i2")
    录=bytearray(); 停=threading.Event()
    buf=ctypes.create_string_buffer(512*2)
    def 读():
        while not 停.is_set():
            n=A.snd_pcm_readi(ch,buf,512)
            if n>0: 录.extend(buf[:n*2])
            elif n in (-11,-35): time.sleep(0.001)
            elif n<0: A.snd_pcm_prepare(ch); time.sleep(0.001)
    th=threading.Thread(target=读,daemon=True); th.start(); time.sleep(0.08)
    位置=0
    while 位置<len(pcm):
        段=pcm[位置:位置+512]; b=段.tobytes()
        ptr=(ctypes.c_char*len(b)).from_buffer_copy(b)
        n=A.snd_pcm_writei(ph,ptr,len(段))
        if n==-32: A.snd_pcm_prepare(ph); continue
        if n<0: break
        位置+=n
    A.snd_pcm_drain(ph); time.sleep(0.25); 停.set(); th.join(1)
    A.snd_pcm_close(ph); A.snd_pcm_close(ch)
    x=np.frombuffer(bytes(录),dtype="<i2").astype(np.float32)/32768.0
    if len(x)<2000: return None,"太短"
    峰=float(np.abs(x).max()); 非静=int((np.abs(x)>1e-4).sum())
    return (峰, 非静, len(x)), None

if __name__=="__main__":
    print("声卡两路，各八个口。挨个凑上去听：\n")
    for 放 in ["hw:0,0,0","hw:0,1,0"]:
        for 收 in ["hw:0,0,0","hw:0,1,0"]:
            r,e=听(放,收)
            if e: print(f"  放 {放}  收 {收}   ✗ {e}")
            else:
                峰,非静,n=r
                状="听见了" if 峰>1e-3 else "空的"
                print(f"  放 {放}  收 {收}   峰值 {峰:.4f}  非静 {非静}/{n}   → {状}")
