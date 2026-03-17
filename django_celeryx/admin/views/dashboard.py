"""Dashboard view — computes stats and passes JSON data for Chart.js rendering."""

from __future__ import annotations

import datetime
import json
from typing import Any

# Period -> (total_seconds, target_bins, label_format)
_PERIOD_CONFIG: dict[str, tuple[int, int, str]] = {
    "today": (86400, 24, "%H:%M"),
    "7d": (7 * 86400, 56, "%a %H:%M"),
    "30d": (30 * 86400, 60, "%b %d"),
}
_DEFAULT_PERIOD = ("", (86400, 24, "%H:%M"))


def _get_throughput(qs: Any, period: str) -> list[tuple[str, int, int]]:
    """Get succeeded/failed counts binned over the active time period."""
    try:
        from django.db.models import Count, Q

        total_seconds, num_bins, fmt = _PERIOD_CONFIG.get(period, _DEFAULT_PERIOD[1])
        now = datetime.datetime.now(tz=datetime.UTC)
        bin_seconds = total_seconds / num_bins
        result = []

        for i in range(num_bins):
            start = now - datetime.timedelta(seconds=(num_bins - i) * bin_seconds)
            end = now - datetime.timedelta(seconds=(num_bins - i - 1) * bin_seconds)

            agg = qs.filter(updated_at__gte=start.timestamp(), updated_at__lt=end.timestamp()).aggregate(
                succeeded=Count("id", filter=Q(state="SUCCESS")),
                failed=Count("id", filter=Q(state="FAILURE")),
            )
            result.append((end.strftime(fmt), agg["succeeded"], agg["failed"]))

        return result
    except Exception:
        return []


def _short_name(name: str) -> str:
    """Shorten a dotted task name to last 2 segments."""
    parts = name.rsplit(".", 2)
    return ".".join(parts[-2:]) if len(parts) > 1 else name


def _chart_slowest(qs: Any) -> str:
    """Compute slowest tasks JSON (avg runtime + stddev)."""
    try:
        from django.db.models import Avg, Count, StdDev

        rows = list(
            qs.exclude(name="")
            .filter(runtime__isnull=False)
            .values("name")
            .annotate(avg_rt=Avg("runtime"), std_rt=StdDev("runtime"), cnt=Count("id"))
            .filter(cnt__gte=2)
            .order_by("-avg_rt")[:10]
        )
        if not rows:
            return ""
        return json.dumps(
            {
                "labels": [_short_name(r["name"]) for r in rows],
                "avg": [round(r["avg_rt"], 3) for r in rows],
                "std": [round(r["std_rt"] or 0, 3) for r in rows],
            }
        )
    except Exception:
        return ""


def _chart_failure_rate(qs: Any) -> str:
    """Compute failure rate by task JSON."""
    try:
        from django.db.models import Count, Q

        rows = list(
            qs.exclude(name="")
            .values("name")
            .annotate(total=Count("id"), failed=Count("id", filter=Q(state="FAILURE")))
            .filter(total__gte=2)
            .order_by("-total")[:15]
        )
        rated = sorted(
            [(r["name"], r["failed"] / r["total"] * 100, r["total"]) for r in rows if r["failed"] > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:10]
        if not rated:
            return ""
        return json.dumps(
            {
                "labels": [_short_name(n) for n, _, _ in rated],
                "rates": [round(r, 1) for _, r, _ in rated],
                "counts": [f"{c} tasks" for _, _, c in rated],
            }
        )
    except Exception:
        return ""


def _chart_worker_load(qs: Any) -> str:
    """Compute tasks per worker JSON."""
    try:
        from django.db.models import Count

        rows = list(qs.exclude(worker="").values("worker").annotate(count=Count("id")).order_by("-count")[:10])
        if not rows:
            return ""
        return json.dumps(
            {
                "labels": [r["worker"].split("@")[0] if "@" in r["worker"] else r["worker"] for r in rows],
                "values": [r["count"] for r in rows],
            }
        )
    except Exception:
        return ""


def compute_dashboard_context(qs: Any, period: str = "") -> dict[str, Any]:
    """Compute all dashboard template context from a (filtered) queryset."""
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

    # Throughput
    throughput_data = _get_throughput(qs, period)
    chartjs_throughput = (
        json.dumps(
            {
                "labels": [r[0] for r in throughput_data],
                "succeeded": [r[1] for r in throughput_data],
                "failed": [r[2] for r in throughput_data],
            }
        )
        if throughput_data
        else ""
    )

    # Top tasks
    chartjs_top_tasks = ""
    if top_tasks:
        items = top_tasks[:10]
        chartjs_top_tasks = json.dumps(
            {
                "labels": [_short_name(n) for n, _ in items],
                "values": [c for _, c in items],
            }
        )

    return {
        "total_tasks": total,
        "total_succeeded": total_succeeded,
        "total_failed": total_failed,
        "success_rate": f"{total_succeeded / total * 100:.1f}%" if total > 0 else "-",
        "avg_runtime": avg_runtime,
        "chartjs_throughput": chartjs_throughput,
        "chartjs_top_tasks": chartjs_top_tasks,
        "chartjs_slowest": _chart_slowest(qs),
        "chartjs_failure_rate": _chart_failure_rate(qs),
        "chartjs_worker_load": _chart_worker_load(qs),
    }
