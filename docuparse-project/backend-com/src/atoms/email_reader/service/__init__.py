"""
email_reader package
--------------------
Leitura de emails não lidos via IMAP com parsing completo de
metadados, corpo (plain + HTML), anexos e imagens inline.
"""
from atoms.email_reader.service.email_reader import Attachment
from atoms.email_reader.service.email_reader import EmailReader
from atoms.email_reader.service.email_reader import ParsedEmail

__all__ = [
    "EmailReader",
    "ParsedEmail",
    "Attachment",
]
