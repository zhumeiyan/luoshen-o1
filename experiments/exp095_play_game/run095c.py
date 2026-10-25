import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from exp095_play_game import *
OUT = os.path.dirname(os.path.abspath(__file__))
RENDER_COST, DECIDE_COST = 0.5, 20.0
WIDTHS = [8,16,32,64,128,256,512,800]
G = {}
for T in [600.0, 1500.0, 3000.0, 6000.0]:
    row = {}
    for wr in WIDTHS:
        frames = max(2, int(T/(wr*RENDER_COST+DECIDE_COST)))
        sc = Screen(keep_history=True)
        f = run(n=48, mode='closed', eye=Eye(sc, cols=min(wr, W_FB)),
                screen=sc, max_steps=frames, hand=None)
        f['frames'] = frames
        row[wr] = f
        print(f'T={T:6.0f}  {wr:4d}列/帧 → {frames:3d}帧  命中率 {f["rate"]:.3f}', flush=True)
    peak = max(WIDTHS, key=lambda w: row[w]['rate'])
    print(f'  → T={T:.0f} 峰值在 {peak} 列/帧\n', flush=True)
    G[T] = row
json.dump({str(k): {str(a): b for a, b in v.items()} for k, v in G.items()},
          open(os.path.join(OUT,'result095c.json'),'w'), ensure_ascii=False, indent=1)
