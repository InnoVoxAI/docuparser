"""Poll Twilio REST API for recent incoming WhatsApp messages and ingest media.

Fluxo:
  poll_configured_twilio_once()
    → Twilio REST API: GET /Messages.json?To=whatsapp:{from_number}
    → Para cada mensagem com mídia: GET /Messages/{sid}/Media.json
    → Baixa cada arquivo com autenticação Basic (Account SID + Auth Token)
    → Deduplicação por SHA256 dentro da sessão (cross-sessão: DuplicateDocumentError do core)
    → process_whatsapp_media() → ingest_document() → pipeline OCR
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from backend_com.config import settings
from backend_com.services.document_ingest import DuplicateDocumentError
from backend_com.services.whatsapp_capture import process_whatsapp_media

logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

ACCEPTED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}

_EXT_MAP = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
}


class TwilioPollingError(ValueError):
    pass


def poll_configured_twilio_once(tenant_id: str = "tenant-demo") -> dict:
    """Poll usando as credenciais Twilio configuradas via env vars."""
    if not settings.twilio_account_sid:
        raise TwilioPollingError("TWILIO_ACCOUNT_SID is required")
    if not settings.twilio_auth_token:
        raise TwilioPollingError("TWILIO_AUTH_TOKEN is required")
    if not settings.twilio_from_number:
        raise TwilioPollingError("TWILIO_FROM_NUMBER is required")
    return _poll_once(
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
        from_number=settings.twilio_from_number,
        tenant_id=tenant_id,
        limit=settings.twilio_poll_limit,
    )


def _poll_once(
    *,
    account_sid: str,
    auth_token: str,
    from_number: str,
    tenant_id: str,
    limit: int = 20,
) -> dict:
    to_param = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
    encoded_to = urllib.parse.quote(to_param, safe="")
    url = (
        f"{TWILIO_API_BASE}/Accounts/{account_sid}/Messages.json"
        f"?To={encoded_to}&PageSize={min(limit, 50)}"
    )
    data = _api_get(url, account_sid, auth_token)
    messages = data.get("messages", [])

    documents: list[dict] = []
    duplicate_count = 0
    seen_hashes: set[str] = set()

    for message in messages:
        message_sid = str(message.get("sid") or "")
        sender = str(message.get("from") or "").replace("whatsapp:", "")
        body = str(message.get("body") or "")
        num_media = int(message.get("num_media") or 0)

        if num_media == 0:
            continue

        media_list = _fetch_message_media(account_sid, auth_token, message_sid)
        media_items: list[dict] = []

        for media in media_list:
            media_sid = str(media.get("sid") or "")
            content_type = str(media.get("content_type") or "")
            if content_type not in ACCEPTED_CONTENT_TYPES:
                logger.debug("twilio_media_skipped_type", extra={"content_type": content_type, "media_sid": media_sid})
                continue

            media_url = (
                f"{TWILIO_API_BASE}/Accounts/{account_sid}"
                f"/Messages/{message_sid}/Media/{media_sid}"
            )
            try:
                content, real_filename = download_twilio_media(media_url, account_sid, auth_token)
            except Exception as exc:
                logger.warning("twilio_media_download_failed", extra={"error": str(exc), "media_sid": media_sid})
                continue

            sha256 = hashlib.sha256(content).hexdigest()
            if sha256 in seen_hashes:
                duplicate_count += 1
                continue
            seen_hashes.add(sha256)

            ext = _EXT_MAP.get(content_type, "")
            fallback_filename = f"whatsapp-{message_sid}-{media_sid}{ext}"
            filename = real_filename or fallback_filename
            media_items.append({
                "filename": filename,
                "content_type": content_type,
                "content": content,
                "media_url": media_url,
            })

        if not media_items:
            continue

        try:
            results = process_whatsapp_media(
                tenant_id=tenant_id,
                media_items=media_items,
                sender=sender,
                message_sid=message_sid,
                body=body,
            )
            documents.extend(results)
        except DuplicateDocumentError:
            duplicate_count += len(media_items)
        except Exception as exc:
            logger.warning("twilio_message_ingest_failed", extra={"error": str(exc), "message_sid": message_sid})

    return {
        "status": "ok",
        "accepted_count": len(documents),
        "duplicate_count": duplicate_count,
        "documents": documents,
    }


def download_twilio_media(url: str, account_sid: str, auth_token: str) -> tuple[bytes, str | None]:
    """Baixa um arquivo de mídia da Twilio com autenticação Basic.

    Returns (content, original_filename) where original_filename is extracted from
    the Content-Disposition header when available, or None if not present.
    """
    request = urllib.request.Request(url)
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    request.add_header("Authorization", f"Basic {credentials}")
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
        filename = _extract_filename_from_headers(response.headers)
        return content, filename


def _extract_filename_from_headers(headers) -> str | None:
    """Extract original filename from Content-Disposition response header."""
    content_disposition = headers.get("Content-Disposition", "")
    if not content_disposition:
        return None
    for part in content_disposition.split(";"):
        part = part.strip()
        if part.lower().startswith("filename*="):
            # RFC 5987: charset'language'encoded-value
            value = part[10:].strip()
            try:
                _, _, encoded = value.partition("''")
                if encoded:
                    return urllib.parse.unquote(encoded)
            except Exception:
                pass
        elif part.lower().startswith("filename="):
            value = part[9:].strip().strip("\"'")
            if value:
                return value
    return None


def _fetch_message_media(account_sid: str, auth_token: str, message_sid: str) -> list[dict]:
    url = f"{TWILIO_API_BASE}/Accounts/{account_sid}/Messages/{message_sid}/Media.json"
    data = _api_get(url, account_sid, auth_token)
    return data.get("media_list", [])


def _api_get(url: str, account_sid: str, auth_token: str) -> dict:
    request = urllib.request.Request(url)
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    request.add_header("Authorization", f"Basic {credentials}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise TwilioPollingError(f"Twilio API error {exc.code}: {exc.reason}") from exc
    except (OSError, urllib.error.URLError) as exc:
        raise TwilioPollingError(f"Twilio API request failed: {exc}") from exc
