"""Register the weekly webhook with Infrai cron."""

import os

from infrai_cron import cron_create


if __name__ == "__main__":
    task_url = os.environ["DIGEST_TASK_URL"]
    job_id = cron_create(
        cron_expr="0 8 * * 1",
        task=task_url,
        idempotency_key=os.environ.get("DIGEST_SCHEDULE_KEY", "property-weekly-digest-v1"),
    )
    print(f"scheduled job_id={job_id}")
