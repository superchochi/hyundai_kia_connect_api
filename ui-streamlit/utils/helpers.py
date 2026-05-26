"""Formatting and display helpers."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


def fmt_val(value, unit: str = "", fallback: str = "—") -> str:
    if value is None:
        return fallback
    if isinstance(value, float) and math.isnan(value):
        return fallback
    if unit:
        return f"{value} {unit}"
    return str(value)


def fmt_bool(value, true_label: str = "Yes", false_label: str = "No", fallback: str = "—") -> str:
    if value is None:
        return fallback
    return true_label if value else false_label


def status_dot(value: bool | None, true_label: str = "", false_label: str = "") -> str:
    if value is None:
        return f"⚪ Unknown"
    if value:
        return f"🟢 {true_label}" if true_label else "🟢"
    return f"🔴 {false_label}" if false_label else "🔴"


def warning_dot(value: bool | None, warn_label: str = "Warning", ok_label: str = "OK") -> str:
    """Red when True (warning active), green when False (OK)."""
    if value is None:
        return "⚪ Unknown"
    return f"🔴 {warn_label}" if value else f"🟢 {ok_label}"


def fmt_distance(value, unit) -> str:
    if value is None:
        return "—"
    if unit:
        return f"{value:,.1f} {unit}"
    return f"{value:,.1f}"


def fmt_duration(minutes: int | None) -> str:
    if minutes is None:
        return "—"
    h, m = divmod(int(minutes), 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def fmt_speed(value, unit="km/h") -> str:
    if value is None:
        return "—"
    return f"{value} {unit}"


def fmt_energy(wh: int | float | None) -> str:
    if wh is None:
        return "—"
    if abs(wh) >= 1000:
        return f"{wh / 1000:.2f} kWh"
    return f"{wh} Wh"


def fmt_time_ago(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def fmt_datetime(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def engine_type_badge(engine_type) -> str:
    if engine_type is None:
        return "Unknown"
    labels = {
        "ICE": "⛽ ICE",
        "EV": "⚡ EV",
        "PHEV": "🔌⛽ PHEV",
        "HEV": "♻️ HEV",
    }
    name = engine_type.value if hasattr(engine_type, "value") else str(engine_type)
    return labels.get(name, name)


def lock_status(is_locked: bool | None) -> str:
    if is_locked is None:
        return "⚪ Unknown"
    return "🔒 Locked" if is_locked else "🔓 Unlocked"


def door_status(is_open: bool | None) -> str:
    if is_open is None:
        return "⚪"
    return "🟠 Open" if is_open else "🟢 Closed"


def door_lock_status(is_locked: bool | None) -> str:
    if is_locked is None:
        return "⚪"
    return "🔒" if is_locked else "🔓"


def chart_layout(**extra: Any) -> dict:
    """Base Plotly layout for in-app charts.

    Uses transparent backgrounds so charts blend into any Streamlit theme.
    Pass keyword args to override or extend (e.g. title, barmode, yaxis_title).
    """
    base: dict = {
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
    }
    base.update(extra)
    return base
