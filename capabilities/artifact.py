"""Artifact — 所有模态产物的统一容器。

为什么要统一容器
----------------
如果不统一，每个模态各有各的返回类型，调用方就要为每个模态写一套
"文件在哪 / 成功了没 / 怎么判定"。而判定层要能跨模态复用，就必须先有
一个所有模态都遵守的形状。

设计上刻意做了两件事：

1. **产物与判定分离。** `Artifact` 只描述"产出了什么"，完全不知道自己
   合不合格。判定是 `verify` 模块对产物做的事，不是产物自带的属性。
   这样"生成层自己给自己发合格证"这条路被堵死了。

2. **`meta` 是生成时的输入，`probed` 是判定读出来的事实。** 两者分开存。
   判定层只读后者。这条是判定层能成立的前提。
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any


class Kind:
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"


@dataclass
class Verdict:
    """一次判定的结果。

    `ok` 是给 CI 用的布尔；`metrics` 是给人用的证据。两者缺一不可：
    只有布尔，失败时无法定位；只有指标，无法当判据用。
    """
    kind: str
    ok: bool
    metrics: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)

    def report(self) -> str:
        head = f"[{self.kind}] {'OK' if self.ok else 'FAIL'}"
        ms = "  ".join(f"{k}={v}" for k, v in self.metrics.items())
        out = [f"{head}  {ms}"]
        out += [f"    - {r}" for r in self.reasons]
        return "\n".join(out)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "ok": self.ok,
                "metrics": self.metrics, "reasons": self.reasons}


@dataclass
class Artifact:
    """一个已落盘的产物。"""
    kind: str
    path: str
    #: 生成时的输入记录。判定层**不许**读这个字段。
    meta: dict = field(default_factory=dict)
    #: 判定层读出来的事实，由 verify 模块回填。
    probed: dict = field(default_factory=dict)

    @property
    def exists(self) -> bool:
        return os.path.exists(self.path)

    @property
    def size(self) -> int:
        return os.path.getsize(self.path) if self.exists else 0

    @property
    def sha256(self) -> str:
        if not self.exists:
            return ""
        h = hashlib.sha256()
        with open(self.path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()

    @property
    def ext(self) -> str:
        return os.path.splitext(self.path)[1].lstrip(".").lower()

    def to_dict(self) -> dict:
        return {"kind": self.kind, "path": self.path, "exists": self.exists,
                "size": self.size, "sha256": self.sha256[:16],
                "ext": self.ext, "meta": self.meta, "probed": self.probed}


def verdict(kind: str, ok: bool, metrics: dict | None = None,
            reasons: list | None = None) -> Verdict:
    return Verdict(kind=kind, ok=bool(ok), metrics=metrics or {},
                   reasons=list(reasons or []))
