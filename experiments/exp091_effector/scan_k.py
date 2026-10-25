import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from handeye4 import run, paired
def cell(eye, hand, ksa, n=12):
    rs=[run(s, eye, hand, k_seek_arr=ksa) for s in range(n)]
    return dict(skew=float(np.mean([r['skew'] for r in rs])),
                alive=float(np.mean([r['alive'] for r in rs])),
                skews=[r['skew'] for r in rs])
print(f"{'ksa':<6}{'格':<12}{'skew':<12}{'存活':<8}{'diff':<12}{'CI'}")
res={}
for ksa in (0.1,0.2,0.3,0.5):
    b=cell(0.0,0.0,ksa)
    for nm,(e,h) in {'基线':(0,0),'眼噪':(0.3,0),'手噪':(0,0.3)}.items():
        c=cell(e,h,ksa)
        r=paired(c['skews'], b['skews']) if nm!='基线' else dict(diff=0.0,ci=[0,0],sig=False)
        print(f"{ksa:<6}{nm:<12}{c['skew']:<12.6f}{c['alive']:<8.3f}{r['diff']:<+12.6f}"
              f"[{r['ci'][0]:+.5f},{r['ci'][1]:+.5f}]{'*' if r['sig'] else ''}")
        res[f'{ksa}_{nm}']=dict(skew=c['skew'],alive=c['alive'],diff=r['diff'],ci=r['ci'],sig=r['sig'])
    print()
json.dump(res, open('scan_k.json','w'), ensure_ascii=False, indent=1)
