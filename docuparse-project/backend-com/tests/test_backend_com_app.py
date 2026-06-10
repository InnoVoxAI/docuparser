from __future__ import annotations

import base64
from email.message import EmailMessage

from fastapi.testclient import TestClient

from backend_com.api.app import app
from docuparse_events import LocalJsonlEventBus
from docuparse_storage import LocalStorage
from events import validate_event


def test_health_and_ready() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "healthy", "service": "docuparse-backend-com"}
    assert client.get("/ready").json() == {"status": "ready", "service": "docuparse-backend-com"}


def test_manual_upload_stores_document_and_publishes_document_received(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DOCUPARSE_LOCAL_STORAGE_DIR", str(tmp_path / "objects"))
    monkeypatch.setenv("DOCUPARSE_LOCAL_EVENT_DIR", str(tmp_path / "events"))
    from backend_com import config
    from backend_com.services import document_ingest

    config.settings.local_storage_dir = tmp_path / "objects"
    config.settings.local_event_dir = tmp_path / "events"
    config.settings.backend_core_document_received_url = ""
    document_ingest.settings.local_storage_dir = tmp_path / "objects"
    document_ingest.settings.local_event_dir = tmp_path / "events"
    document_ingest.settings.backend_core_document_received_url = ""
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/manual",
        data={
            "tenant_id": "tenant-demo",
            "sender": "operator@example.test",
            "metadata_json": '{"source":"unit-test"}',
        },
        files={"file": ("fixture.pdf", b"%PDF fake", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["event_type"] == "document.received"
    assert body["core_sync_status"] == "disabled"
    assert LocalStorage(tmp_path / "objects").get_bytes(body["file_uri"]) == b"%PDF fake"

    events = LocalJsonlEventBus(tmp_path / "events").consume("document.received")
    assert len(events) == 1
    validated = validate_event(events[0])
    assert validated.event_type == "document.received"
    assert events[0]["data"]["file"]["uri"] == body["file_uri"]


def test_manual_upload_rejects_unsupported_mime() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/manual",
        files={"file": ("fixture.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert "unsupported content_type" in response.json()["detail"]


def test_manual_upload_requires_internal_token_when_configured(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    from backend_com import config
    from backend_com.api import app as app_module

    config.settings.internal_service_token = "secret"
    app_module.settings.internal_service_token = "secret"
    client = TestClient(app)

    rejected = client.post(
        "/api/v1/documents/manual",
        files={"file": ("fixture.pdf", b"%PDF fake", "application/pdf")},
    )
    accepted = client.post(
        "/api/v1/documents/manual",
        headers={"Authorization": "Bearer secret"},
        files={"file": ("fixture.pdf", b"%PDF fake", "application/pdf")},
    )

    config.settings.internal_service_token = ""
    app_module.settings.internal_service_token = ""
    assert rejected.status_code == 401
    assert accepted.status_code == 200


def test_manual_upload_reports_failed_core_sync_without_failing_upload(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    from backend_com import config
    from backend_com.services import document_ingest

    config.settings.backend_core_document_received_url = "http://127.0.0.1:1/api/ocr/events/document-received"
    document_ingest.settings.backend_core_document_received_url = "http://127.0.0.1:1/api/ocr/events/document-received"
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/manual",
        files={"file": ("fixture.pdf", b"%PDF fake", "application/pdf")},
    )

    config.settings.backend_core_document_received_url = ""
    document_ingest.settings.backend_core_document_received_url = ""
    assert response.status_code == 200
    assert response.json()["core_sync_status"] == "failed"


def test_email_webhook_with_zero_attachments_generates_no_events(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/email/webhook",
        data={"tenant_id": "tenant-demo", "message_id": "msg-0"},
    )

    assert response.status_code == 200
    assert response.json() == {"accepted_count": 0, "documents": []}
    assert LocalJsonlEventBus(tmp_path / "events").consume("document.received") == []


def test_email_webhook_with_multiple_attachments_generates_one_event_per_attachment(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/email/webhook",
        data={
            "tenant_id": "tenant-demo",
            "sender": "sender@example.test",
            "message_id": "msg-1",
            "subject": "Documentos",
        },
        files=[
            ("attachments", ("a.pdf", b"%PDF a", "application/pdf")),
            ("attachments", ("b.png", b"PNG", "image/png")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_count"] == 2
    events = LocalJsonlEventBus(tmp_path / "events").consume("document.received")
    assert len(events) == 2
    assert {event["data"]["file"]["filename"] for event in events} == {"a.pdf", "b.png"}
    assert all(event["data"]["channel"] == "email" for event in events)
    assert all(validate_event(event).event_type == "document.received" for event in events)


def test_email_messages_rejects_invalid_attachment(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/email/messages",
        files=[("attachments", ("bad.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 400
    assert "unsupported content_type" in response.json()["detail"]


def test_email_webhook_signature_when_configured(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    from backend_com import config
    from backend_com.api import app as app_module

    config.settings.email_webhook_token = "secret"
    app_module.settings.email_webhook_token = "secret"
    client = TestClient(app)

    invalid = client.post(
        "/api/v1/email/webhook",
        files=[("attachments", ("a.pdf", b"%PDF a", "application/pdf"))],
    )
    valid = client.post(
        "/api/v1/email/webhook",
        headers={"x-docuparse-signature": "secret"},
        files=[("attachments", ("a.pdf", b"%PDF a", "application/pdf"))],
    )

    config.settings.email_webhook_token = ""
    app_module.settings.email_webhook_token = ""
    assert invalid.status_code == 401
    assert valid.status_code == 200


def test_imap_poll_ingests_accepted_attachments(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    from backend_com.services.imap_polling import email_settings_from_payload, poll_imap_once

    result = poll_imap_once(
        email_settings=email_settings_from_payload(
            {
                "provider": "imap",
                "inbox_folder": "INBOX",
                "imap_host": "imap.example.test",
                "imap_port": 993,
                "username": "docs@example.test",
                "accepted_content_types": "application/pdf,image/png",
                "max_attachment_mb": 20,
                "blocked_senders": "",
                "is_active": True,
            }
        ),
        password="app-password",
        client_factory=lambda host, port: FakeImapClient([
            _email_with_attachment(
                sender="sender@example.test",
                subject="Documentos",
                filename="invoice.pdf",
                content=b"%PDF imap",
                content_type="application/pdf",
            )
        ]),
    )

    assert result["status"] == "ok"
    assert result["processed_messages"] == 1
    assert result["accepted_count"] == 1
    events = LocalJsonlEventBus(tmp_path / "events").consume("document.received")
    assert len(events) == 1
    assert events[0]["data"]["channel"] == "email"
    assert events[0]["data"]["sender"] == "sender@example.test"
    assert events[0]["data"]["file"]["filename"] == "invoice.pdf"


def test_imap_poll_skips_blocked_sender_and_invalid_mime(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    from backend_com.services.imap_polling import email_settings_from_payload, poll_imap_once

    result = poll_imap_once(
        email_settings=email_settings_from_payload(
            {
                "provider": "imap",
                "inbox_folder": "INBOX",
                "imap_host": "imap.example.test",
                "imap_port": 993,
                "username": "docs@example.test",
                "accepted_content_types": "application/pdf",
                "max_attachment_mb": 20,
                "blocked_senders": "blocked@example.test",
                "is_active": True,
            }
        ),
        password="app-password",
        client_factory=lambda host, port: FakeImapClient([
            _email_with_attachment(
                sender="blocked@example.test",
                subject="blocked",
                filename="invoice.pdf",
                content=b"%PDF blocked",
                content_type="application/pdf",
            ),
            _email_with_attachment(
                sender="sender@example.test",
                subject="bad mime",
                filename="notes.txt",
                content=b"hello",
                content_type="text/plain",
            ),
        ]),
    )

    assert result["status"] == "ok"
    assert result["processed_messages"] == 1
    assert result["accepted_count"] == 0
    assert result["skipped_attachments"] == 1
    assert LocalJsonlEventBus(tmp_path / "events").consume("document.received") == []


def test_imap_poll_requires_password() -> None:
    from backend_com.services.imap_polling import email_settings_from_payload, poll_imap_once

    try:
        poll_imap_once(
            email_settings=email_settings_from_payload(
                {
                    "provider": "imap",
                    "inbox_folder": "INBOX",
                    "imap_host": "imap.example.test",
                    "imap_port": 993,
                    "username": "docs@example.test",
                    "is_active": True,
                }
            ),
            password="",
            client_factory=lambda host, port: FakeImapClient([]),
        )
    except ValueError as exc:
        assert "DOCUPARSE_IMAP_PASSWORD" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_whatsapp_webhook_with_zero_media_generates_no_events(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "MessageSid": "SM123",
            "From": "whatsapp:+5511999999999",
            "NumMedia": "0",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"accepted_count": 0, "documents": []}


def test_whatsapp_webhook_with_multiple_inline_media_generates_events(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "MessageSid": "SM123",
            "From": "whatsapp:+5511999999999",
            "Body": "segue documento",
            "NumMedia": "2",
            "MediaContentType0": "application/pdf",
            "MediaFilename0": "doc.pdf",
            "MediaContent0": base64.b64encode(b"%PDF whatsapp").decode("ascii"),
            "MediaContentType1": "image/jpeg",
            "MediaFilename1": "foto.jpg",
            "MediaContent1": base64.b64encode(b"JPEG").decode("ascii"),
        },
    )

    assert response.status_code == 200
    assert response.json()["accepted_count"] == 2
    events = LocalJsonlEventBus(tmp_path / "events").consume("document.received")
    assert len(events) == 2
    assert all(event["data"]["channel"] == "whatsapp" for event in events)
    assert {event["data"]["file"]["filename"] for event in events} == {"doc.pdf", "foto.jpg"}


def test_whatsapp_webhook_rejects_invalid_mime(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "MessageSid": "SM123",
            "From": "whatsapp:+5511999999999",
            "NumMedia": "1",
            "MediaContentType0": "text/plain",
            "MediaFilename0": "bad.txt",
            "MediaContent0": base64.b64encode(b"hello").decode("ascii"),
        },
    )

    assert response.status_code == 400
    assert "unsupported content_type" in response.json()["detail"]


def test_whatsapp_webhook_signature_when_configured(monkeypatch, tmp_path) -> None:
    _point_backend_com_to_tmp(monkeypatch, tmp_path)
    from backend_com import config
    from backend_com.api import app as app_module

    config.settings.whatsapp_webhook_token = "secret"
    app_module.settings.whatsapp_webhook_token = "secret"
    client = TestClient(app)

    invalid = client.post(
        "/api/v1/whatsapp/webhook",
        data={"NumMedia": "0"},
    )
    valid = client.post(
        "/api/v1/whatsapp/webhook",
        headers={"x-docuparse-signature": "secret"},
        data={"NumMedia": "0"},
    )

    config.settings.whatsapp_webhook_token = ""
    app_module.settings.whatsapp_webhook_token = ""
    assert invalid.status_code == 401
    assert valid.status_code == 200


def _point_backend_com_to_tmp(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DOCUPARSE_LOCAL_STORAGE_DIR", str(tmp_path / "objects"))
    monkeypatch.setenv("DOCUPARSE_LOCAL_EVENT_DIR", str(tmp_path / "events"))
    from backend_com import config
    from backend_com.services import document_ingest

    config.settings.local_storage_dir = tmp_path / "objects"
    config.settings.local_event_dir = tmp_path / "events"
    config.settings.email_webhook_token = ""
    config.settings.whatsapp_webhook_token = ""
    config.settings.internal_service_token = ""
    config.settings.backend_core_document_received_url = ""
    document_ingest.settings.local_storage_dir = tmp_path / "objects"
    document_ingest.settings.local_event_dir = tmp_path / "events"
    document_ingest.settings.email_webhook_token = ""
    document_ingest.settings.whatsapp_webhook_token = ""
    document_ingest.settings.backend_core_document_received_url = ""


def _email_with_attachment(*, sender: str, subject: str, filename: str, content: bytes, content_type: str) -> bytes:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "docs@example.test"
    message["Subject"] = subject
    message["Message-ID"] = f"<{filename}@example.test>"
    message.set_content("Segue anexo.")
    maintype, subtype = content_type.split("/", 1)
    message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
    return message.as_bytes()


class FakeImapClient:
    def __init__(self, messages: list[bytes]) -> None:
        self.messages = messages
        self.seen: list[bytes] = []

    def login(self, username: str, password: str):
        return "OK", [b"logged in"]

    def select(self, mailbox: str):
        return "OK", [str(len(self.messages)).encode("ascii")]

    def search(self, charset, criterion: str):
        ids = b" ".join(str(index).encode("ascii") for index in range(1, len(self.messages) + 1))
        return "OK", [ids]

    def fetch(self, message_id: bytes, query: str):
        message = self.messages[int(message_id) - 1]
        return "OK", [(b"RFC822", message)]

    def store(self, message_id: bytes, command: str, flags: str):
        self.seen.append(message_id)
        return "OK", [b"stored"]

    def logout(self):
        return "OK", [b"logged out"]
