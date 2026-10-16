import ctypes, json, sys, os
from wasmtime import (Engine, Store, Module, Linker, Memory, MemoryType, Limits,
                      Table, TableType, Global, GlobalType, ValType, Val)

WASM='xmtls.wasm'; PAGES=1024
MEM_BASE=1024; HEAP_BASE=0x100000; STACK=0x2000000

engine=Engine(); store=Store(engine)
module=Module.from_file(engine,WASM)
linker=Linker(engine)
mem=Memory(store, MemoryType(Limits(PAGES,4096)))
linker.define(store,'env','memory',mem)

base = ctypes.cast(mem.data_ptr(store), ctypes.c_void_p).value
def rd(off,n): return ctypes.string_at(base+off, n)
def wr(off,b): ctypes.memmove(base+off, b, len(b))
def rdi32(off): return int.from_bytes(rd(off,4),'little')

def mem_pages():
    try: return mem.size(store)
    except Exception: return mem.size_bytes(store)//65536

def resize_heap(size):
    need=(int(size)+65535)//65536
    cur=mem_pages()
    if need>cur:
        try:
            r=mem.grow(store, need-cur)
        except Exception:
            return 0
        if r==-1: return 0
    return 1

def fd_write(fd, iovs, iovcnt, nwritten):
    total=0
    for k in range(iovcnt):
        p=rdi32(iovs+k*8); l=rdi32(iovs+k*8+4)
        if l:
            sys.stdout.write(rd(p,l).decode('utf-8','replace')); total+=l
    wr(nwritten, total.to_bytes(4,'little'))
    return 0

def _getentropy(buf,n):
    sys.stderr.write('[DBG] getentropy called n=%s\n'%n)
    try:
        wr(buf, os.urandom(int(n))); return 0
    except Exception: return -1
def _getrandom(buf,n,flags):
    sys.stderr.write('[DBG] getrandom called\n')
    try:
        wr(buf, os.urandom(int(n))); return int(n)
    except Exception: return -1


def rd_cstr(off):
    out=bytearray()
    while True:
        c=rd(off+len(out),1)
        if c==b'\x00' or not c: break
        out+=c
    return bytes(out).decode('utf-8','replace')

URFD=777
def _open(path, flags=0, mode=0):
    try: p=rd_cstr(path)
    except Exception: return -1
    if 'urandom' in p: return URFD
    if 'random' in p: return URFD
    return -1
def _read(fd, buf, n):
    if fd==URFD:
        try:
            wr(buf, os.urandom(int(n))); return int(n)
        except Exception: return -1
    return 0
def _close(fd): return 0

def fd_read(fd, iovs, cnt, nread):
    total=0
    for k in range(cnt):
        p=rdi32(iovs+k*8); l=rdi32(iovs+k*8+4)
        if l:
            wr(p, os.urandom(l)); total+=l
    wr(nread, total.to_bytes(4,'little'))
    return 0

SPECIAL={
         'fd_read': lambda *a: fd_read(a[0],a[1],a[2],a[3]),
         'fd_pread': lambda *a: fd_read(a[0],a[1],a[2],a[3]),
         '__sys_open': lambda *a: _open(a[0], a[1] if len(a)>1 else 0),
         '__sys_openat': lambda *a: _open(a[1], a[2] if len(a)>2 else 0),
         '__sys_read': lambda *a: _read(a[0],a[1],a[2]) if len(a)>2 else 0,
         '__sys_close': lambda *a: _close(a[0]),'getentropy': lambda *a: _getentropy(a[0],a[1]) if len(a)>=2 else 0,
         'getrandom': lambda *a: _getrandom(a[0],a[1],a[2]) if len(a)>=3 else -1,
         'emscripten_resize_heap': lambda *a: resize_heap(a[0]) if a else 1,
         'emscripten_get_heap_max': lambda *a: 0x7FFFFFFF,
         'fd_write': lambda *a: fd_write(a[0],a[1],a[2],a[3]),
         'proc_exit': lambda *a: None}

def stub_for(ft):
    res=list(ft.results)
    def f(*args):
        if not res: return None
        vals=[0 if str(r).startswith('i') else 0.0 for r in res]
        return vals[0] if len(vals)==1 else vals
    return f

for imp in module.imports:
    mo,nm,t=imp.module,imp.name,imp.type
    cn=t.__class__.__name__
    if 'Func' in cn:
        if nm in SPECIAL: linker.define_func(mo,nm,t,SPECIAL[nm])
        else: linker.define_func(mo,nm,t,stub_for(t))
    elif 'Table' in cn:
        linker.define(store,mo,nm,Table(store,TableType(t.element,Limits(200000,200000)),Val.funcref(None)))
    elif 'Global' in cn:
        vt=t.content; s=str(vt); mut=bool(t.mutable)
        if 'funcref' in s: val=Val.funcref(None)
        elif 'i32' in s:
            val=Val.i32({'__stack_pointer':STACK,'__memory_base':MEM_BASE,
                         '__table_base':0,'__heap_base':HEAP_BASE}.get(nm,0))
        elif 'i64' in s: val=Val.i64(0)
        else: val=Val.f64(0.0)
        linker.define(store,mo,nm,Global(store,GlobalType(vt,mut),val))

inst=linker.instantiate(store,module)
ex=inst.exports(store)
names=list(ex.keys())
print("实例化成功, 导出:", len(names))

for init in ['__wasm_apply_data_relocs','_initialize','__wasm_call_ctors']:
    if init in names:
        try: ex[init](store); print("已调用:", init)
        except Exception as e: print("调用",init,"失败:",e)

def cstr(s):
    b=s.encode('utf-8')+b'\x00'
    p=ex['malloc'](store,len(b)); wr(p,b); return p
def rdstr(p):
    out=bytearray()
    while True:
        c=rd(p+len(out),1)
        if c==b'\x00' or not c: break
        out+=c
    return bytes(out).decode('utf-8','replace')

client=ex['NewClient'](store)
print("NewClient ->", client)
payload=json.dumps({"hello":"world"},separators=(',',':'))
print("payload:", payload)
pp=cstr(payload)
out=ex['ClientEncrypt'](store,client,pp)
print("ClientEncrypt ->", out)
if out: print("密文(前120):", rdstr(out)[:120])
