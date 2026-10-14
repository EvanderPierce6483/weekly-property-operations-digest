"""Typed property records and the weekly digest business decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class MaintenanceState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True)
class MaintenanceRequest:
    property_name: str
    unit: str
    summary: str
    state: MaintenanceState


@dataclass(frozen=True)
class TenantDocument:
    property_name: str
    unit: str
    document_name: str
    expires_on: date


@dataclass(frozen=True)
class InspectionReminder:
    property_name: str
    unit: str
    inspection_on: date


@dataclass(frozen=True)
class DigestRequest:
    as_of: date
    recipient: str
    maintenance: tuple[MaintenanceRequest, ...]
    documents: tuple[TenantDocument, ...]
    inspections: tuple[InspectionReminder, ...]


@dataclass(frozen=True)
class DigestEmail:
    recipient: str
    subject: str
    body: str


def build_weekly_digest(request: DigestRequest) -> DigestEmail:
    """Include open work and documents or inspections due in the next seven days."""
    horizon = request.as_of.toordinal() + 7
    open_work = [item for item in request.maintenance if item.state is MaintenanceState.OPEN]
    due_documents = [
        item for item in request.documents
        if request.as_of.toordinal() <= item.expires_on.toordinal() <= horizon
    ]
    due_inspections = [
        item for item in request.inspections
        if request.as_of.toordinal() <= item.inspection_on.toordinal() <= horizon
    ]
    lines = [
        f"Open maintenance: {len(open_work)}",
        *(f"- {item.property_name} / {item.unit}: {item.summary}" for item in open_work),
        f"Tenant documents due: {len(due_documents)}",
        *(f"- {item.property_name} / {item.unit}: {item.document_name} ({item.expires_on})" for item in due_documents),
        f"Inspections due: {len(due_inspections)}",
        *(f"- {item.property_name} / {item.unit}: {item.inspection_on}" for item in due_inspections),
    ]
    return DigestEmail(request.recipient, f"Property digest | {request.as_of}", "\n".join(lines))
