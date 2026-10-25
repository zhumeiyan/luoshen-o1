"""exp137: per-domain density scan of the SHIPPED rule set (parallel).

Pre-registered in PREREG.md before any data was fetched.
Gates: density >= 5.0 /100KB, strict precision >= 60%, n >= 5 with
Wilson lower bound >= 0.45.

Per-file hard timeout (10 s) so one pathological file cannot stall the run
and cannot silently shrink the denominator.
"""
import sys, json, pathlib, collections, signal, multiprocessing as mp
sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")

CORP = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137/corpus5")
BASE = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp137")

class TO(Exception):
    pass

def _alarm(sig, frm):
    raise TO()

def work(fname):
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, 10.0)
    try:
        from evalguard import cli
        from evalguard.cli import scan
        cli.PRO_ON[0] = True
        return fname, scan(str(CORP / fname))
    except TO:
        return fname, [{"eg_id": "TIMEOUT", "severity": "info", "hits": [{"line": 0, "hit": "10s"}]}]
    except Exception as e:
        return fname, [{"eg_id": "CRASH", "severity": "info", "hits": [{"line": 0, "hit": str(e)[:80]}]}]
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

if __name__ == "__main__":
    files = sorted(p.name for p in CORP.glob("*.py"))
    with mp.Pool(8) as pool:
        res = dict(pool.imap_unordered(work, files, chunksize=4))
    (BASE / "scan5.json").write_text(json.dumps(res, indent=1))

    man = []
    for mf in ("manifest5.json", "manifest5b.json"):
        p = BASE / mf
        if p.exists():
            man += json.loads(p.read_text())
    dom_of = {m["file"]: m["domain"] for m in man}

    from evalguard.classes import shipped
    byt, nf, hits, files_c, rule = (collections.Counter() for _ in range(5))
    findings = []
    for f, fs in sorted(res.items()):
        d = dom_of.get(f) or f.split("__")[0]
        files_c[d] += 1
        byt[d] += (CORP / f).stat().st_size
        nh = 0
        for r in fs:
            eg = r.get("eg_id", "?")
            if eg in ("CRASH", "TIMEOUT", "EG000"):
                rule[eg] += 1
                continue
            if not shipped(eg):
                continue
            for h in r.get("hits", []):
                hits[d] += 1
                rule[eg] += 1
                nh += 1
                findings.append(dict(domain=d, file=f, eg=eg, line=h.get("line", 0),
                                     hit=str(h.get("hit", ""))[:200]))
        if nh:
            nf[d] += 1

    print(f"{'domain':<12}{'files':>6}{'KB':>9}{'hits':>6}{'per100KB':>10}{'silent':>10}")
    print("-" * 55)
    rows = []
    for d in sorted(files_c):
        kb = byt[d] / 1000.0
        rate = hits[d] / (kb / 100.0) if kb else 0.0
        print(f"{d:<12}{files_c[d]:>6}{kb:>9.1f}{hits[d]:>6}{rate:>10.2f}{files_c[d]-nf[d]:>4}/{files_c[d]:<5}")
        rows.append(dict(domain=d, files=files_c[d], kb=round(kb, 1), hits=hits[d],
                         per100kb=round(rate, 3), silent=f"{files_c[d]-nf[d]}/{files_c[d]}"))
    print("-" * 55)
    print("rule counts:", rule.most_common())
    print("total shipped findings:", len(findings))
    (BASE / "density.json").write_text(json.dumps(rows, indent=1))
    (BASE / "findings.json").write_text(json.dumps(findings, indent=1))
