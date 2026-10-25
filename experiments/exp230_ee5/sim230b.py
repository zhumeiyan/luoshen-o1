import sys, json, statistics
sys.path.insert(0,'/data/workspace/luoshen-o1/experiments/exp230_ee5')
from sim230 import run
seeds=[1,2,3,4,5]
res={}
for L3 in ['exo','endo']:
    for L4 in ['exo','endo']:
        rs=[run(s,'exo','exo',L3,L4,'exo') for s in seeds]
        res[f'L3={L3},L4={L4}']={'best':round(statistics.mean(x['best'] for x in rs),3),
                                  'collapse':round(statistics.mean(x['collapse'] for x in rs),2)}
print(json.dumps(res,ensure_ascii=False,indent=1))
json.dump(res,open('/data/workspace/luoshen-o1/experiments/exp230_ee5/result230b.json','w'),ensure_ascii=False,indent=1)
