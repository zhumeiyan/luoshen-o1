#!/usr/bin/env python3
import os, time, json, subprocess, tempfile, shutil
os.chdir(os.path.dirname(os.path.abspath(__file__)))
R={}
tmp = tempfile.mkdtemp(dir=".")
t=time.time()
for i in range(20):
    with open(os.path.join(tmp,f"a{i}.txt"),"w") as f: f.write("x")
R["open_ms"] = round((time.time()-t)/20*1000,4)
t=time.time()
for i in range(20): os.listdir(tmp)
R["listdir_ms"] = round((time.time()-t)/20*1000,4)
t=time.time()
for i in range(20):
    try: os.remove(os.path.join(tmp,f"a{i}.txt"))
    except: pass
R["remove_ms"] = round((time.time()-t)/20*1000,4)
t=time.time()
for i in range(3):
    subprocess.run(["python3","-c","print(1)"],capture_output=True)
R["spawn_ms"] = round((time.time()-t)/3*1000,1)
R["mkdir_ms"] = None
t=time.time()
for i in range(10):
    d=os.path.join(tmp,f"d{i}"); os.mkdir(d); shutil.rmtree(d,ignore_errors=True)
R["mkdir_rmtree_ms"] = round((time.time()-t)/10*1000,4)
shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps(R, indent=1, ensure_ascii=False))
json.dump(R, open("result_env.json","w"), ensure_ascii=False, indent=1)
