# backend-com

Serviço FastAPI (porta 8070) que recebe documentos pelos canais de entrada e os entrega
ao backend-core.

## Canais

| Endpoint | Canal |
|---|---|
| `POST /api/v1/documents/manual` | Upload manual pelo frontend |
| `POST /api/v1/email/webhook`, `POST /api/v1/email/messages` | E-mail recebido por webhook |
| `POST /api/v1/email/poll` | Leitura de caixa IMAP com as configurações salvas no backend-core |
| `POST /api/v1/whatsapp/webhook`, `POST /api/v1/whatsapp/poll` | WhatsApp (Twilio) |
| `GET /health`, `GET /ready` | Probes |

## O que acontece com cada arquivo

`services/document_ingest.py`:

1. Valida o arquivo (tipo, tamanho, tenant) e grava no storage compartilhado (S3/MinIO ou disco).
2. Monta o evento `document.received` e o publica no barramento. Hoje nenhum serviço
   consome esse stream.
3. Envia o mesmo payload ao backend-core por HTTP (`BACKEND_CORE_DOCUMENT_RECEIVED_URL`).
   O core cria o documento e dispara OCR e extração.

## Testes

```bash
uv run pytest
```
