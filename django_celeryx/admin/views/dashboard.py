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
    config.update(
        inner_radius=0.35,
        print_values=True,
        print_values_position="center",
        value_formatter=lambda x: str(int(x)),
        legend_at_bottom_columns=2,
        margin=5,
        margin_top=20,
        margin_bottom=5,
        height=250,
        width=320,
    )
    chart = pygal.Pie(**config)
    # Build ordered lists so legend colors match pie slices
    state_colors = {
        "SUCCESS": "#417690",
        "FAILURE": "#ba2121",
        "STARTED": "#79aec8",
        "RETRY": "#e09c3f",
        "REVOKED": "#7c3aed",
        "RECEIVED": "#c4a000",
        "PENDING": "#999",
        "REJECTED": "#bbb",
    }
    # Preferred display order
    order = ["SUCCESS", "FAILURE", "STARTED", "RETRY", "REVOKED", "RECEIVED", "PENDING", "REJECTED"]
    items = [(s, state_counts[s]) for s in order if state_counts.get(s, 0) > 0]

    # Set style colors to match the ordered slices
    config["style"] = _chart_style(colors=tuple(state_colors.get(s, "#999") for s, _ in items))
    chart = pygal.Pie(**config)
    chart.title = "Task States"

    for state, count in items:
        chart.add(state, count)

    return chart.render(is_unicode=True)


def _build_throughput_chart(hourly_data: list[tuple[str, int, int]]) -> str:
    """Build a line chart of task throughput over time."""
    import pygal

    config = _common_config()
    config["style"] = _chart_style(colors=("#417690", "#ba2121"))
    config.update(
        x_label_rotation=45,
        show_dots=False,
        fill=True,
        show_minor_x_labels=False,
        x_labels_major_every=4,
        height=250,
    )
    chart = pygal.Line(**config)
    chart.title = "Throughput (last 24h)"

    labels = [row[0] for row in hourly_data]
    succeeded = [row[1] for row in hourly_data]
    failed = [row[2] for row in hourly_data]

    chart.x_labels = labels
    chart.add("Succeeded", succeeded)
    chart.add("Failed", failed)

    return chart.render(is_unicode=True)


def _build_top_tasks_bar(task_counts: list[tuple[str, int]]) -> str:
    """Build a horizontal bar chart of most common task types."""
    import pygal

    config = _common_config()
    config.update(
        show_legend=False,
        print_values=True,
        value_formatter=lambda x: str(int(x)),
        truncate_label=-1,
        margin_left=10,
        spacing=15,
        height=max(180, 50 * len(task_counts[:10])),
    )
    config["style"] = _chart_style(colors=("#417690",))
    chart = pygal.HorizontalBar(**config)
    chart.title = "Top Tasks (by count)"

    # Sort descending and take top 10, then reverse for horizontal bar (top = biggest)
    items = sorted(task_counts[:10], key=lambda x: x[1])
    labels = []
    for name, _count in items:
        parts = name.rsplit(".", 2)
        labels.append(".".join(parts[-2:]) if len(parts) > 1 else name)
    chart.x_labels = labels
    chart.add("Tasks", [{"value": c, "color": "#417690"} for _, c in items])

    return chart.render(is_unicode=True)


def _chart_style(colors: tuple[str, ...] | None = None) -> object:
    """Pygal style matching Django admin."""
    from pygal.style import Style

    if colors is None:
        colors = (
            "#417690",
            "#ba2121",
            "#79aec8",
            "#e09c3f",
            "#7c3aed",
            "#c4a000",
            "#999",
            "#14b8a6",
            "#ec4899",
            "#84cc16",
        )

    return Style(
        background="transparent",
        plot_background="transparent",
        foreground="#417690",
        foreground_strong="#205067",
        foreground_subtle="#ddd",
        opacity=".85",
        opacity_hover=".95",
        transition="200ms",
        colors=colors,
        value_colors=("#fff",),
        font_family="'Segoe UI', system-ui, Roboto, 'Helvetica Neue', Arial, sans-serif",
        title_font_size=15,
        label_font_size=12,
        major_label_font_size=12,
        value_font_size=12,
        legend_font_size=13,
        tooltip_font_size=12,
        guide_stroke_color="#eee",
        guide_stroke_dasharray="2,4",
        major_guide_stroke_color="#ddd",
        major_guide_stroke_dasharray="2,4",
    )


def _get_hourly_throughput(qs: Any) -> list[tuple[str, int, int]]:
    """Get hourly succeeded/failed counts for the last 24h from a base queryset."""
    try:
        from django.db.models import Count, Q

        now = datetime.datetime.now(tz=datetime.UTC)
        result = []

        for hours_ago in range(23, -1, -1):
            start = now - datetime.timedelta(hours=hours_ago + 1)
            end = now - datetime.timedelta(hours=hours_ago)

            agg = qs.filter(updated_at__gte=start.timestamp(), updated_at__lt=end.timestamp()).aggregate(
                succeeded=Count("id", filter=Q(state="SUCCESS")),
                failed=Count("id", filter=Q(state="FAILURE")),
            )
            result.append((end.strftime("%H:%M"), agg["succeeded"], agg["failed"]))

        return result
    except Exception:
        return []


