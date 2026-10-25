# 111 · 真实后端：把 provenance 从 SIMULATED 翻成 REAL

> 上一份 `eo_io_matrix.py` 里 9 条通道的 provenance 全是 `SIMULATED`。
> 接口形状对，信号是我生成的。本轮只做一件事：**把沙盒内真实可达的通道换成真的，换不了的说清为什么。**

校验码 `E7B6D6` · 哈希链头 `0e3024f3` · 8 条信号全部 REAL

---

## 一、核心原则

> **provenance 由「系统调用是否真的成功了」决定，不是由注释里写什么决定。**
> 打开失败 → `UNAVAILABLE` 并如实上报 errno，**绝不静默降级成 SIMULATED**。

这条写进 `real_backends.py` 的每个构造函数：先 `open`/`ioctl`，成功才置 `REAL`。

---

## 二、挂载结果

| 通道 | 设备 | provenance | 证据 |
|---|---|---|---|
| 视觉 | `/dev/fb0` | **REAL** | ioctl `FBIOGET_VSCREENINFO` → `1024×768×32bpp` |
| 数字触觉 | `/dev/input/event0` | **REAL** | 内核 evdev 流可读 |
| 效应器 | `/dev/uinput` | **REAL** | 内核注册 → `/dev/input/event1` |
| 本体觉 | `/proc` | **REAL** | loadavg / meminfo / clock |

内核认账的原始输出：

```
I: Bus=0003 Vendor=0001 Product=0110 Version=0001
N: Name="luoshen-eo-hid"
H: Handlers=sysrq kbd mouse0 event1
B: REL=3
```

**`Handlers` 里带 `kbd` 和 `mouse0`** —— 不是我声明它是键盘鼠标，是内核这么分类它。

---

## 三、三项验证（每项都必须能同时产生真和假）

### A · 可证伪性：三态两两可分辨

| 状态 | mean_luma | entropy | edge | dev_ratio | ink |
|---|---|---|---|---|---|
| blank（全黑） | 0.000 | 0.0000 | 0.000000 | 0.000000 | 1.0000 |
| white（全白） | 255.000 | 0.0000 | 0.000000 | 0.000000 | 0.0000 |
| content（渲染内容） | 251.417 | 0.2195 | 0.011422 | 0.018764 | 0.0188 |

```
可分 blank|white    -> mean_luma
可分 white|content  -> entropy_bits
可分 blank|content  -> mean_luma
A 通过 = True
```

### B · 内核闭环：下发 → 读回

```
静默对照 (不动)          : 读到 0 个事件   [应=0]
下发 move(+140,-70)      -> 读回 rel=2 key=0  lat=0.12ms
下发 click               -> 读回 rel=0 key=2  lat=0.06ms
下发 move(-90,+45)       -> 读回 rel=2 key=0  lat=0.06ms
B 通过 = True
```

**静默时读回 0，动作后真实读回 rel=4 / key=2。** 这是效应器→感受器在内核里的真闭环，不是我把变量传给自己。

### C · 本体觉随时间变化

```
cpu_s 0.4232 -> 0.4509 (Δ=+0.0277)
wall  ...298.015 -> ...298.644 (Δ=+0.629s)
C 通过 = True
```

### 自检回读

结果渲染上屏 → 从 `/dev/fb0` 真实采集 → OCR：

```
EO REAL BACKEND E7B6D6
A falsifiable True · B kernel loop True · C propriocept True
signals 8 REAL 8 · chain 0e3024f3 · rel 4 key 2
```

**校验码 `E7B6D6` 与运行时一致。**

---

## 四、本轮抓到的错误

### 1. `uinput_user_dev` 结构体打包错了 → `EINVAL(22)`

我按 112 字节打包。真实布局是 **1116 字节**：

```
char name[80] | struct input_id (4×__u16) | __u32 ff_effects_max
| __u32 absmax[64] | absmin[64] | absfuzz[64] | absflat[64]
```

前 8 次我怀疑的是权限、是 `dry_run`、是设备名，**没有一次怀疑结构体尺寸**。
修正后内核立即接受。

> 教训：先看 schema / 结构体定义，再试参数。试到对为止不是调试。

### 2. 判据选错特征 → 差点把真通道判成不可证伪

首版 `ok_A` 要求 `content.entropy > blank.entropy + 1.0`。实测：

```
blank entropy = 0.0000
white entropy = 0.0000     ← 熵区分不了黑屏和白屏！
content       = 0.2198     ← 白底黑字只占 2% 像素
→ A 判 False
```

**通道其实分辨了**（edge 0.000000 → 0.011422），是我拿一个会饱和的特征去判它。
改成「三态两两至少被一个特征分辨」后通过。

> **单特征饱和 ≠ 通道不可证伪。** 这是判据核 #443（返回空/饱和不等于没有）的又一次复发。

### 3. confidence 语义混淆

原代码 `conf = entropy/8` —— 把「读到了多少信息」当成了「我有多信这个读数」。
后果：白底黑字被判 `conf=0.028`，**把"内容稀疏"误读成"读数不可信"**。

已改：`conf` = 设备读数可信度（真实设备读成功 = 1.0），信息量放进 payload。

### 4. `time.times()` 在 Python 3.13 已移除 → 改 `time.process_time()`

---

## 五、边界（不扩大主张）

**仍然 SIMULATED，且不冒充真：**
深度相机 / 触觉电子皮肤 / 麦克风阵列 / 机械臂 / EEG / EMG —— 沙盒里没有这些硬件，接口形状保留，信号仍是合成的。

**`/dev/fb0` 的诚实界定：**
这是**真实设备 I/O**（真 ioctl、真 read 3,145,728 字节），但它读的是**显示输出**，不是外部场景。
它是屏幕感知，不是摄像头。provenance 标 REAL，scope 是 `display-output`。

**`content` 状态只有 1.88% 的像素偏离主色阶** —— 判别是有效的，但余量很薄。真机上要用真实场景重新标定阈值。

---

## 六、判据

新增判据核第 448–453 条：

- **#448** provenance 由系统调用结果决定，不由注释决定
- **#449** 结构体/协议尺寸错误优先于参数试错
- **#450** 单特征饱和不等于通道不可证伪，需多特征两两分辨
- **#451** confidence 语义须区分「读数可信度」与「信息量」
- **#452** 短读（short read）不等于成功
- **#453** EAGAIN 是「暂无数据」，不是故障，不得降级为 UNAVAILABLE
