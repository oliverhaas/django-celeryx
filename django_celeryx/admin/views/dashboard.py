"""Dashboard view with Pygal charts for task metrics."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.shortcuts import render

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def _common_config() -> dict[str, Any]:
    """Common Pygal chart configuration."""
    return {
        "style": _chart_style(),
        "disable_xml_declaration": True,
        "explicit_size": False,
        "show_x_guides": False,
        "show_y_guides": True,
        "margin": 20,
        "legend_at_bottom": True,
        "legend_at_bottom_columns": 4,
        "tooltip_border_radius": 4,
        "no_prefix": True,
    }


def _build_state_pie(state_counts: dict[str, int]) -> str:
    """Build a pie chart of task states."""
    import pygal

    config = _common_config()
    config.update(inner_radius=0.4, print_values=True, value_formatter=lambda x: str(int(x)))
    chart = pygal.Pie(**config)
    chart.title = "Task States"

    colors = {
        "SUCCESS": "#22c55e",
        "FAILURE": "#ef4444",
        "STARTED": "#3b82f6",
        "RETRY": "#f97316",
        "REVOKED": "#8b5cf6",
        "RECEIVED": "#eab308",
        "PENDING": "#6b7280",
        "REJECTED": "#9ca3af",
    }

    for state, count in sorted(state_counts.items()):
        if count > 0:
            chart.add(state, [{"value": count, "color": colors.get(state, "#6b7280")}])

    return chart.render(is_unicode=True)


def _build_throughput_chart(hourly_data: list[tuple[str, int, int]]) -> str:
    """Build a line chart of task throughput over time."""
    import pygal

    config = _common_config()
    config.update(
        x_label_rotation=45,
        show_dots=False,
        fill=True,
        show_minor_x_labels=False,
        x_labels_major_every=4,
    )
    chart = pygal.Line(**config)
    chart.title = "Throughput (last 24h)"

    labels = [row[0] for row in hourly_data]
    succeeded = [row[1] for row in hourly_data]
    failed = [row[2] for row in hourly_data]

    chart.x_labels = labels
    chart.add("Succeeded", succeeded, color="#22c55e")
    chart.add("Failed", failed, color="#ef4444")

    return chart.render(is_unicode=True)


def _build_top_tasks_bar(task_counts: list[tuple[str, int]]) -> str:
    """Build a horizontal bar chart of most common task types."""
    import pygal

    config = _common_config()
    config.update(
        show_legend=False,
        print_values=True,
        value_formatter=lambda x: str(int(x)),
    )
    chart = pygal.HorizontalBar(**config)
    chart.title = "Top Tasks (by count)"

    for name, count in task_counts[:15]:
        short_name = name.rsplit(".", 1)[-1] if "." in name else name
        chart.add(short_name, count)

    return chart.render(is_unicode=True)


def _chart_style() -> object:
    """Pygal style matching Django admin."""
    from pygal.style import Style

    return Style(
        background="transparent",
        plot_background="transparent",
        foreground="#417690",
        foreground_strong="#205067",
        foreground_subtle="#ddd",
        opacity=".8",
        opacity_hover=".9",
        transition="200ms",
        colors=(
            "#22c55e",
            "#ef4444",
            "#3b82f6",
            "#f97316",
            "#8b5cf6",
            "#eab308",
            "#6b7280",
            "#14b8a6",
            "#ec4899",
            "#84cc16",
        ),
        value_colors=("#417690",),
        font_family="'Segoe UI', system-ui, Roboto, 'Helvetica Neue', Arial, sans-serif",
        title_font_size=14,
        label_font_size=11,
        major_label_font_size=11,
        value_font_size=11,
        legend_font_size=12,
        tooltip_font_size=12,
        guide_stroke_color="#e0e0e0",
        major_guide_stroke_color="#ccc",
    )


def _get_hourly_throughput() -> list[tuple[str, int, int]]:
    """Get hourly succeeded/failed counts for the last 24h."""
    try:
        from django.db.models import Count, Q

        from django_celeryx.db_models import TaskState
        from django_celeryx.settings import get_db_alias

        db = get_db_alias()
        now = datetime.datetime.now(tz=datetime.UTC)
        result = []

        for hours_ago in range(23, -1, -1):
            start = now - datetime.timedelta(hours=hours_ago + 1)
            end = now - datetime.timedelta(hours=hours_ago)
            start_ts = start.timestamp()
            end_ts = end.timestamp()

            agg = (
                TaskState.objects.using(db)
                .filter(
                    updated_at__gte=start_ts,
                    updated_at__lt=end_ts,
                )
                .aggregate(
                    succeeded=Count("id", filter=Q(state="SUCCESS")),
                    failed=Count("id", filter=Q(state="FAILURE")),
                )
            )
            label = end.strftime("%H:%M")
            result.append((label, agg["succeeded"], agg["failed"]))

        return result
    except Exception:
        return []


def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Render the metrics dashboard with Pygal SVG charts."""
    from django.db.models import Avg, Count

    from django_celeryx.db_models import TaskState
    from django_celeryx.settings import get_db_alias

    db = get_db_alias()

    # State counts
    state_counts: dict[str, int] = {}
    try:
        for row in TaskState.objects.using(db).values("state").annotate(count=Count("id")):
            state_counts[row["state"]] = row["count"]
    except Exception:
        state_counts = {}

    # Average runtime
    avg_runtime = None
    try:
        agg = TaskState.objects.using(db).filter(runtime__isnull=False).aggregate(avg=Avg("runtime"))
        if agg["avg"] is not None:
            avg_runtime = f"{agg['avg']:.3f}s"
    except Exception:
        avg_runtime = None

    # Top tasks by count
    top_tasks: list[tuple[str, int]] = []
    try:
        top_tasks = [
            (row["name"], row["count"])
            for row in TaskState.objects.using(db)
            .exclude(name="")
            .values("name")
            .annotate(count=Count("id"))
            .order_by("-count")[:15]
        ]
    except Exception:
        top_tasks = []

    # Total counts
    total = TaskState.objects.using(db).count()
    total_succeeded = state_counts.get("SUCCESS", 0)
    total_failed = state_counts.get("FAILURE", 0)
    success_rate = f"{total_succeeded / total * 100:.1f}%" if total > 0 else "-"

    # Build charts
    state_pie_svg = _build_state_pie(state_counts) if state_counts else ""
    hourly_data = _get_hourly_throughput()
    throughput_svg = _build_throughput_chart(hourly_data) if hourly_data else ""
    top_tasks_svg = _build_top_tasks_bar(top_tasks) if top_tasks else ""

    context = admin.site.each_context(request)
    context.update(
        {
            "title": "Dashboard",
            "opts": {
                "app_label": "django_celeryx",
                "model_name": "task",
                "verbose_name_plural": "Tasks",
                "app_config": type("", (), {"verbose_name": "django-celeryx"})(),
            },
            "total_tasks": total,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "success_rate": success_rate,
            "avg_runtime": avg_runtime,
            "state_pie_svg": state_pie_svg,
            "throughput_svg": throughput_svg,
            "top_tasks_svg": top_tasks_svg,
        }
    )
    return render(request, "admin/django_celeryx/dashboard.html", context)
