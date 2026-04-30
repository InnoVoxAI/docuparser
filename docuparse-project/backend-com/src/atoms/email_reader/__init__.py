"""
email_reader package
--------------------
Leitura de emails não lidos via IMAP com parsing completo de
metadados, corpo (plain + HTML), anexos e imagens inline.
"""
from atoms.email_reader.api.v1.camunda import camunda_email_fetch_unread
from atoms.email_reader.api.v1.fastapi import router as email_reader_router
from atoms.email_reader.config import imap_config
from atoms.email_reader.config import KNOWN_HOSTS
from atoms.email_reader.service.email_reader import Attachment
from atoms.email_reader.service.email_reader import EmailReader
from atoms.email_reader.service.email_reader import ParsedEmail

__all__ = [
    "EmailReader",
    "ParsedEmail",
    "Attachment",
    "imap_config",
    "KNOWN_HOSTS",
    "email_reader_router",
    "camunda_email_fetch_unread",
]
