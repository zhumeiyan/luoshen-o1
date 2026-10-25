---
来源: 元宝 / 读 easyAi 真实源码 251 文件 / 2026-10-15
类型: 证据
支撑: A有代码可复现
改核: 否
关键词: easyAi 零依赖 线程安全 上帝类
---

# easyAi 实测：零依赖属实，工程债四条

## 主张
是一个人的工程作品，不是社区级框架。

## 内容
29060 行 / 251 文件 / Java 8 / Apache-2.0。
零依赖属实：pom 无 dependencies 段，全部 import 为自家包。
但：synchronized 仅 1 处（且与核心计算无关），volatile/Atomic/ThreadLocal/Lock 全 0；
零测试零 CI；MatrixOperation.java 1149 行为上帝类。

## 判据
pom 依赖段 + import 外部包统计 + 并发原语 grep 计数 + 测试目录存在性。

## 缺口
未做编译验证；CUDA 路径（4 文件）与"零环境配置"叙事的张力未评估。
