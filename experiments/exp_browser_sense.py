#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★ 浏览器感官：把"看"从挂件变成硬依赖
========================================================
★ 上一轮的失败（★33 记录）：
    把定位精度调成 0（等于让它瞎）→ 输出【完全不变】
    ★ 证明"看"根本没参与输出，是挂件

★ 本实验的判据（可证伪）：
    【正常看】与【瞎掉/内容被替换】的输出必须【不同】
    如果还是相同 → 仍然是假依赖，判 ❌

★ 三层对照：
    A 正常看真网页
    B 看失败（403）—— 必须 raise，不许回退到先验
    C 内容被替换（给错误内容）—— 输出必须跟着变
"""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.browser_sense import BrowserSense, SeenWeb, describe, _now

if __name__ == "__main__":
    print("="*88); print(" ★ 浏览器感官：看，必须是硬依赖"); print("="*88)
    ok = {}

    # ---------- 1 真能打开吗 ----------
    print("\n【实验1】真的去看，记录每一个的 HTTP 状态")
    print("-"*88)
    b = BrowserSense(strict=False)
    targets = ["https://mail.qq.com", "https://www.baidu.com",
               "https://github.com/zhumeiyan/luoshen-eo",
               "https://gitee.com/zhu-meiyan1/luoshen-eo"]
    seen = {}
    for u in targets:
        s = b.look(u, timeout=15)
        seen[u] = s
        print(f"  {'✅' if s.ok else '❌'} {u:<48} HTTP {s.status}  "
              f"{s.nchars:>7} chars  {s.elapsed:.2f}s")
        if s.err:
            print(f"      err: {s.err[:80]}")
    n_ok = sum(1 for s in seen.values() if s.ok)
    ok["① ★ 至少有一个网址真能打开（不是全 403）"] = bool(n_ok >= 1)
    ok["② ★ 打不开的如实报 403，不伪装成空内容"] = bool(
        all(s.status == "HTTPERROR 403" for s in seen.values() if not s.ok))
    print(f"\n  ★ 能开 {n_ok}/{len(targets)}。打不开的就是 403，如实报。")

    # ---------- 2 ★ 看完之后说出来 ----------
    print("\n【实验2】★ 看完之后说出来（只能说看到的）")
    print("-"*88)
    good = next((s for s in seen.values() if s.ok and s.nchars > 100), None)
    if good:
        print(describe(good))
        # ★ 从真实内容里读，读不到返回 None
        f = b.read_field(good, "title")
        print(f"\n  从内容里读 title：{f if f else '（没读到，不猜）'}")
        ok["③ ★ 能报出 URL/状态/字符数/哈希/时刻"] = bool(
            good.url and good.status and good.nchars > 0 and good.sha)
        ok["④ ★ 内容哈希不为 None（内容真的抓到了）"] = bool(good.sha is not None)
    else:
        ok["③ ★ 能报出 URL/状态/字符数/哈希/时刻"] = False
        ok["④ ★ 内容哈希不为 None（内容真的抓到了）"] = False

    # ---------- 3 ★★ 硬依赖：看失败必须 raise ----------
    print("\n【实验3】★★ 硬依赖测试：看失败 → 必须答不出来")
    print("-"*88)
    bs = BrowserSense(strict=True)
    bad = next((s for s in seen.values() if not s.ok), None)
    raised = False
    if bad:
        try:
            bs.must_look(bad.url, timeout=10)
        except RuntimeError as e:
            raised = True
            print(f"  ✅ raise 了：{str(e)[:110]}")
    ok["⑤ ★★ 看失败时 must_look 抛错（不许回退到先验）"] = bool(raised)
    # 对照：非严格模式不抛
    b2 = BrowserSense(strict=False)
    not_raised = True
    try:
        b2.must_look(bad.url, timeout=10)
    except RuntimeError:
        not_raised = False
    ok["⑥ ★ 对照：strict=False 时不抛（证明 raise 是机制不是巧合）"] = bool(not_raised)
    print(f"  ★ strict=True 抛错 / strict=False 不抛 —— 是机制在起作用")

    # ---------- 4 ★★★ 消融：内容被替换，输出必须跟着变 ----------
    print("\n【实验4】★★★ 消融对照：内容被替换 → 输出必须变")
    print("-"*88)
    print("  ★ 这是上一轮【失败】的那个测试的修正版")
    print("    上一轮：定位精度=0 → 输出不变 → 判假依赖 ❌")

    def answer_from(s: SeenWeb, key: str) -> str | None:
        """★ 答案【只能】来自看到的内容。"""
        return b.read_field(s, key)

    # 构造三个"看到"：真内容 / 被替换 / 空
    if good:
        real = good
        fake = SeenWeb(good.url, True, good.status,
                       "TITLE: 这是一个被替换掉的假页面\nBODY: 内容完全不同",
                       None, _now(), 0.1)
        empty = SeenWeb(good.url, True, good.status, "", None, _now(), 0.1)

        a_real = answer_from(real, "title")
        a_fake = answer_from(fake, "title")
        a_empty = answer_from(empty, "title")
        print(f"  真内容  → {str(a_real)[:70]}")
        print(f"  被替换  → {str(a_fake)[:70]}")
        print(f"  空内容  → {str(a_empty)[:70]}")

        ok["⑦ ★★★ 被替换后输出【改变】（不再是挂件）"] = bool(
            str(a_real) != str(a_fake))
        ok["⑧ ★★ 空内容时返回 None（不编造）"] = bool(a_empty is None)
        print(f"\n  ★ 真内容 vs 被替换：{'不同 ✅ 真依赖' if str(a_real)!=str(a_fake) else '相同 ❌ 还是挂件'}")
        print(f"  ★ 空内容：{'None（不编造）✅' if a_empty is None else '编了内容 ❌'}")
    else:
        ok["⑦ ★★★ 被替换后输出【改变】（不再是挂件）"] = False
        ok["⑧ ★★ 空内容时返回 None（不编造）"] = False

    # ---------- 5 留痕 ----------
    print("\n【实验5】★ 每次看都留证据")
    print("-"*88)
    shots = os.path.join(HERE, ".sense", "shots")
    n = len([f for f in os.listdir(shots) if f.endswith(".json")]) \
        if os.path.isdir(shots) else 0
    print(f"  留痕文件 {n} 个（含 URL/时刻/HTTP状态/内容哈希）")
    ok["⑨ ★ 留痕目录有记录"] = bool(n > 0)
    if n:
        one = sorted(os.listdir(shots))[-1]
        d = json.load(open(os.path.join(shots, one), encoding="utf-8"))
        print(f"  最新一条：{d['url']}  HTTP {d['status']}  sha {d['sha']}  {d['ts']}")
        ok["⑩ ★ 留痕含 URL/状态/哈希/时刻四项"] = bool(
            all(k in d for k in ("url", "status", "sha", "ts")))

    print("\n"+"="*88); print(" 判据汇总"); print("="*88)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未做到：真浏览器渲染（这是 urllib 抓 HTML，不是 Chrome 渲染）")
    print("  ❌ 未做到：解析 DOM/JS 动态内容")
    print("  ⚠️ github/gitee 仍是 403 —— 出口策略挡的，不是能力问题")
    json.dump({k: bool(v) for k, v in ok.items()},
              open(os.path.join(HERE, ".sense", "browser.json"), "w"),
              ensure_ascii=False, indent=1)
