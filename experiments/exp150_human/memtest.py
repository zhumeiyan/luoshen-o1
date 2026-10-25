import os, mmap, json
from multiprocessing import shared_memory
HERE=os.path.dirname(os.path.abspath(__file__))
def t(n,f):
    try: print(f"{n}: OK {f()!r}")
    except Exception as e: print(f"{n}: FAIL {type(e).__name__}: {e}")

# 1) mmap 文件：写后同映射读回
def m1():
    p=os.path.join(HERE,"mm.bin")
    f=open(p,"wb"); f.write(b"\x00"*4096); f.flush(); f.close()
    g=open(p,"r+b"); mm=mmap.mmap(g.fileno(),4096)
    mm[:5]=b"hello"; r=mm[:5]; mm.flush()
    mm.close(); g.close(); os.remove(p); return r
# 2) shared_memory 写后立即读
def m2():
    shm=shared_memory.SharedMemory(create=True,size=1024)
    shm.buf[:5]=b"hello"; r=bytes(shm.buf[:5]); shm.close(); shm.unlink(); return r
t("mmap file write+same-map read", m1)
t("shared_memory write+read", m2)
