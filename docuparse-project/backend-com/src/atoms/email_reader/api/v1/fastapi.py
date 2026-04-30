import asyncio

import structlog
from atoms.email_reader.config import imap_config
from atoms.email_reader.service.email_reader import EmailReader
from atoms.email_reader.service.email_reader import ParsedEmail
from atoms.fastapi_decorator import daemon
from atoms.send_to_webhook import send_using_webhook
from atoms.send_to_webhook import WebhookSender
from fastapi import APIRouter
from fastapi import Form
from pydantic import SecretStr

logger = structlog.get_logger()

router = APIRouter(tags=["email_reader"])


@router.post("/fetch_unread")
async def fetch_unread(
    host: str = Form(...),
    username: str = Form(...),
    password: SecretStr = Form(...),
    port: int = Form(993),
    ssl: bool = Form(True),
    folder: str = Form("INBOX"),
    limit: int | None = Form(None),
    mark_as_read: bool = Form(False),
) -> list[ParsedEmail]:
    reader = EmailReader(
        host=host,
        username=username,
        password=password,
        port=port,
        ssl=ssl,
        folder=folder,
    )

    emails = reader.fetch_unread(limit=limit, mark_as_read=mark_as_read)

    return emails


if imap_config.run_as_daemon:
    if imap_config.webhook_url:
        webhook_sender = WebhookSender(
            url=imap_config.webhook_url, headers=imap_config.headers
        )
    else:
        logger.warning(
            "webhook_url_not_configured",
            message="IMAP reader will run as daemon but webhook_url is not configured. Emails will be fetched but not sent to any webhook.",
        )
        webhook_sender = None

    @daemon
    async def daemon_fetch_unread():
        reader = EmailReader(
            host=imap_config.host,
            username=imap_config.username,
            password=imap_config.password,
            port=imap_config.port,
            ssl=imap_config.ssl,
            folder=imap_config.folder,
        )

        while True:
            try:
                logger.info("Daemon Fetch Unread running...")
                emails = reader.fetch_unread(
                    limit=imap_config.limit, mark_as_read=imap_config.mark_as_read
                )

                for email in emails:
                    logger.info(
                        "Email recebido", attachments_count=len(email.attachments)
                    )
                    for att in email.attachments:
                        payload = email.model_copy(
                            deep=True, update={"attachments": [att]}
                        )  # Criar uma cópia do email para modificar o campo attachments
                        if webhook_sender:
                            result = await send_using_webhook(
                                payload=payload.model_dump(mode="json"),
                                sender=webhook_sender,
                            )
                            logger.info(
                                "webhook_email_reader_enqueued",
                                email_uid=email.uid,
                                webhook_response=result,
                            )
            except Exception as e:
                logger.error(
                    "webhook_email_reader_failed", email_uid=email.uid, error=str(e)
                )
            await asyncio.sleep(imap_config.daemon_interval)
