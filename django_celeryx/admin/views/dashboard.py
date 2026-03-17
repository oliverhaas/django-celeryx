"""Dashboard view — computes stats and passes JSON data for Chart.js rendering."""

from __future__ import annotations

import datetime
import json
from typing import Any


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


def compute_dashboard_context(qs: Any) -> dict[str, Any]:
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

    # Hourly throughput data
    hourly_data = _get_hourly_throughput(qs)

    # Chart.js JSON data
    chartjs_throughput = ""
    if hourly_data:
        chartjs_throughput = json.dumps(
            {
                "labels": [row[0] for row in hourly_data],
                "succeeded": [row[1] for row in hourly_data],
                "failed": [row[2] for row in hourly_data],
            }
        )

    chartjs_top_tasks = ""
    if top_tasks:
        items = sorted(top_tasks[:10], key=lambda x: x[1])
        labels = []
        for name, _ in items:
            parts = name.rsplit(".", 2)
            labels.append(".".join(parts[-2:]) if len(parts) > 1 else name)
        chartjs_top_tasks = json.dumps(
            {
                "labels": labels,
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
    }
