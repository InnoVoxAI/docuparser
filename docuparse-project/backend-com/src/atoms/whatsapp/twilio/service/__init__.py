from atoms.whatsapp.twilio.service.twilio_client import TwilioClient
from atoms.whatsapp.twilio.service.webhook import router as webhook_router
from atoms.whatsapp.twilio.service.webhook import WhatsAppMessage

"""TwilioClient para envio de mensagens WhatsApp via Twilio API.
Encapsula a autenticação e chamadas HTTP à Messages API do Twilio.
Usa API Key (api_key_sid + api_key_secret) para autenticação outbound,
separando de auth_token que é usado apenas para validação de assinatura
inbound no webhook.
Args:

    account_sid: Twilio Account SID (identifica a conta).
    api_key_sid: Twilio API Key SID (ex: SKxxxxxxxx).
    api_key_secret: Twilio API Key Secret.
    from_number: Número remetente no formato whatsapp:+XXXXXXXXXXX.
Exemplo:
    >>> client = TwilioClient("AC...",
    ...                     "SK...",
    ...                     "secret",
    ...                     "whatsapp:+14155238886")
    >>> sid = await client.send_message("+5511999999999", "Olá!")
"""

__all__ = ["TwilioClient", "webhook_router", "WhatsAppMessage"]
