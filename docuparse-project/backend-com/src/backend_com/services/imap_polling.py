from __future__ import annotations

import email
import imaplib
import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import Message
from email.policy import default
from email.utils import getaddresses
from typing import Protocol

from backend_com.config import settings
from backend_com.services.email_capture import process_email_attachments

logger = logging.getLogger(__name__)


class ImapPollingError(ValueError):
    pass


@dataclass(frozen=True)
class EmailCaptureSettings:
    tenant_id: str
    provider: str
    inbox_folder: str
    imap_host: str
    imap_port: int
    username: str
    accepted_content_types: set[str]
    max_attachment_bytes: int
    blocked_senders: set[str]
    is_active: bool


class ImapClient(Protocol):
    def login(self, username: str, password: str): ...
    def select(self, mailbox: str): ...
    def search(self, charset, criterion: str): ...
    def fetch(self, message_id: bytes, query: str): ...
    def store(self, message_id: bytes, command: str, flags: str): ...
    def logout(self): ...


def fetch_email_settings_from_core(tenant_id: str) -> EmailCaptureSettings:
    query = urllib.parse.urlencode({"tenant": tenant_id})
    request = urllib.request.Request(f"{settings.backend_core_email_settings_url}?{query}", method="GET")
    if settings.internal_service_token:
        request.add_header("Authorization", f"Bearer {settings.internal_service_token}")
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return email_settings_from_payload(payload, tenant_id=tenant_id)


def email_settings_from_payload(payload: dict, *, tenant_id: str = "tenant-demo") -> EmailCaptureSettings:
    accepted = {
        item.strip()
        for item in str(payload.get("accepted_content_types") or "").split(",")
        if item.strip()
    }
    blocked = {
        item.strip().lower()
        for raw_line in str(payload.get("blocked_senders") or "").splitlines()
        for item in raw_line.split(",")
        if item.strip()
    }
    return EmailCaptureSettings(
        tenant_id=tenant_id,
        provider=str(payload.get("provider") or "imap"),
        inbox_folder=str(payload.get("inbox_folder") or "INBOX"),
        imap_host=str(payload.get("imap_host") or ""),
        imap_port=int(payload.get("imap_port") or 993),
        username=str(payload.get("username") or ""),
        accepted_content_types=accepted,
        max_attachment_bytes=int(payload.get("max_attachment_mb") or 20) * 1024 * 1024,
        blocked_senders=blocked,
        is_active=bool(payload.get("is_active", True)),
    )


def poll_imap_once(
    *,
    email_settings: EmailCaptureSettings,
    password: str,
    limit: int = 10,
    mark_as_read: bool = False,
    client_factory=None,
) -> dict:
    if not email_settings.is_active:
        return {"status": "skipped", "reason": "email settings inactive", "accepted_count": 0, "documents": []}
    if email_settings.provider != "imap":
        return {"status": "skipped", "reason": f"provider {email_settings.provider} is not imap", "accepted_count": 0, "documents": []}
    if not email_settings.imap_host.strip():
        raise ValueError("imap_host is required")
    if not email_settings.username.strip():
        raise ValueError("username is required")
    if not password.strip():
        raise ValueError("DOCUPARSE_IMAP_PASSWORD is required")

    factory = client_factory or (lambda host, port: imaplib.IMAP4_SSL(host, port, timeout=settings.imap_timeout_seconds))
    client = factory(email_settings.imap_host, email_settings.imap_port)
    documents: list[dict] = []
    processed_messages = 0
    skipped_attachments = 0
    duplicate_count = 0

    try:
        _expect_ok(_imap_call(client.login, email_settings.username, password, action="login"), "login")
        _expect_ok(_imap_call(client.select, email_settings.inbox_folder, action="select mailbox"), "select mailbox")
        _, message_ids = _expect_ok(_imap_call(client.search, None, "UNSEEN", action="search unseen"), "search unseen")
        ids = message_ids[0].split()[:limit] if message_ids else []

        fetch_query = "(RFC822)" if mark_as_read else "(BODY.PEEK[])"
        for message_id in ids:
            _, fetched = _expect_ok(_imap_call(client.fetch, message_id, fetch_query, action="fetch message"), "fetch message")
            raw_message = _raw_message_bytes(fetched)
            if raw_message is None:
                continue

            message = email.message_from_bytes(raw_message, policy=default)
            sender = _message_sender(message)
            if sender.lower() in email_settings.blocked_senders:
                continue

            attachments, skipped = _attachments_from_message(message, email_settings)
            skipped_attachments += skipped
            if attachments:
                result = process_email_attachments(
                    tenant_id=email_settings.tenant_id,
                    attachments=attachments,
                    sender=sender,
                    message_id=str(message.get("Message-ID") or message_id.decode("ascii", errors="ignore")),
                    subject=str(message.get("Subject") or ""),
                    provider="imap",
                )
                documents.extend(result["documents"])
                duplicate_count += result["duplicate_count"]
            if mark_as_read:
                _imap_call(client.store, message_id, "+FLAGS", "\\Seen", action="mark message as read")
            processed_messages += 1
    finally:
        try:
            client.logout()
        except Exception:
            logger.debug("imap_logout_failed", exc_info=True)

    return {
        "status": "ok",
        "processed_messages": processed_messages,
        "accepted_count": len(documents),
        "skipped_attachments": skipped_attachments,
        "duplicate_count": duplicate_count,
        "documents": documents,
    }


def poll_configured_imap_once(tenant_id: str = "tenant-demo") -> dict:
    return poll_imap_once(
        email_settings=fetch_email_settings_from_core(tenant_id),
        password=settings.imap_password,
        limit=settings.imap_poll_limit,
        mark_as_read=settings.imap_mark_as_read,
    )


def _attachments_from_message(message: Message, email_settings: EmailCaptureSettings) -> tuple[list[dict], int]:
    attachments = []
    skipped = 0
    for part in message.walk():
        filename = part.get_filename()
        if not filename:
            continue
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True) or b""
        if email_settings.accepted_content_types and content_type not in email_settings.accepted_content_types:
            skipped += 1
            continue
        if len(payload) > email_settings.max_attachment_bytes:
            skipped += 1
            continue
        attachments.append(
            {
                "filename": filename,
                "content_type": content_type,
                "content": payload,
            }
        )
    return attachments, skipped


def _expect_ok(result, action: str):
    status, payload = result
    if _decode_status(status) != "OK":
        raise ImapPollingError(f"IMAP {action} failed: {payload!r}")
    return status, payload


def _imap_call(function, *args, action: str):
    try:
        return function(*args)
    except imaplib.IMAP4.error as exc:
        raise ImapPollingError(f"IMAP {action} failed: {_format_imap_error(exc)}") from exc


def _format_imap_error(error: imaplib.IMAP4.error) -> str:
    if error.args and isinstance(error.args[0], bytes):
        return error.args[0].decode("utf-8", errors="replace")
    return str(error)


def _decode_status(status) -> str:
    if isinstance(status, bytes):
        return status.decode("ascii", errors="ignore")
    return str(status)


def _raw_message_bytes(fetched) -> bytes | None:
    for item in fetched:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def _message_sender(message: Message) -> str:
    addresses = getaddresses([str(message.get("From") or "")])
    if addresses:
        return addresses[0][1] or str(message.get("From") or "")
    return str(message.get("From") or "")
