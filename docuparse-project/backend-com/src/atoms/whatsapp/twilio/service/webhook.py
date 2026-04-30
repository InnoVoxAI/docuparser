"""Webhook do Twilio — processamento assíncrono via fila.

Recebe mensagens do Twilio, valida, aplica rate limit, e coloca na fila
para processamento pelo Worker. Retorna 200 imediatamente (TwiML vazio).

Fluxo: Twilio -> POST /webhook/twilio -> Fila (PostgreSQL) -> Worker

Uso:
    curl -X POST ".../webhook/twilio?agent=rhawk_assistant" \
         -d "MessageSid=SM123&From=whatsapp:+5511..."
"""
import structlog
from atoms.send_to_webhook import send_using_webhook
from atoms.send_to_webhook import WebhookSender
from atoms.whatsapp.twilio.config import twilio_settings
from atoms.whatsapp.twilio.service.dependencies import check_rate_limit
from atoms.whatsapp.twilio.service.dependencies import validate_twilio_signature
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Form
from fastapi import HTTPException
from fastapi import Response
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(tags=["whatsapp_twilio_webhook"])

# TwiML vazio — indica ao Twilio que recebemos a mensagem
EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


class WhatsAppMessage(BaseModel):
    """Modelo de mensagem WhatsApp recebido do Twilio.

    Campos principais:
    - message_sid: ID da mensagem no Twilio (MessageSid).
    - from_number: Número remetente (From) no formato whatsapp:+55...
    - to_number: Número de destino (To) no formato whatsapp:+...
    - body: Texto da mensagem (pode ser vazio em mensagens de mídia).
    - num_media: Quantidade de mídias anexadas.
    - media_url: URL da primeira mídia (quando num_media > 0).
    - media_type: MIME type da primeira mídia.
    - wa_id: WhatsApp ID do remetente (WaId, fallback de From).

    A validação de assinatura é feita separadamente via Depends(validate_twilio_signature).
    """

    message_sid: str
    from_number: str
    to_number: str
    body: str
    num_media: int
    media_url: str | None
    media_type: str | None
    wa_id: str


webhook_sender = WebhookSender(
    url=twilio_settings.webhook_url, headers=twilio_settings.headers
)


@router.post("/webhook/twilio")
async def webhook_twilio(
    message_sid: str = Form(
        default="",
        alias="MessageSid",
        description="ID da mensagem no Twilio (MessageSid).",
    ),
    from_number: str = Form(
        default="",
        alias="From",
        description="Número remetente no formato whatsapp:+55...",
    ),
    to_number_form: str = Form(
        default="",
        alias="To",
        description="Número de destino no formato whatsapp:+...",
    ),
    body: str = Form(
        default="",
        alias="Body",
        description="Texto da mensagem (pode ser vazio em mensagens de mídia).",
    ),
    num_media_raw: str = Form(
        default="0",
        alias="NumMedia",
        description="Quantidade de mídias anexadas.",
    ),
    media_url_form: str | None = Form(
        default=None,
        alias="MediaUrl0",
        description="URL da primeira mídia (quando NumMedia > 0).",
    ),
    media_type_form: str | None = Form(
        default=None,
        alias="MediaContentType0",
        description="MIME type da primeira mídia.",
    ),
    wa_id: str = Form(
        default="",
        alias="WaId",
        description="WhatsApp ID do remetente (fallback de From).",
    ),
    _signature: None = Depends(validate_twilio_signature),
) -> Response:
    """Recebe webhook do Twilio e enfileira para processamento.

    O Worker consome a mensagem da fila, executa o agente, e envia
    a resposta via Twilio. Assinatura validada via HMAC-SHA1 (SDK oficial)
    quando VALIDATE_TWILIO_SIGNATURE=true.

    Args:
        agent: ID do agente (query param).

    Returns:
        TwiML vazio com status 200.
    """
    # Sanitização de campos do Twilio recebidos via x-www-form-urlencoded.
    # From vem como "whatsapp:+55...", WaId vem como "5511..." sem + (fallback).
    phone_number = (from_number or "").replace("whatsapp:", "")
    if not phone_number and wa_id:
        # WaId pode vir sem + — normaliza para E.164
        phone_number = wa_id if wa_id.startswith("+") else f"+{wa_id}"
    body = body or ""
    to_number = (to_number_form or "").replace("whatsapp:", "")
    message_sid = message_sid or ""

    # Rejeita webhook sem identidade de remetente (From e WaId ambos vazios)
    if not phone_number:
        logger.warning(
            "webhook_missing_sender",
            message_sid=message_sid,
            from_raw=from_number,
            wa_id_raw=wa_id,
        )
        raise HTTPException(
            status_code=400,
            detail="Missing sender identity (From/WaId)",
        )

    # Mídia (imagem, áudio)
    try:
        num_media = int(num_media_raw or "0")
    except ValueError:
        num_media = 0
    media_url = media_url_form.strip() if (num_media > 0 and media_url_form) else None
    media_type = (
        media_type_form.strip() if (num_media > 0 and media_type_form) else None
    )

    # Rate limit
    await check_rate_limit(phone_number)

    # envia a mensagem via webhook para processamento assíncrono pelo Worker
    message = WhatsAppMessage(
        message_sid=message_sid,
        from_number=phone_number,
        to_number=to_number,
        body=body,
        num_media=num_media,
        media_url=media_url,
        media_type=media_type,
        wa_id=wa_id,
    )

    logger.info(
        "webhook_twilio_received",
        phone=phone_number,
        message_id=message.message_sid,
        buffered=False,
    )

    result = await send_using_webhook(
        payload=message.model_dump(), sender=webhook_sender
    )
    logger.info(
        "webhook_twilio_enqueued",
        phone=phone_number,
        message_id=message.message_sid,
        webhook_result=result,
    )

    return Response(content=EMPTY_TWIML, media_type="application/xml")
