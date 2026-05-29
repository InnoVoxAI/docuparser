# Email Reader (IMAP) - Backend Com

Este documento descreve o fluxo atual de leitura de emails via IMAP no backend-com, cobrindo endpoints, daemon, dependencias e configuracao.

## Visao geral do modulo

Arquivos principais:
- src/atoms/email_reader/service/email_reader.py
- src/atoms/email_reader/api/v1/fastapi.py
- src/atoms/email_reader/api/v1/camunda.py
- src/atoms/email_reader/config.py

O modulo oferece:
- Leitura de emails nao lidos via IMAP.
- Parsing de corpo plain/HTML e anexos (incluindo imagens inline).
- Endpoint FastAPI para fetch on-demand.
- Daemon opcional que faz polling e envia anexos via webhook interno.
- Task Camunda para leitura pontual.

## Estruturas principais

Arquivo: src/atoms/email_reader/service/email_reader.py

- Attachment
  - Anexo ou imagem inline.
  - Conteudo serializado em base64 para JSON.
- ParsedEmail
  - Metadados do email e lista de anexos.
  - Campos computados: sender_email, attachment_count, inline_image_count.
- EmailReader
  - fetch_unread(): busca emails nao lidos com imap-tools.

## Endpoint FastAPI (on-demand)

Arquivo: src/atoms/email_reader/api/v1/fastapi.py

Rota:
- POST /fetch_unread
  - Parametros: host, username, password, port, ssl, folder, limit, mark_as_read
  - Retorna lista de ParsedEmail (com anexos em base64).

Fluxo:
1. Endpoint recebe credenciais e configuracao IMAP.
2. Instancia EmailReader.
3. Executa fetch_unread() e retorna os emails parseados.

## Daemon de polling (opcional)

Arquivo: src/atoms/email_reader/api/v1/fastapi.py

Quando imap_config.run_as_daemon == True:
1. Um daemon e registrado via decorator @daemon.
2. Loop infinito faz fetch_unread periodicamente.
3. Para cada email, envia cada anexo individualmente via webhook interno.
4. Usa send_using_webhook (src/atoms/send_to_webhook.py).

Observacao:
- Se webhook_url nao estiver configurado, o daemon apenas loga um warning.
- O payload enviado inclui um ParsedEmail com apenas um attachment por request.

## Task Camunda

Arquivo: src/atoms/email_reader/api/v1/camunda.py

- camunda_email_fetch_unread
  - Busca apenas 1 email (limit=1) e retorna ParsedEmail ou None.

## Dependencias

Principais dependencias:
- imap-tools
- pydantic
- fastapi
- structlog

## Configuracao via env

Arquivo: src/atoms/email_reader/config.py

Variaveis (prefixo imap_reader_):
- imap_reader_run_as_daemon (bool)
- imap_reader_host (string)
- imap_reader_username (string)
- imap_reader_password (string)
- imap_reader_port (int)
- imap_reader_ssl (bool)
- imap_reader_folder (string)
- imap_reader_limit (int)
- imap_reader_mark_as_read (bool)
- imap_reader_webhook_url (string)
- imap_reader_headers (dict)
- imap_reader_daemon_interval (int)

Hosts conhecidos (mapeamento utilitario):
- gmail, outlook, yahoo, zoho

## Regras e logica relevantes

- fetch_unread usa criterio AND(seen=False) para nao lidos.
- mark_as_read controla se marca como lido apos buscar.
- O parser coleta anexos e imagens inline via mail.obj.walk().

## Pontos de integracao

- Webhook interno: usa WebhookSender em src/atoms/send_to_webhook.py.
- FastAPI app: o router e incluido em src/atoms/fastapi_app.py.
- Daemon: registrado via src/atoms/fastapi_decorator.py.
