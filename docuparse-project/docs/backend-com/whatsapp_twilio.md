# WhatsApp (Twilio) - Backend Com

Este documento descreve o fluxo atual de WhatsApp via Twilio no backend-com, cobrindo rotas, dependencias, configuracao e pontos de integracao.

## Visao geral do modulo

Arquivos principais:
- src/atoms/whatsapp/twilio/service/webhook.py
- src/atoms/whatsapp/twilio/service/dependencies.py
- src/atoms/whatsapp/twilio/service/twilio_client.py
- src/atoms/whatsapp/twilio/api/v1/fastapi.py
- src/atoms/whatsapp/twilio/api/v1/camunda.py
- src/atoms/whatsapp/twilio/config.py

O modulo expõe:
- Webhook inbound do Twilio para receber mensagens WhatsApp.
- Endpoints outbound para enviar mensagens e indicador de digitacao.
- Tarefas Camunda para envio de mensagens/typing.
- Validacao opcional de assinatura do Twilio e rate limit por numero.

## Fluxo inbound (webhook Twilio)

Fluxo principal:
1. Twilio envia POST form-url-encoded para /webhook/twilio.
2. O backend-com (FastAPI) recebe essa chamada.
3. A rota valida assinatura (opcional) e aplica rate limit por telefone.
4. Os campos sao normalizados (From/WaId, To, Body, midia).
5. O payload e enviado para um webhook interno (queue/worker externo).
6. A resposta ao Twilio e um TwiML vazio com status 200.

Quem chama e quem recebe:
- Chamador: Twilio (evento inbound quando alguem envia mensagem no WhatsApp).
- Receptor: backend-com (FastAPI), rota /webhook/twilio.

Detalhes por arquivo:
- src/atoms/whatsapp/twilio/service/webhook.py
  - Define o modelo WhatsAppMessage.
  - Sanitiza telefone (From ou WaId) e midia.
  - Chama check_rate_limit().
  - Envia o payload via WebhookSender para twilio_settings.webhook_url.
  - Retorna TwiML vazio.
- src/atoms/whatsapp/twilio/service/dependencies.py
  - validate_twilio_signature(): valida X-Twilio-Signature via SDK oficial.
  - check_rate_limit(): sliding window em memoria por numero.
  - build_validation_url(): reconstrucao da URL quando atras de proxy.

Observacoes:
- A fila/worker que processa a mensagem nao esta neste modulo. O webhook interno e apenas o ponto de handoff.
- O rate limit fica em memoria do processo FastAPI (nao e compartilhado entre pods).

## Fluxo outbound (send_message / send_typing)

Rotas FastAPI:
- POST /send_message
  - Quem chama: seu sistema (servico interno ou outro modulo).
  - Quem recebe: backend-com (FastAPI).
  - O backend-com envia a mensagem para a API do Twilio (Messages API).
- POST /send_typing
  - Quem chama: seu sistema (servico interno ou outro modulo).
  - Quem recebe: backend-com (FastAPI).
  - O backend-com envia o indicador de digitacao para a API do Twilio (Typing API).

Resumo do sentido do fluxo:
- /send_message e /send_typing sao outbound: seu sistema -> backend-com -> Twilio.
- /webhook/twilio e inbound: Twilio -> backend-com (apenas recebimento).

Detalhes:
- src/atoms/whatsapp/twilio/api/v1/fastapi.py
  - Instancia TwilioClient com credenciais e from_number.
  - Encapsula resposta da API do Twilio.
- src/atoms/whatsapp/twilio/service/twilio_client.py
  - Realiza chamadas HTTP assincronas via httpx.
  - Divide mensagem acima de 1600 caracteres.
  - Suporta delivery_mode="mock" para dev.

## Tarefas Camunda

- src/atoms/whatsapp/twilio/api/v1/camunda.py
  - twilio_whatsapp_send_message
  - twilio_whatsapp_send_typing

Essas tarefas encapsulam o TwilioClient para uso em workflows Camunda.

## Dependencias

Principais dependencias:
- fastapi
- httpx
- structlog
- twilio (SDK para validar assinatura)
- pydantic

## Configuracao via env

Arquivo: src/atoms/whatsapp/twilio/config.py

Variaveis (prefixo twilio_):
- twilio_validate_twilio_signature (bool)
- twilio_twilio_auth_token (string)
- twilio_twilio_webhook_url (string)
- twilio_rate_limit_per_hour (int)
- twilio_internal_service_token (string)
- twilio_webhook_url (string) -> webhook interno que recebe o payload
- twilio_headers (dict) -> headers extras para o webhook interno

Observacao:
- validate_twilio_signature exige twilio_auth_token.
- twilio_webhook_url precisa estar configurado para enfileirar o payload.

## Regras e logica relevantes

- Se From e WaId estiverem vazios, a rota retorna 400.
- O rate limit usa janela de 1 hora e bloqueia com 429.
- O webhook responde imediatamente (TwiML vazio), sem aguardar processamento.
- delivery_mode="mock" evita chamadas reais ao Twilio.

## Pontos de integracao

- Webhook interno: usa WebhookSender em src/atoms/send_to_webhook.py.
- FastAPI app: o router e incluido em src/atoms/fastapi_app.py.
