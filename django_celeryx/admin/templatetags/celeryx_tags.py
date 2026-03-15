"""Template tags for django-celeryx admin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import template
from django.utils.html import format_html

from django_celeryx.types import TASK_STATE_COLORS, WORKER_STATUS_COLORS

if TYPE_CHECKING:
    from django.utils.safestring import SafeString

register = template.Library()


@register.simple_tag
def task_state_badge(state: str) -> SafeString:
    """Render a color-coded task state badge."""
    style = TASK_STATE_COLORS.get(state, "background:#f3f4f6;color:#374151;")
    return format_html(
        '<span style="{}padding:2px 8px;border-radius:4px;'
        'font-size:11px;font-weight:600;text-transform:uppercase">{}</span>',
        style,
        state or "-",
    )


@register.simple_tag
def worker_status_badge(status: str) -> SafeString:
    """Render a color-coded worker status badge."""
    style = WORKER_STATUS_COLORS.get(status, "background:#f3f4f6;color:#374151;")
    return format_html(
        '<span style="{}padding:2px 8px;border-radius:4px;'
        'font-size:11px;font-weight:600;text-transform:uppercase">{}</span>',
        style,
        status or "-",
    )


@register.simple_tag
def format_uptime(seconds: int | None) -> str:
    """Format uptime seconds as human-readable duration."""
    if seconds is None:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if hours < 24:
        return f"{hours}h {remaining_minutes}m"
    days = hours // 24
    remaining_hours = hours % 24
    return f"{days}d {remaining_hours}h"
