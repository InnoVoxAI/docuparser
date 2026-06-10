"""
email_reader.py
---------------
Módulo standalone para leitura de emails via IMAP.
Captura metadados, corpo (plain + HTML), anexos e imagens inline.

Dependência:
    pip install imap-tools
"""
from __future__ import annotations

import base64
import logging
import re
from datetime import datetime

from imap_tools import AND
from imap_tools import MailBox
from imap_tools import MailMessage
from pydantic import BaseModel
from pydantic import computed_field
from pydantic import ConfigDict
from pydantic import field_serializer
from pydantic import SecretStr

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class Attachment(BaseModel):
    """Representa um anexo ou imagem inline de um email."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    filename: str
    mime_type: str
    size_bytes: int
    content: bytes
    is_inline: bool = False
    content_id: str | None = None

    @field_serializer("content")
    def serialize_content(self, value: bytes, _info):
        """
        Serializa bytes como base64 para JSON.
        """
        return base64.b64encode(value).decode("utf-8")


class ParsedEmail(BaseModel):
    """Representa um email completamente parseado."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    uid: str
    message_id: str
    date: datetime
    subject: str
    sender: str
    recipients: list[str]
    cc: list[str]
    reply_to: str | None = None
    body_plain: str
    body_html: str | None = None
    attachments: list[Attachment] = []
    folder: str = "INBOX"

    @computed_field
    @property
    def sender_email(self) -> str:
        """Extrai só o endereço de email do campo sender."""
        match = re.search(r"<(.+?)>", self.sender)
        return match.group(1) if match else self.sender

    @computed_field
    @property
    def attachment_count(self) -> int:
        return len([a for a in self.attachments if not a.is_inline])

    @computed_field
    @property
    def inline_image_count(self) -> int:
        return len([a for a in self.attachments if a.is_inline])

    def summary(self) -> str:
        """Resumo legível para logging/debug."""
        return (
            f"[{self.uid}] {self.date:%Y-%m-%d %H:%M} | "
            f"De: {self.sender_email} | "
            f"Assunto: {self.subject!r} | "
            f"Anexos: {self.attachment_count} | "
            f"Imagens inline: {self.inline_image_count}"
        )


# ---------------------------------------------------------------------------
# Parser interno
# ---------------------------------------------------------------------------


def _parse_message(msg: MailMessage, folder: str) -> ParsedEmail:
    """Converte um MailMessage do imap-tools em ParsedEmail."""

    # --- Anexos e imagens inline ---
    attachments: list[Attachment] = []

    for att in msg.attachments:
        attachments.append(
            Attachment(
                filename=att.filename or f"attachment_{len(attachments)}",
                mime_type=att.content_type,
                size_bytes=len(att.payload),
                content=att.payload,
                is_inline=False,
                content_id=None,
            )
        )

    # Imagens inline (embutidas no HTML via cid:)
    for part in msg.obj.walk():
        content_disposition = part.get("Content-Disposition", "")
        content_id = part.get("Content-ID", "")
        content_type = part.get_content_type()

        is_inline_image = content_type.startswith("image/") and (
            "inline" in content_disposition.lower()
            or content_id  # tem Content-ID = provavelmente inline
        )

        if is_inline_image:
            payload = part.get_payload(decode=True)
            if payload:
                cid_clean = content_id.strip("<>") if content_id else None
                filename = (
                    part.get_filename()
                    or f"inline_image_{len(attachments)}.{content_type.split('/')[1]}"
                )
                attachments.append(
                    Attachment(
                        filename=filename,
                        mime_type=content_type,
                        size_bytes=len(payload),
                        content=payload,
                        is_inline=True,
                        content_id=cid_clean,
                    )
                )

    # --- Corpo HTML ---
    body_html: str | None = msg.html if msg.html else None

    # --- Reply-To ---
    reply_to_raw = msg.obj.get("Reply-To")
    reply_to = str(reply_to_raw).strip() if reply_to_raw else None

    return ParsedEmail(
        uid=str(msg.uid),
        message_id=msg.obj.get("Message-ID", "").strip(),
        date=msg.date,
        subject=msg.subject,
        sender=msg.from_,
        recipients=list(msg.to),
        cc=list(msg.cc),
        reply_to=reply_to,
        body_plain=msg.text or "",
        body_html=body_html,
        attachments=attachments,
        folder=folder,
    )


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------


class EmailReader:
    """
    Lê emails não lidos da INBOX via IMAP.

    Uso básico:
        reader = EmailReader(host="imap.gmail.com", username="...", password="...")
        emails = reader.fetch_unread()

    Para Gmail com App Password:
        - Ative "Acesso a app menos seguro" OU use uma App Password (recomendado)
        - host = "imap.gmail.com", port = 993

    Para Outlook/Office365:
        - host = "outlook.office365.com", port = 993
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: SecretStr,
        port: int = 993,
        ssl: bool = True,
        folder: str = "INBOX",
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ssl = ssl
        self.folder = folder

    def fetch_unread(
        self,
        limit: int | None = None,
        mark_as_read: bool = False,
    ) -> list[ParsedEmail]:
        """
        Busca todos os emails não lidos da pasta configurada.

        Args:
            limit: Limita o número de emails retornados (mais recentes primeiro).
            mark_as_read: Se True, marca os emails como lidos após buscar.
                          Padrão False (só leitura, sem alterar estado).

        Returns:
            Lista de ParsedEmail ordenada do mais recente para o mais antigo.
        """
        emails: list[ParsedEmail] = []

        try:
            with MailBox(
                self.host,
                port=self.port,
                ssl_context=None
                if not self.ssl
                else __import__("ssl").create_default_context(),
            ).login(
                self.username,
                self.password.get_secret_value(),
                initial_folder=self.folder,
            ) as mailbox:
                criteria = AND(seen=False)

                for msg in mailbox.fetch(
                    criteria, mark_seen=mark_as_read, reverse=True
                ):
                    try:
                        parsed = _parse_message(msg, self.folder)
                        emails.append(parsed)
                        logger.debug("Parsed: %s", parsed.summary())
                    except Exception as e:
                        logger.warning("Erro ao parsear email uid=%s: %s", msg.uid, e)

                    if limit and len(emails) >= limit:
                        break

        except Exception as e:
            logger.error("Erro na conexão IMAP (%s): %s", self.host, e)
            raise

        logger.info(
            "Lidos %d email(s) não lido(s) de %s/%s",
            len(emails),
            self.host,
            self.folder,
        )
        return emails
