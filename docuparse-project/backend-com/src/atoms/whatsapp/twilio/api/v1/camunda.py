import structlog
from atoms.camunda_decorator import camunda_task
from atoms.whatsapp.twilio.service.twilio_client import TwilioClient
from pydantic import SecretStr

logger = structlog.get_logger()


@camunda_task(topic_name="twilio_whatsapp_send_message")
async def twilio_whatsapp_send_message(
    account_sid: str,
    api_key_sid: str,
    api_key_secret: SecretStr,
    from_number: str,
    to: str,
    body: str,
    delivery_mode: str = "real",
) -> str:
    client = TwilioClient(
        account_sid=account_sid,
        api_key_sid=api_key_sid,
        api_key_secret=api_key_secret.get_secret_value(),
        from_number=from_number,
        delivery_mode=delivery_mode,
    )
    response = await client.send_message(to=to, body=body)
    return response


@camunda_task(topic_name="twilio_whatsapp_send_typing")
async def twilio_whatsapp_send_typing(
    account_sid: str,
    api_key_sid: str,
    api_key_secret: SecretStr,
    from_number: str,
    to: str,
    message_sid: str,
    delivery_mode: str = "real",
) -> bool:
    client = TwilioClient(
        account_sid=account_sid,
        api_key_sid=api_key_sid,
        api_key_secret=api_key_secret.get_secret_value(),
        from_number=from_number,
        delivery_mode=delivery_mode,
    )
    response = await client.send_typing(to=to, message_sid=message_sid)
    return response
