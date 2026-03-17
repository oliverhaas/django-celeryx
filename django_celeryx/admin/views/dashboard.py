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

    # Throughput binned data
    throughput_data = _get_throughput(qs, period)

    # Chart.js JSON
    chartjs_throughput = ""
    if throughput_data:
        chartjs_throughput = json.dumps(
            {
                "labels": [row[0] for row in throughput_data],
                "succeeded": [row[1] for row in throughput_data],
                "failed": [row[2] for row in throughput_data],
            }
        )

    chartjs_top_tasks = ""
    if top_tasks:
        # Reverse so biggest is at top in horizontal bar chart
        items = list(reversed(top_tasks[:10]))
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
