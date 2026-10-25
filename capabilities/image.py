"""图片生成层。

诚实定位
--------
这是**渲染**，不是扩散模型。它能稳定产出的是：数据图、示意图、排版图、
信息图。它不能产出"一张照片"或"一个虚构场景的插画"。

这条边界必须写死在代码里而不是文档里——因为文档可以吹，代码不能。
`spec` 里如果出现了渲染层兑现不了的请求类型，这里直接拒绝并说明，
而不是返回一张"看起来像那么回事"的图。
"""
from __future__ import annotations

import os

from .artifact import Artifact, Kind

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


class UnsupportedImageRequest(ValueError):
    """渲染层兑现不了的请求。宁可拒绝，不许糊弄。"""


#: 渲染层真正能兑现的类型。超出这个集合的请求拒绝，不静默降级。
SUPPORTED = {"chart", "diagram", "infographic", "layout"}

#: 这些是渲染层做不到的，遇到要明确说出来由别的引擎接，
#: 而不是出一张"差不多"的图交差。
OUT_OF_SCOPE = {
    "photo", "photorealistic", "illustration", "portrait",
    "anime", "painting", "3d_render", "product_shot",
}


def render(spec: dict, out_dir: str = DEFAULT_OUT) -> Artifact:
    """按 spec 渲染一张 PNG。

    spec 最小字段：`kind`（在 SUPPORTED 内）、`title`、以及该 kind 的数据字段。
    返回 Artifact；合不合格由 verify.image() 判定，本函数不做判定。
    """
    kind = str(spec.get("kind", "chart")).lower()
    if kind in OUT_OF_SCOPE:
        raise UnsupportedImageRequest(
            f"渲染层做不出 {kind!r}。这是渲染不是扩散模型 —— "
            f"能做的：{sorted(SUPPORTED)}")
    if kind not in SUPPORTED:
        raise UnsupportedImageRequest(
            f"未知图片类型 {kind!r}，支持：{sorted(SUPPORTED)}")

    os.makedirs(out_dir, exist_ok=True)
    name = spec.get("name") or f"img_{abs(hash(str(sorted(spec.items())))) % 10**8}"
    path = os.path.join(out_dir, f"{name}.png")

    if kind == "chart":
        _render_chart(spec, path)
    elif kind == "diagram":
        _render_diagram(spec, path)
    elif kind == "infographic":
        _render_infographic(spec, path)
    else:                                   # layout
        _render_layout(spec, path)

    return Artifact(kind=Kind.IMAGE, path=path, meta=dict(spec))


# ---------------------------------------------------------------------------
def _style(spec: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return plt


def _render_chart(spec: dict, path: str) -> None:
    plt = _style(spec)
    series = spec.get("series") or []
    fig, ax = plt.subplots(figsize=spec.get("figsize", (8, 4.5)), dpi=spec.get("dpi", 150))
    for s in series:
        ax.plot(s.get("x") or list(range(len(s["y"]))), s["y"],
                marker=s.get("marker", "o"), label=s.get("label", ""),
                linewidth=s.get("lw", 2),
                color=s.get("color"), linestyle=s.get("ls", "-"))
    ax.set_title(spec.get("title", ""), fontsize=spec.get("title_size", 14))
    ax.set_xlabel(spec.get("xlabel", ""))
    ax.set_ylabel(spec.get("ylabel", ""))
    if any(s.get("label") for s in series):
        ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _render_diagram(spec: dict, path: str) -> None:
    """节点-边示意图。用于画关系、流程、结构。"""
    plt = _style(spec)
    nodes = spec.get("nodes") or []
    edges = spec.get("edges") or []
    pos = {n["id"]: tuple(n.get("pos", (i, 0))) for i, n in enumerate(nodes)}
    fig, ax = plt.subplots(figsize=spec.get("figsize", (8, 4.5)), dpi=150)
    for e in edges:
        a, b = pos.get(e[0]), pos.get(e[1])
        if a is None or b is None:
            continue
        ax.annotate("", xy=b, xytext=a,
                    arrowprops=dict(arrowstyle="->", lw=1.6,
                                    color="#555", shrinkA=18, shrinkB=18))
        if len(e) > 2 and e[2]:
            ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, str(e[2]),
                    fontsize=9, color="#333", ha="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
    for n in nodes:
        x, y = pos[n["id"]]
        ax.scatter([x], [y], s=1400, c=n.get("color", "#4C78A8"), zorder=3)
        ax.text(x, y, n.get("label", n["id"]), ha="center", va="center",
                fontsize=n.get("size", 10), color="white", zorder=4)
    ax.set_title(spec.get("title", ""), fontsize=13)
    ax.set_axis_off()
    ax.autoscale_view()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _render_infographic(spec: dict, path: str) -> None:
    """数字条 + 要点信息图。"""
    plt = _style(spec)
    stats = spec.get("stats") or []
    bullets = spec.get("bullets") or []
    fig = plt.figure(figsize=spec.get("figsize", (9, 5)), dpi=150)
    fig.suptitle(spec.get("title", ""), fontsize=15, y=0.96)

    n = max(1, len(stats))
    for i, s in enumerate(stats):
        ax = fig.add_subplot(1, n, i + 1)
        ax.text(0.5, 0.62, str(s.get("value", "")), ha="center", va="center",
                fontsize=34, fontweight="bold", color=s.get("color", "#222"),
                transform=ax.transAxes)
        ax.text(0.5, 0.26, str(s.get("label", "")), ha="center", va="center",
                fontsize=11, color="#555", transform=ax.transAxes)
        ax.set_axis_off()

    if bullets:
        ax = fig.add_axes([0.08, 0.06, 0.84, 0.16])
        ax.text(0, 1, "\n".join("• " + b for b in bullets),
                va="top", fontsize=10, color="#333")
        ax.set_axis_off()
    fig.savefig(path)
    plt.close(fig)


def _render_layout(spec: dict, path: str) -> None:
    """纯排版图：标题 + 正文块。用于封面、卡片。"""
    plt = _style(spec)
    fig = plt.figure(figsize=spec.get("figsize", (8, 4.5)), dpi=150)
    fig.patch.set_facecolor(spec.get("bg", "white"))
    fig.text(0.5, 0.72, spec.get("title", ""), ha="center", fontsize=22,
             fontweight="bold", color=spec.get("fg", "#111"))
    fig.text(0.5, 0.48, spec.get("subtitle", ""), ha="center", fontsize=12,
             color="#666")
    body = spec.get("body") or []
    for i, line in enumerate(body):
        fig.text(0.5, 0.34 - i * 0.07, line, ha="center", fontsize=11, color="#444")
    fig.savefig(path)
    plt.close(fig)
