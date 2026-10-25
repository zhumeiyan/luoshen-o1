import os, json
HERE=os.path.dirname(os.path.abspath(__file__))
def t(name, fn):
    try:
        v=fn(); print(f"{name}: OK  {v!r}")
    except Exception as e:
        print(f"{name}: FAIL {type(e).__name__}: {e}")

def m1():
    p=os.path.join(HERE,"t1.txt"); f=open(p,"w+")
    f.write("hello"); f.flush(); f.seek(0); r=f.read(); f.close(); os.remove(p); return r
def m2():
    p=os.path.join(HERE,"t2.txt"); f=open(p,"w+")
    f.write("hello"); f.flush(); os.fsync(f.fileno()); f.seek(0); r=f.read(); f.close(); os.remove(p); return r
def m3():
    p=os.path.join(HERE,"t3.txt"); f=open(p,"w+")
    json.dump({"a":1},f); f.flush(); f.seek(0); r=f.read(); f.close(); os.remove(p); return r
def m4():
    p=os.path.join(HERE,"t4.txt")
    fd=os.open(p, os.O_RDWR|os.O_CREAT|os.O_TRUNC)
    os.write(fd, b"hello"); os.lseek(fd,0,0); r=os.read(fd,100); os.close(fd); os.remove(p); return r
def m5():
    p=os.path.join(HERE,"t5.txt"); f=open(p,"w+")
    f.write("hello"); f.flush(); f.close()
    g=open(p,"r"); r=g.read(); g.close(); os.remove(p); return r
t("w+ flush seek read", m1)
t("w+ flush fsync seek read", m2)
t("w+ json flush seek read", m3)
t("os.open O_RDWR lseek read", m4)
t("write close then reopen r", m5)
