import structlog
from atoms.whatsapp.twilio.service.twilio_client import TwilioClient
from fastapi import APIRouter
from fastapi import Form

logger = structlog.get_logger()

router = APIRouter(tags=["whatsapp_twilio"])


@router.post("/send_message")
async def twilio_whatsapp_send_message(
    account_sid: str = Form(...),
    api_key_sid: str = Form(...),
    api_key_secret: str = Form(...),
    from_number: str = Form(...),
    to: str = Form(...),
    body: str = Form(...),
    delivery_mode: str = Form("real"),
) -> str:
    client = TwilioClient(
        account_sid=account_sid,
        api_key_sid=api_key_sid,
        api_key_secret=api_key_secret,
        from_number=from_number,
        delivery_mode=delivery_mode,
    )
    response = await client.send_message(to=to, body=body)
    return response


@router.post("/send_typing")
async def twilio_whatsapp_send_typing(
    account_sid: str = Form(...),
    api_key_sid: str = Form(...),
    api_key_secret: str = Form(...),
    from_number: str = Form(...),
    to: str = Form(...),
    message_sid: str = Form(...),
    delivery_mode: str = Form("real"),
) -> bool:
    client = TwilioClient(
        account_sid=account_sid,
        api_key_sid=api_key_sid,
        api_key_secret=api_key_secret,
        from_number=from_number,
        delivery_mode=delivery_mode,
    )
    response = await client.send_typing(to=to, message_sid=message_sid)
    return response
