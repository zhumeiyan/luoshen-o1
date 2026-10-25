# 仓库结构

**一个仓库装全部。** 原先分散的 luoshen-o1 与 luoshen-eo 已合并于此。

入库文件总数：**3981**

| 目录 | 文件数 | 内容 |
|---|---:|---|
| `experiments` | 1968 | 实验与判据（每层一套） |
| `感官桥` | 735 | 感官素材图 |
| `evidence` | 227 | 证据留痕 |
| `data` | 213 | 语料、素材、真论文 PDF |
| `.sense` | 209 | 运行痕迹 |
| `(根目录)` | 108 | 核心模块与文档 |
| `overseas` | 80 | 海外材料 |
| `luoshen-eo` | 73 | ★ 并入的 luoshen-eo 全量（eo_core/eo_brain + archive 状态历史） |
| `core` | 46 | 核心机制层（各感官/身体/本能） |
| `fig` | 45 | 图 |
| `docs` | 34 | 文档 |
| `capabilities` | 33 | 能力清单 |
| `参数库` | 25 | 参数库 |
| `assets` | 24 | 资源 |
| `tools` | 23 | 工具 |
| `协议` | 22 | 协议 |
| `名片` | 20 | 名片 |
| `archive` | 17 |  |
| `接收` | 12 |  |
| `TACT提交` | 9 |  |
| `paper` | 8 |  |
| `deliver` | 7 |  |

## 合并说明

- `luoshen-eo/` 为原 luoshen-eo 仓库全量并入（73 项，含 eo_core/eo_brain/eo_symbiosis 等模块与 archive 状态历史）
- 保持原目录结构整体搬迁，未做筛选、未做改写——留待后续自行处理

## 安全与排除（.gitignore）

- 凭证：`.auth/`、`*token*`、`*cookie*` —— 绝不入仓
- 第三方源码副本：`扒/`（含 claude-code-main 等，61M） —— 版权，不入仓
- 实验过程截图：`_cap/`、`shots/`、`fov_s*.png`、`s?????.png` —— 中间产物
- 大体积二进制：`*.bin` `*.raw` `*.npy` `*.zip` `*.bundle` `*.mp4`

## 已知限制

- 工作区为 virtiofs 挂载且配额 500M，小文件批量 IO 极慢，`git add` 需分批（每批 ≤350 项）
- git 协议（github.com 域名 / SSH）在出口被拦截，推送统一走 REST API（`api_sync_file.py`）
- 根目录散落 108 个模块未归并，保留原位以免破坏 import
