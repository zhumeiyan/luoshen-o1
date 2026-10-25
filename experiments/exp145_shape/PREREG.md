# 145 预注册（跑之前写死，跑完只做对质）

## 问题
144 发现：保持时间顺序是资产还是负债，取决于世界的形状
（monotone drift +0.0731 资产 / square 周期 -0.0387 负债 / stationary 跨0 无信息）。
但 144 里"形状"是实验者已知的。真实系统不知道自己处在什么世界里。

## 主张（H）
H1 可判定：只用**过去**的观测序列（不看标签、不看未来），能区分 drift 世界与非 drift 世界，
判对率显著高于随机；且在 stationary 上判 drift 率低（能产生假，不恒真）。
H2 可用：按判定结果切换记忆策略（drift→近因 / 非drift→全记忆）的 ADAPTIVE，
其下一步预测误差不劣于两种固定策略中较好的那个。
H3 判别器不是装饰：把判定结果随机化的 ADAPTIVE_RANDOM，误差显著劣于 ADAPTIVE。

## 判据（跑之前定死）
- G1 H1：drift 世界判 drift 率 > 0.5 且 stationary 世界判 drift 率 < 0.3（必须两边都成立）
- G2 H2：ADAPTIVE 误差 <= min(ALWAYS_RECENT, ALWAYS_ALL) + 0.02（容差）
- G3 H3：ADAPTIVE_RANDOM - ADAPTIVE > 0，bootstrap CI 不跨 0
- 阴性对照：stationary 世界里 ADAPTIVE 与两固定策略无显著差异（世界无形状可判时，切换无用）

## 阈值
theta 扫描 {1.0,1.5,2.0,3.0,4.0}，主结果报 theta=2.0，其余作敏感性，不挑好看的。

## 真实臂
真实 CPU jitter，两种真实模式：持续负载 vs 周期 idle/load 切换。
判据：判别器在两种真实模式上必须给出**不同**判定，否则判别器在真实数据上无区分力（判 FAIL）。
