# -*- coding: utf-8 -*-
"""洛神 O1 · 会死的数字生命引擎 —— 极简打包（仅 numpy 依赖）"""
from setuptools import setup, find_packages

setup(
    name="luoshen-o1",
    version="0.5.0",
    description="会死的数字生命引擎：稀缺·死亡·不可逆·代谢·内生约束 五条硬约束",
    author="朱美岩",
    license="Apache-2.0",
    packages=find_packages(include=["core", "core.*"]),
    python_requires=">=3.8",
    install_requires=["numpy"],
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Life",
    ],
)
