from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class WebhookSender:
    """Sends data to a HTTP inbound connector (webhook).

    Configure once, call send() for each payload.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ):
        self.url = url
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.timeout = timeout

    async def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json() if response.content else {}


async def send_using_webhook(
    payload: dict[str, Any],
    sender: WebhookSender,
) -> dict[str, Any]:
    try:
        logger.info("Sending payload to webhook", url=sender.url)
        result = await sender.send(payload)
        logger.info("webhook_sent", url=sender.url)
        return result
    except Exception as e:
        logger.error("webhook_failed", url=sender.url, error=str(e))
        raise