# Time period filter choices: (param_value, label, timedelta)
_PERIOD_CHOICES = [
    ("today", "Today", datetime.timedelta(days=1)),
    ("7d", "Last 7 days", datetime.timedelta(days=7)),
    ("30d", "Last 30 days", datetime.timedelta(days=30)),
]


def _build_filter_url(request: Any, **overrides: str | None) -> str:
    """Build a URL preserving current query params but overriding specified ones."""
    from urllib.parse import urlencode

    params = dict(request.GET.items())
    for key, value in overrides.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    qs = urlencode(params)
    return f"?{qs}" if qs else "?"


def _apply_filters(request: Any, qs: Any) -> Any:
    """Apply queue, worker, and time period filters from query params."""
    if queue := request.GET.get("queue", ""):
        qs = qs.filter(routing_key=queue)
    if worker := request.GET.get("worker", ""):
        qs = qs.filter(worker=worker)
    if period := request.GET.get("period", ""):
        for value, _label, delta in _PERIOD_CHOICES:
            if period == value:
                cutoff = datetime.datetime.now(tz=datetime.UTC) - delta
                qs = qs.filter(updated_at__gte=cutoff.timestamp())
                break
    return qs


def _build_sidebar_filters(request: Any, all_qs: Any) -> list[dict[str, Any]]:
    """Build filter sidebar choices for time period, queue, and worker."""
    active_queue = request.GET.get("queue", "")
    active_worker = request.GET.get("worker", "")
    active_period = request.GET.get("period", "")

    filters: list[dict[str, Any]] = []

    # Time period
    period_items = [{"label": "All time", "url": _build_filter_url(request, period=None), "active": not active_period}]
    period_items.extend(
        {"label": label, "url": _build_filter_url(request, period=value), "active": active_period == value}
        for value, label, _delta in _PERIOD_CHOICES
    )
    filters.append({"title": "Time period", "items": period_items})

    # Queue
    queue_choices = sorted(all_qs.exclude(routing_key="").values_list("routing_key", flat=True).distinct())
    if queue_choices:
        queue_items = [{"label": "All", "url": _build_filter_url(request, queue=None), "active": not active_queue}]
        queue_items.extend(
            {"label": q, "url": _build_filter_url(request, queue=q), "active": active_queue == q} for q in queue_choices
        )
        filters.append({"title": "Queue", "items": queue_items})

    # Worker
    worker_choices = sorted(all_qs.exclude(worker="").values_list("worker", flat=True).distinct())
    if worker_choices:
        worker_items = [{"label": "All", "url": _build_filter_url(request, worker=None), "active": not active_worker}]
        worker_items.extend(
            {"label": w, "url": _build_filter_url(request, worker=w), "active": active_worker == w}
            for w in worker_choices
        )
        filters.append({"title": "Worker", "items": worker_items})

    return filters


def _compute_stats(qs: Any) -> dict[str, Any]:
    """Compute dashboard statistics from a queryset."""
    from django.db.models import Avg, Count

    state_counts: dict[str, int] = {}
    try:
        for row in qs.values("state").annotate(count=Count("id")):
            state_counts[row["state"]] = row["count"]
    except Exception:
        state_counts = {}

    avg_runtime = None
    try:
        agg = qs.filter(runtime__isnull=False).aggregate(avg=Avg("runtime"))
        if agg["avg"] is not None:
            avg_runtime = f"{agg['avg']:.3f}s"
    except Exception:
        avg_runtime = None

    top_tasks: list[tuple[str, int]] = []
    try:
        top_tasks = [
            (row["name"], row["count"])
            for row in qs.exclude(name="").values("name").annotate(count=Count("id")).order_by("-count")[:15]
        ]
    except Exception:
        top_tasks = []

    total = qs.count()
    total_succeeded = state_counts.get("SUCCESS", 0)
    total_failed = state_counts.get("FAILURE", 0)

    return {
        "total_tasks": total,
        "total_succeeded": total_succeeded,
        "total_failed": total_failed,
        "success_rate": f"{total_succeeded / total * 100:.1f}%" if total > 0 else "-",
        "avg_runtime": avg_runtime,
        "top_tasks": top_tasks,
    }


def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Render the metrics dashboard with Pygal SVG charts and sidebar filters."""
    from django_celeryx.db_models import TaskState
    from django_celeryx.settings import get_db_alias

    db = get_db_alias()
    all_qs = TaskState.objects.using(db)
    qs = _apply_filters(request, all_qs)

    filters = _build_sidebar_filters(request, all_qs)
    stats = _compute_stats(qs)

    hourly_data = _get_hourly_throughput(qs)
    throughput_svg = _build_throughput_chart(hourly_data) if hourly_data else ""
    top_tasks_svg = _build_top_tasks_bar(stats["top_tasks"]) if stats["top_tasks"] else ""

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
            **stats,
            "throughput_svg": throughput_svg,
            "top_tasks_svg": top_tasks_svg,
            "filters": filters,
        }
    )
    return render(request, "admin/django_celeryx/dashboard.html", context)
