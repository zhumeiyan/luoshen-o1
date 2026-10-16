# -*- coding: utf-8 -*-
"""洛神 O1 · 核心包

对外只暴露一个入口：Life5（五条硬约束下的数字生命个体）。

    from core import Life5
    life = Life5(seed=3)
    life.run(600)

历史教训（判据核第 278 条）：本文件曾长期缺失，导致
setuptools.find_packages() 返回空列表，`pip install .` 装出一个不含任何
代码的空包，而 README / PDF 仍声称"可 pip 安装、具备实际部署条件"。
该文件由 tools/verify_all.py 的第 ④ 组检查项守护，删除即检出。
"""

from .life5 import Life5

__all__ = ["Life5"]
__version__ = "0.5.0"
