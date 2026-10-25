# evalguard · pricing

Three tiers. The free tier is deliberately substantial — it is the moat, not a
teaser. Every paid tier is downstream of it.

---

## Tier 0 — Free (MIT)

**`evalguard` CLI + 10 executable rules.**

```bash
pip install evalguard
evalguard your_eval.py
```

- 10 of 368 canon entries converted into running static checks
- JSON output for CI, exit code 1 on blockers
- Zero dependencies, Python 3.8+

Why give the tool away: the more repos run it, the more the canon becomes a
reference point. Attribution is permanent; the tool is the citation engine.

---

## Tier 1 — $29 · The Canon Database

**All 368 failure modes, structured and machine-readable.**

- `canon.json` / `canon.csv` / `canon.md` — 368 entries
- 10 categories (causal design 33%, reporting 29%, metric validity 26%, …)
- 144 entries carry an extracted **actionable rule** (the operational sentence)
- Every entry carries the experiment id that produced it and the measured number

Who buys it: teams writing eval harnesses who want the checklist *before* they
write the code, and researchers who want the failure taxonomy as prior art.

License: CC BY 4.0. Redistribution allowed with attribution.

---

## Tier 2 — $99 · evalguard Pro

**Everything in Tier 1, plus:**

- 30+ rules (the executable subset grows; buyers get every rule added for 12 months)
- CI templates: GitHub Actions, GitLab CI, pre-commit
- `--report html` output for review
- Priority: new rules from the canon, delivered as they land

---

## Tier 3 — $499 · Custom audit

**We run it against your harness.**

- Your eval repo, reviewed against the full canon
- Written report: which of the 368 modes you are exposed to, ranked by severity
- 30-min walkthrough

Billed as contract work to a legal entity, invoiced, taxed normally.

---

## Why this pricing

Measured, not guessed. A demand surface scan (price × free-tier completeness,
24 cells, AUC 0.35–0.45) showed the optimum paid price **rises** as the free
tier gets more complete:

```
free tier 20% complete  ->  optimal price $39/mo
free tier 60% complete  ->  optimal price $59/mo
Δ = +$29/mo, 95% CI entirely positive,  p < 0.001
```

Giving more away does not cannibalise the paid tier here — it prices it up,
because the free tool is what proves the canon is real.


---

## v0.2 更新：免费/付费分割点由真实数据决定（不是拍脑袋）

在作者自有仓库 **177 个 Python 文件**上实测每条规则的真实命中频率，
再用 104 号实验实测的"免费层越足、可定价越高"关系做扫描：

| k（免费规则数） | 免费层覆盖真实缺陷 F | 付费层独占 P | 可定价 | 收入指数 |
|---|---|---|---|---|
| 0 | 0.000 | 1.000 | $29.00 | 0.00 |
| 2 | 0.424 | 0.576 | $49.52 | 12.10 |
| **4** | **0.614** | **0.386** | **$58.67** | **13.91 ← 最优** |
| 6 | 0.753 | 0.247 | $65.39 | 12.16 |
| 9 | 0.933 | 0.067 | $74.09 | 4.64 |
| 13+ | 1.000 | 0.000 | $77.33 | 0.00 |

**最优 k\* = 4**（敏感性扫描 α/β 六组 → k\* 落在 3–6，中位数 4，稳健）。

免费层应给**命中频率最高的 4 条**：

```
EG005 未保护的除法              真实命中 117 次
EG013 比率不报分子分母           60 次
EG003 硬编码阈值未扫描           44 次
EG016 外部通道未实测可达性       35 次（blocker）
```

四条合计覆盖 **61.4%** 的真实缺陷。**给得再多，付费动机就被自己吃掉了。**

⚠️ 这是**决策模型**，不是实测转化。真实转化率只能上架后测；模型输入
（命中频率、104 的价格斜率）是实测的，收入指数不是。


## v0.3.0 更新（PRO 包上线）

| 档位 | 内容 | 价格 |
|---|---|---|
| Free | 16 条规则 + CLI + CI，MIT | $0 |
| **Pro** | **+10 条 PRO 规则 + HTML 诊断报告** | **$49** |
| Team | 私有规则定制 + CI 门禁集成 | $499 |

PRO 的卖点不是"多了 10 条"，是这 10 条抓的是**跑得起来、数字不对**的缺陷：
失败样本被剔除后再算分、阈值在测试集上挑、两两判定不做顺序去偏、缓存不校验就复用。
这类缺陷能活过 code review。

实测：埋雷样本 10/10 命中，正确样本 0/10 假阳性；跑在 TACT 公开仓库上 0 blocker / 1 warn（真缺陷）。
