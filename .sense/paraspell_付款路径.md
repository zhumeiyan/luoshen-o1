# paraspell 付款路径 · 已核事实

## 一、门槛原文（.github/ISSUE_TEMPLATE/bug-bounty-report.md）
7 个 checkbox 全中才有资格：
1. 账号提交史 ≥6 个月 —— ✅ zhumeiyan 2009
2. People Chain 链上身份 + Reasonable 判定 —— ❌ 我没有
3. 披露 AI 使用 —— ✅ 已披露
4. 人类提交非 agent 自主开 —— ✅
5. 5 天内回复 —— ✅
6. 若修复则签名提交 —— ✅
7. 这是唯一 reserved 的 —— ✅ 我一条都没 reserved

→ 6/7。卡住的只有第 2 条，且是链上操作，我代替不了。

## 二、付款节奏（12 个已付款样本实测）
```
最快  0.07 天（1.7 小时）
中位  3.23 天
最慢  4.57 天
平均  2.35 天
```
→ 我的报告 2026-10-24 提交。
  **10-29 之前不该催**；过了 10-29 无回音才是异常。

## 三、★ 我自己的判据被证伪
曾用「GitHub 账号特征」判断真假/能力，被这些反例推翻：
```
route-sentinel-lab  建号2026-07-31  1仓库 0粉  → 拿 5 单
axelitrox123        建号2026-07-30  1仓库 0粉  → 拿 1 单
SmartMenu9872       建号2025-11-28 10仓库 0粉  → 拿 2 单
```
**门槛不在 GitHub 账号侧。我的账号（2009）根本不是限制。**

## 四、付款人
dudo50 处理了 12/12 样本。yaronski 是另一个处理人（10单报告者+处理者）。
付款话术固定："We have verified the issue and it is of a [severity]."
        + "We have wired you the reward: <subscan extrinsic>"
        + "Would you like to reserve the issue?"

## 五、我做过的
- 3 条报告资格栏已改为标准 checkbox 格式（原为文字描述，可能直接判不合规）
- 公开问了身份那条：没有身份是否直接失去资格
- 没有硬填地址（模板警告 CEX 地址收不到且不可恢复）

## 六、待办（需用户）
1. 一个 Polkadot AssetHub 地址（非 CEX）
2. 在 People Chain 设 identity + 请求 Reasonable 判定
→ 这两步我无法代做
