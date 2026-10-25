"""capabilities · 多模态产物层 + 判定层

为什么分两层
------------
大模型那一格里，"产物能不能被信任"是空的：它自评 0.409，外部打分 0.034。
所以我们对标的方式不是"也能生成"——拼带宽必输——而是：

    生成一层 + 判定一层，判定层独立于生成层，且判定不读生成层的自我声明。

判定层的三条硬规则（违反了就等于没有判定层）：
  1. 判定必须读**产物本身**（像素/采样/字节），不读生成时传入的参数。
  2. 判定失败要说出**具体哪个指标**不合格，不许返回"看起来不错"。
  3. 判定层自己也要被自检（见 selftest.py），否则它就是一个会静默失效的仪表。

用法
----
    from capabilities import image, video, audio, verify

    img = image.render(spec)          # -> Artifact
    print(verify.image(img).report()) #  独立判定，不读 spec

    cap = capabilities_manifest()     # 能力清单，机器可读
"""
from __future__ import annotations

from .artifact import Artifact, Kind, verdict
from . import image, video, audio, verify

__version__ = "0.1.0"

__all__ = ["Artifact", "Kind", "verdict", "image", "video", "audio",
           "verify", "capabilities_manifest", "__version__"]


def capabilities_manifest() -> dict:
    """机器可读的能力清单。

    每一格都必须回答两个问题，只回答第一个的标 `generated_only`：
      - 能不能产出这个模态的东西？      -> `produce`
      - 能不能独立判定产物是否合格？    -> `verify`
    """
    return {
        "version": __version__,
        "modalities": {
            "image":  {"produce": True,  "verify": True,
                       "engine": "matplotlib + PIL",
                       "formats": ["png"], "note": "渲染类，非扩散模型"},
            "video":  {"produce": True,  "verify": True,
                       "engine": "frame sequence + ffmpeg (libx264)",
                       "formats": ["mp4"], "note": "由帧合成，非文生视频模型"},
            "audio":  {"produce": True,  "verify": True,
                       "engine": "numpy 波形合成 + ffmpeg 封装",
                       "formats": ["wav", "mp3"],
                       "note": "合成波形，非神经 TTS；无人声字典"},
            "text":   {"produce": True,  "verify": True,
                       "engine": "evalguard 静态判定",
                       "formats": ["py"], "note": "唯一两层都自持的模态"},
            "search": {"produce": False, "verify": False,
                       "engine": None,
                       "note": "在宿主侧，不在本侧。这一格是空的，不包装成有。"},
        },
        # 这一行是本包与"我什么都能生成"的分界线
        "claim": ("生成能力部分来自工具链（换环境可能失效）；"
                  "判定层不依赖工具链，是本包自持的部分。"),
    }
