"""★103 她去听 —— 35 段真人中文语音，特征全部从她自己的耳朵里来"""
import sys, os, json, glob
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
from core import real_voice as rv

ROOT = os.path.join(os.path.dirname(__file__), '..')


def job(p):
    try:
        r = rv.analyze_via_ear(p)
        r['file'] = os.path.basename(p)
        r['dir'] = os.path.basename(os.path.dirname(p))
        return r
    except Exception as e:
        return {'file': os.path.basename(p), 'error': str(e)}


if __name__ == '__main__':
    files = sorted(glob.glob(os.path.join(ROOT, 'data/cn_voice/*.mp3'))) + \
            sorted(glob.glob(os.path.join(ROOT, 'data/dialog_voice/*.mp3')))
    print('待听语音:', len(files), flush=True)
    with ProcessPoolExecutor(max_workers=8) as ex:
        out = list(ex.map(job, files))
    ok = [r for r in out if 'error' not in r and r.get('F0均值', 0) > 0]
    print('听到:', len(ok), '/', len(out), flush=True)

    def col(k):
        return np.array([r[k] for r in ok], float)

    summary = {}
    for k in ['时长', 'F0均值', 'F0标准差', 'F1', 'F2', 'jitter', 'AN均值', 'AN通道方差']:
        v = col(k)
        summary[k] = {'中位': float(np.median(v)), '均值': float(v.mean()),
                      'std': float(v.std()), '最小': float(v.min()), '最大': float(v.max())}
    print(json.dumps(summary, ensure_ascii=False, indent=1))

    # ★ 检查她听出来的东西有没有区分度
    for k in ['F1', 'F2', 'jitter', 'AN均值', 'AN通道方差']:
        v = col(k)
        print(f"  {k}: 唯一值 {len(np.unique(np.round(v, 6)))} / {len(v)}  跨度 {v.max()-v.min():.6g}")

    json.dump({'per_file': out, 'summary': summary},
              open(os.path.join(ROOT, 'data/exp103_listen.json'), 'w'),
              ensure_ascii=False, indent=1)
    print('已存 data/exp103_listen.json')
