import structlog
from atoms.camunda_decorator import camunda_task
from atoms.email_reader.service.email_reader import EmailReader
from atoms.email_reader.service.email_reader import ParsedEmail
from pydantic import SecretStr

logger = structlog.get_logger()


@camunda_task(topic_name="email_reader_fetch_unread")
def camunda_email_fetch_unread(
    host: str,
    username: str,
    password: SecretStr,
    port: int = 993,
    ssl: bool = True,
    folder: str = "INBOX",
    mark_as_read: bool = False,
) -> ParsedEmail | None:
    reader = EmailReader(
        host=host,
        username=username,
        password=password,
        port=port,
        ssl=ssl,
        folder=folder,
    )

    logger.info(
        "Fetching unread emails",
        host=host,
        username=username,
        folder=folder,
        limit=1,
        mark_as_read=mark_as_read,
    )

    emails = reader.fetch_unread(limit=1, mark_as_read=mark_as_read)

    return emails[0] if emails and len(emails) > 0 else None
