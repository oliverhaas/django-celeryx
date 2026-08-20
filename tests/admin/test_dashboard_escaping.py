"""The dashboard embeds task and worker names in a JSON <script> block.

Those names come from the Celery cluster, so they are attacker-controlled if
anyone can register a task. The json_script filter escapes <, > and & so a name
cannot close the script tag.
"""

import re
import time

import pytest
from django.urls import reverse

from django_celeryx.db_models import TaskState, WorkerState

PAYLOAD = "</script><script>alert(1)</script>"


@pytest.mark.django_db
class TestDashboardEscaping:
    def test_task_name_cannot_close_the_script_tag(self, admin_client):
        now = time.time()
        for i in range(3):
            TaskState.objects.create(
                uuid=f"xss-{i}",
                name=PAYLOAD,
                state="SUCCESS",
                runtime=1.0,
                worker="w1@host",
                updated_at=now,
            )

        content = admin_client.get(reverse("admin:django_celeryx_dashboard_changelist")).content.decode()

        block = re.search(r'<script id="cx-data" type="application/json">(.*?)</script>', content, re.DOTALL)
        assert block is not None, "dashboard did not render the cx-data JSON block"
        assert PAYLOAD not in block.group(1)
        assert "\\u003C" in block.group(1)
        assert "<script>alert(1)</script>" not in content

    def test_worker_hostname_cannot_close_the_script_tag(self, admin_client):
        now = time.time()
        WorkerState.objects.create(hostname=PAYLOAD, status="online", updated_at=now)
        TaskState.objects.create(
            uuid="xss-w",
            name="proj.add",
            state="SUCCESS",
            worker=PAYLOAD,
            runtime=1.0,
            updated_at=now,
        )

        content = admin_client.get(reverse("admin:django_celeryx_dashboard_changelist")).content.decode()

        assert "<script>alert(1)</script>" not in content
