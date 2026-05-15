from __future__ import annotations

import json
import hmac
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend_com.config import settings
from backend_com.services.email_capture import process_email_attachments
from backend_com.services.imap_polling import ImapPollingError, poll_configured_imap_once
from backend_com.services.document_ingest import DuplicateDocumentError
from backend_com.services.manual_upload import process_manual_upload
from backend_com.services.whatsapp_capture import process_whatsapp_media

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log_startup_config()
    yield


def _log_startup_config() -> None:
    """Print resolved config values on startup to diagnose env var issues."""
    raw_primary = os.environ.get("DOCUPARSE_IMAP_PASSWORD")
    raw_fallback = os.environ.get("imap_reader_password")
    password_status = f"[SET, {len(settings.imap_password)} chars]" if settings.imap_password else "[EMPTY — adicione DOCUPARSE_IMAP_PASSWORD no .env raiz do projeto]"

    print("", flush=True)
    print("=== backend-com startup config ===", flush=True)
    print(f"  imap_password          : {password_status}", flush=True)
    print(f"  DOCUPARSE_IMAP_PASSWORD: {'[presente, raw=' + repr(raw_primary[:4]) + '...]' if raw_primary else '[AUSENTE no os.environ]'}", flush=True)
    print(f"  imap_reader_password   : {'[presente, raw=' + repr(raw_fallback[:4]) + '...]' if raw_fallback else '[AUSENTE no os.environ]'}", flush=True)
    print(f"  imap_poll_limit        : {settings.imap_poll_limit}", flush=True)
    print(f"  imap_mark_as_read      : {settings.imap_mark_as_read}", flush=True)
    print(f"  imap_timeout_seconds   : {settings.imap_timeout_seconds}", flush=True)
    print(f"  cors_allowed_origins   : {settings.cors_allowed_origins}", flush=True)
    print(f"  backend_core_email_url : {settings.backend_core_email_settings_url}", flush=True)
    print("==================================", flush=True)
    print("", flush=True)


app = FastAPI(
    title="DocuParse Backend COM",
    description="Captura documentos e publica eventos document.received",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.service_name}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": settings.service_name}


@app.post("/api/v1/documents/manual")
async def manual_document_upload(
    file: UploadFile = File(...),
    tenant_id: str = Form("tenant-demo"),
    sender: str | None = Form(None),
    metadata_json: str | None = Form(None),
    authorization: str | None = Header(default=None),
):
    _validate_internal_service_token(authorization)
    try:
        metadata = json.loads(metadata_json) if metadata_json else {}
        if not isinstance(metadata, dict):
            raise ValueError("metadata_json must decode to an object")
        content = await file.read()
        return process_manual_upload(
            tenant_id=tenant_id,
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            content=content,
            sender=sender,
            metadata=metadata,
        )
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/email/webhook")
async def email_webhook(
    attachments: list[UploadFile] = File(default=[]),
    tenant_id: str = Form("tenant-demo"),
    sender: str | None = Form(None),
    message_id: str | None = Form(None),
    subject: str | None = Form(None),
    provider: str = Form("webhook"),
    x_docuparse_signature: str | None = Header(default=None),
):
    _validate_email_signature(x_docuparse_signature)
    return await _process_email_files(
        attachments=attachments,
        tenant_id=tenant_id,
        sender=sender,
        message_id=message_id,
        subject=subject,
        provider=provider,
    )


@app.post("/api/v1/email/messages")
async def email_messages(
    attachments: list[UploadFile] = File(default=[]),
    tenant_id: str = Form("tenant-demo"),
    sender: str | None = Form(None),
    message_id: str | None = Form(None),
    subject: str | None = Form(None),
):
    return await _process_email_files(
        attachments=attachments,
        tenant_id=tenant_id,
        sender=sender,
        message_id=message_id,
        subject=subject,
        provider="imap",
    )


@app.post("/api/v1/email/poll")
async def poll_email_messages(
    tenant_id: str = "tenant-demo",
    authorization: str | None = Header(default=None),
):
    _validate_internal_service_token(authorization)
    try:
        return poll_configured_imap_once(tenant_id=tenant_id)
    except ImapPollingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _process_email_files(
    *,
    attachments: list[UploadFile],
    tenant_id: str,
    sender: str | None,
    message_id: str | None,
    subject: str | None,
    provider: str,
):
    try:
        attachment_payloads = [
            {
                "filename": attachment.filename or "",
                "content_type": attachment.content_type or "application/octet-stream",
                "content": await attachment.read(),
            }
            for attachment in attachments
        ]
        metadata_channel = {
            "provider": provider,
            "sender": sender or "",
            "message_id": message_id or "",
            "subject": subject or "",
        }
        result = process_email_attachments(
            tenant_id=tenant_id,
            attachments=attachment_payloads,
            sender=sender,
            message_id=message_id,
            subject=subject,
            provider=provider,
            metadata_channel=metadata_channel,
        )
        return {
            "accepted_count": len(result["documents"]),
            "duplicate_count": result["duplicate_count"],
            "documents": result["documents"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _validate_email_signature(signature: str | None) -> None:
    if settings.email_webhook_token and signature != settings.email_webhook_token:
        raise HTTPException(status_code=401, detail="invalid email webhook signature")


def _validate_internal_service_token(authorization: str | None) -> None:
    if not settings.internal_service_token:
        return
    expected = f"Bearer {settings.internal_service_token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="invalid internal service token")


@app.post("/api/v1/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    x_docuparse_signature: str | None = Header(default=None),
):
    _validate_whatsapp_signature(x_docuparse_signature)
    form = await request.form()
    try:
        tenant_id = str(form.get("tenant_id") or form.get("TenantId") or "tenant-demo")
        message_sid = str(form.get("MessageSid") or "")
        sender = str(form.get("From") or form.get("WaId") or "")
        body = str(form.get("Body") or "")
        num_media = int(str(form.get("NumMedia") or "0"))
        media_items = [_media_item_from_form(form, index) for index in range(num_media)]
        documents = process_whatsapp_media(
            tenant_id=tenant_id,
            media_items=media_items,
            sender=sender,
            message_sid=message_sid,
            body=body,
        )
        return {
            "accepted_count": len(documents),
            "documents": documents,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _media_item_from_form(form: Any, index: int) -> dict:
    content_type = str(form.get(f"MediaContentType{index}") or "")
    filename = str(form.get(f"MediaFilename{index}") or f"whatsapp-media-{index + 1}")
    media_url = form.get(f"MediaUrl{index}")
    content_base64 = form.get(f"MediaContent{index}") or form.get(f"MediaBody{index}")
    return {
        "filename": filename,
        "content_type": content_type,
        "media_url": str(media_url) if media_url else None,
        "content_base64": str(content_base64) if content_base64 else None,
    }


def _validate_whatsapp_signature(signature: str | None) -> None:
    if settings.whatsapp_webhook_token and signature != settings.whatsapp_webhook_token:
        raise HTTPException(status_code=401, detail="invalid whatsapp webhook signature")
