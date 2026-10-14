"""Executable webhook that builds and sends the property digest."""

from __future__ import annotations

import json
import os
import smtplib
from datetime import date
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from property_digest import (
    DigestRequest,
    InspectionReminder,
    MaintenanceRequest,
    MaintenanceState,
    TenantDocument,
    build_weekly_digest,
)


def parse_request(raw: dict[str, Any]) -> DigestRequest:
    return DigestRequest(
        as_of=date.fromisoformat(raw["as_of"]),
        recipient=str(raw["recipient"]),
        maintenance=tuple(
            MaintenanceRequest(item["property_name"], item["unit"], item["summary"], MaintenanceState(item["state"]))
            for item in raw.get("maintenance", [])
        ),
        documents=tuple(
            TenantDocument(item["property_name"], item["unit"], item["document_name"], date.fromisoformat(item["expires_on"]))
            for item in raw.get("documents", [])
        ),
        inspections=tuple(
            InspectionReminder(item["property_name"], item["unit"], date.fromisoformat(item["inspection_on"]))
            for item in raw.get("inspections", [])
        ),
    )


def send_email(recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = os.environ["DIGEST_FROM_EMAIL"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=30) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


class DigestHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/property-digest":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        request = parse_request(json.loads(self.rfile.read(length)))
        email = build_weekly_digest(request)
        send_email(email.recipient, email.subject, email.body)
        result = json.dumps({"sent": True, "recipient": email.recipient}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), DigestHandler).serve_forever()
