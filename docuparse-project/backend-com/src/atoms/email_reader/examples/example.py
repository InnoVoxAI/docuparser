"""
example.py
----------
Exemplos de uso do módulo email_reader.
"""
import logging
from pathlib import Path

from atoms.email_reader import EmailReader
from atoms.email_reader import imap_config

# Configura logging para ver o que está acontecendo
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


# ---------------------------------------------------------------------------
# Exemplo 1 — Instanciação direta
# ---------------------------------------------------------------------------
def example_direct():
    reader = EmailReader(
        host=imap_config.host,
        username=imap_config.username,
        password=imap_config.password,
    )

    emails = reader.fetch_unread(limit=10)

    for email in emails:
        print(email.summary())
        print(f"  Plain text ({len(email.body_plain)} chars)")
        if email.body_html:
            print(f"  HTML ({len(email.body_html)} chars)")
        for att in email.attachments:
            kind = "inline" if att.is_inline else "anexo"
            print(
                f"  [{kind}] {att.filename} — {att.mime_type} ({att.size_bytes} bytes)"
            )


# ---------------------------------------------------------------------------
# Exemplo 3 — Salvar anexos em disco
# ---------------------------------------------------------------------------
def example_save_attachments(output_dir: str = "/tmp/email_attachments"):
    reader = EmailReader(
        host=imap_config.host,
        username=imap_config.username,
        password=imap_config.password,
    )

    emails = reader.fetch_unread(limit=5)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for email in emails:
        # Pasta por UID do email
        email_dir = output_path / email.uid
        email_dir.mkdir(exist_ok=True)

        for att in email.attachments:
            dest = email_dir / att.filename
            dest.write_bytes(att.content)
            print(f"Salvo: {dest}")


# ---------------------------------------------------------------------------
# Exemplo 4 — Acessando campos individualmente
# ---------------------------------------------------------------------------
def example_field_access():
    reader = EmailReader(
        host=imap_config.host,
        username=imap_config.username,
        password=imap_config.password,
    )

    emails = reader.fetch_unread(limit=1)
    if not emails:
        print("Nenhum email não lido.")
        return

    e = emails[0]

    print(f"UID:        {e.uid}")
    print(f"Message-ID: {e.message_id}")
    print(f"Data:       {e.date}")
    print(f"Assunto:    {e.subject}")
    print(f"De:         {e.sender}")
    print(f"Email de:   {e.sender_email}")
    print(f"Para:       {e.recipients}")
    print(f"CC:         {e.cc}")
    print(f"Reply-To:   {e.reply_to}")
    print(f"Plain text:\n{e.body_plain[:300]}...")
    if e.body_html:
        print(f"HTML (primeiros 300 chars):\n{e.body_html[:300]}...")
    print(f"Anexos: {e.attachment_count}")
    print(f"Imagens inline: {e.inline_image_count}")


if __name__ == "__main__":
    # Troque para o exemplo que quiser testar
    example_direct()
