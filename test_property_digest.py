from datetime import date

from property_digest import (
    DigestRequest,
    InspectionReminder,
    MaintenanceRequest,
    MaintenanceState,
    TenantDocument,
    build_weekly_digest,
)


def test_digest_keeps_open_work_and_only_next_seven_days() -> None:
    request = DigestRequest(
        as_of=date(2026, 9, 14),
        recipient="manager@example.com",
        maintenance=(
            MaintenanceRequest("Maple Court", "2A", "Leaking tap", MaintenanceState.OPEN),
            MaintenanceRequest("Maple Court", "3B", "Replace lock", MaintenanceState.CLOSED),
        ),
        documents=(
            TenantDocument("Maple Court", "2A", "Insurance certificate", date(2026, 9, 18)),
            TenantDocument("Oak House", "1C", "Lease", date(2026, 9, 30)),
        ),
        inspections=(InspectionReminder("Oak House", "1C", date(2026, 9, 21)),),
    )

    email = build_weekly_digest(request)

    assert "Leaking tap" in email.body
    assert "Replace lock" not in email.body
    assert "Insurance certificate" in email.body
    assert "Lease" not in email.body
    assert "2026-09-21" in email.body
