# -*- coding: utf-8 -*-
"""实测：国际顶级 AI 项目 README 首屏结构"""
import json, urllib.request, os, time, re, base64, statistics

T = os.environ.get("GH_TOKEN", "ghp_REDACTED")


def g(p, tries=3):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                "https://api.github.com" + p,
                headers={"Authorization": "token " + T, "User-Agent": "x",
                         "Accept": "application/vnd.github+json"})
            return json.loads(urllib.request.urlopen(r, timeout=30).read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(10)


REPOS = [("langchain-ai", "langchain"), ("vllm-project", "vllm"), ("ollama", "ollama"),
         ("langgenius", "dify"), ("run-llama", "llama_index"), ("huggingface", "transformers"),
         ("All-Hands-AI", "OpenHands"), ("langchain-ai", "langgraph"),
         ("deepset-ai", "haystack"), ("milvus-io", "milvus"),
         ("langfuse", "langfuse"), ("crewAIInc", "crewAI"),
         ("microsoft", "autogen"), ("Significant-Gravitas", "AutoGPT")]

print("=" * 78)
print("实测：14 个国际顶级 AI 项目 README 首屏结构")
print("=" * 78)
rows = []
for o, r in REPOS:
    try:
        d = g("/repos/%s/%s" % (o, r))
        rd = g("/repos/%s/%s/readme" % (o, r))
        txt = base64.b64decode(rd["content"]).decode("utf-8", "ignore")
    except Exception as e:
        print("  %s/%s: 读不到 %s" % (o, r, repr(e)[:60]))
        continue
    lines = [l for l in txt.splitlines() if l.strip()]
    head = ""
    for l in lines:
        s = re.sub(r"<[^>]+>", "", l).strip()
        if s and not s.startswith("#") and len(s) > 8:
            head = s
            break
    badges = len(re.findall(r"!\[[^\]]*\]\(", txt[:3000]))
    has_demo = bool(re.search(r"(demo|playground|colab|try it|live)", txt[:4000], re.I))
    has_bench = bool(re.search(r"(benchmark|throughput|latency|tokens/s|accuracy|score)", txt, re.I))
    has_arch = bool(re.search(r"architecture", txt, re.I)
                    or "```mermaid" in txt
                    or re.search(r"!\[[^\]]*(architect|diagram|overview)", txt, re.I))
    has_install = bool(re.search(r"(pip install|docker run|npm i|quickstart|getting started)", txt, re.I))
    rows.append((f"{o}/{r}", d.get("stargazers_count", 0), len(head), badges,
                 has_demo, has_bench, has_arch, has_install, head))
    print("\n  %s/%s  ★%s" % (o, r, d.get("stargazers_count", 0)))
    print("    tagline: %s" % head[:78])
    print("    徽章%d个  在线试玩%s  benchmark%s  架构图%s  安装段%s" %
          (badges, "✅" if has_demo else "—", "✅" if has_bench else "—",
           "✅" if has_arch else "—", "✅" if has_install else "—"))
    time.sleep(1.2)

print("\n" + "=" * 78)
n = len(rows)
print("样本 %d 个" % n)
for lbl, idx in [("有在线试玩", 4), ("有benchmark", 5), ("有架构图", 6), ("有安装段", 7)]:
    c = sum(1 for r in rows if r[idx])
    print("  %-12s %d/%d  (%.0f%%)" % (lbl, c, n, 100.0 * c / n))
tl = [r[2] for r in rows if r[2]]
if tl:
    print("  tagline 长度中位数 ≈ %d 字符" % sorted(tl)[len(tl) // 2])
    print("  徽章数中位数 %s" % statistics.median([r[3] for r in rows]))

json.dump([{"repo": r[0], "stars": r[1], "tagline": r[8], "badges": r[3],
            "demo": r[4], "bench": r[5], "arch": r[6], "install": r[7]} for r in rows],
          open("/data/workspace/luoshen-o1/名片/scan.json", "w"),
          ensure_ascii=False, indent=1)
