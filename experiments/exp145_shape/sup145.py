import numpy as np, json, importlib.util, os
spec=importlib.util.spec_from_file_location('r','real145.py'); m=importlib.util.module_from_spec(spec)
import sys; sys.modules['r']=m
# 只借用函数, 不跑 main
exec(open('real145.py').read().split('def main')[0], m.__dict__)
OUT=os.path.dirname(os.path.abspath(__file__))
res={}
for kind in ['sustain','cycle']:
    z=m.collect(kind)
    zz=(z-z.mean())/(z.std() if z.std()>1e-12 else 1.0)
    row={}
    for lag in [1,3,6,10]:
        X,Y=m.make_features(zz,lag=lag)
        r_all=m.run(X,Y,'ALL'); r_rec=m.run(X,Y,'RECENT')
        ident=r_all['ident']
        row[lag]={'ALL':r_all['err'],'RECENT':r_rec['err'],'ident':ident,
                  'best_beats_ident': bool(min(r_all['err'],r_rec['err'])<ident)}
    res[kind]=row
    print('==',kind)
    for lag in sorted(row):
        r=row[lag]
        print('  lag %2d  ALL %.4f  RECENT %.4f  ident %.4f  beats=%s'%(lag,r['ALL'],r['RECENT'],r['ident'],r['best_beats_ident']))
json.dump(res,open(os.path.join(OUT,'result_145_sup.json'),'w'),indent=2)
print('WROTE result_145_sup.json')
