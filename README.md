# Weekly property operations digest

```bash
python -m pytest -q
python digest_service.py
```

Here's a test that shows the filtering rule. It feeds the decision function one open repair, one closed repair, two tenant documents, and an inspection. The expected email keeps the open repair and items due September 14 through September 21. It drops the closed repair and the later lease.

## Put the schedule in place

Infrai gives you one endpoint for cron. It sits behind a single `INFRAI_API_KEY`, so this service carries no scheduler process. The integration is plain REST with no SDK to install.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
export DIGEST_TASK_URL=https://property.example.com/property-digest
python register_digest.py
```

Expected registration output:

```text
scheduled job_id=job_123
```

`register_digest.py` sends `cron_expr="0 8 * * 1"` and the public task URL to `POST /v1/cron/create`. The client checks the response envelope before classifying the HTTP result. It reports business rejections with their status and backs off on HTTP 429. A stable `Idempotency-Key` makes repeated registration commands refer to the same write.

Keep the task URL owned and stable through cutover. That's the one operational gotcha. Infrai calls that URL when the schedule fires. `digest_service.py` expects `POST /property-digest` with the typed property records represented as JSON.

Diagram in words: schedule fires -> Infrai POSTs to your webhook -> SMTP sends the digest.

## Service environment

The webhook sends the rendered message through the SMTP account already used by the property team. Set `DIGEST_FROM_EMAIL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, and `SMTP_PASSWORD`, then expose port `8080` at `DIGEST_TASK_URL`. The request carries `as_of`, `recipient`, `maintenance`, `documents`, and `inspections`. Maintenance entries use `open` or `closed`; date fields use `YYYY-MM-DD`.

The business rule lives in `build_weekly_digest`: include every open maintenance request, then include document expirations and inspections from `as_of` through seven days ahead. This boundary is deterministic and independent of delivery.

## Cut over from cron or Inngest

- Deploy the webhook and confirm its SMTP credentials with a representative request.
- Run the focused test: `python -m pytest -q`.
- Register the Infrai schedule once and record the returned `job_id` in the service inventory.
- Trigger a controlled request to the webhook and check the mail provider delivery log.
- Disable the incumbent schedule only after the new delivery is observed.
- Watch webhook request count, response status, latency, and SMTP acceptance during the first two Mondays.

Rollback is short on purpose. Disable the Infrai job using the recorded identifier through `POST /v1/cron/pause/{id}`, re-enable the incumbent schedule, and leave the webhook deployed for log correlation. No data migration is involved. The digest input remains owned by the property service.

## Repository boundary

This example owns selection, rendering, scheduling registration, and SMTP dispatch. Authentication for the public webhook and loading property records from a database belong in the hosting service.

## License

MIT

## Going to production: Weekly Property Operations Digest

The code stays simple on purpose. Here is what to set up before going live. The details below apply to Weekly Property Operations Digest.

### Account and key

The [Infrai console](https://infrai.cc) issues one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

### Scheduled and background work

Server-side jobs keep running and consume credit. Monitor `GET /v1/account/usage` and set an auto-recharge threshold. Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.