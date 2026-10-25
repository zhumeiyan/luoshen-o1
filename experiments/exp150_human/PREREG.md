# 150 预注册（跑之前写死，跑完只做对质）

## 环境实测（probe_env.py，决定 tick 预算）
open 182.50ms / listdir 65.56ms / remove 56.10ms / spawn 9.8ms / mkdir+rmtree 314.23ms
=> 每 tick 开文件不可行，全部改常驻 fd；spawn 便宜，文化格可多 rep。

## 子实验与判据
S1 独白：三臂 pre(先说后做) / post(先做后说) / off
   H1a: pre 完成率 > off，CI 不跨 0
   H1b: post 不 > off（若 post 也显著优于 off，说明起作用的是"写"不是"说在动作前"，H1a 的解释作废）
S2 自传：causal vs log，在真 do() 上检验
   H2: causal 预测优于 log，CI 不跨 0
S3 知死：真 rmtree(不可恢复) vs 真 move(可恢复)
   H3: mortal 外化率 > recoverable，CI 不跨 0
S4 文化：真 spawn 子进程，三臂 inherit / scratch / wrong
   H4: inherit > scratch 且 wrong < inherit（wrong 是能产生假的臂）
