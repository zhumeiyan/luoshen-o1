"""DashboardGrid layout component."""

from __future__ import annotations

from typing import Any

from fasthtml.common import Div

from ...core._stability import beta
from ...core.base import merge_classes
from ...core.registry import register
from ...core.theme import UNSET, resolve_defaults
from ...utils.attrs import convert_attrs


def _normalize_size(value: str | int | float) -> str:
    if isinstance(value, (int, float)):
        return f"{value}rem"
    return value


def _normalize_px(value: str | int | float) -> str:
    if isinstance(value, (int, float)):
        return f"{value}px"
    return value


@register(category="layout")
@beta
def DashboardGrid(
    *children: Any,
    cols: int | None = UNSET,
    gap: str | int | float = 1.5,
    min_card_width: str | int | float = 240,
    dense: bool = False,
    **kwargs: Any,
) -> Div:
    """Responsive dashboard grid using CSS grid."""
    cfg = resolve_defaults(
        "DashboardGrid",
        cols=cols,
        gap=gap,
        min_card_width=min_card_width,
        dense=dense,
    )
    c_cols = cfg.get("cols", cols)
    c_gap = cfg.get("gap", gap)
    c_min_card_width = cfg.get("min_card_width", min_card_width)
    c_dense = cfg.get("dense", dense)

    if c_cols is not None and c_cols < 1:
        msg = f"cols must be >= 1, got {c_cols}"
        raise ValueError(msg)

    style: dict[str, Any] = {
        "display": "grid",
        "gap": _normalize_size(c_gap),
    }

    if c_cols:
        style["grid_template_columns"] = f"repeat({c_cols}, minmax(0, 1fr))"
    else:
        style["grid_template_columns"] = (
            f"repeat(auto-fit, minmax({_normalize_px(c_min_card_width)}, 1fr))"
        )

    if c_dense:
        style["grid_auto_flow"] = "dense"

    user_style = kwargs.pop("style", None)
    if isinstance(user_style, dict):
        style.update(user_style)

    user_cls = kwargs.pop("cls", "")
    wrapper_cls = merge_classes("faststrap-dashboard-grid", user_cls)

    kwargs["style"] = style

    attrs: dict[str, Any] = {"cls": wrapper_cls}
    attrs.update(convert_attrs(kwargs))

    if isinstance(user_style, str) and user_style:
        attrs["style"] = f"{attrs.get('style', '')}; {user_style}".strip("; ")

    return Div(*children, **attrs)
