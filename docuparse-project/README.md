# DocuParse Experimental

Sistema para validação de extração de dados estruturados de documentos complexos.

## Arquitetura

O projeto é dividido em microserviços:

1. **frontend**: React + Vite (porta 5173)
2. **backend-com**: FastAPI de captura manual/email/WhatsApp (porta 8070)
3. **backend-core**: Django + DRF para orquestração, validação e configuração (porta 8000)
4. **backend-ocr**: FastAPI de OCR (porta 8080)
5. **layout-service**: classificação de layout (porta 8090)
6. **langextract-service**: extração estruturada (porta 8091)
7. **postgres**, **redis** e **minio** como infraestrutura local

## Como Rodar com Docker Compose

1.  Certifique-se de ter o Docker e Docker Compose instalados.
2.  Configure `OPENROUTER_API_KEY` e `OPENROUTER_MODEL` em `.env`.
3.  A partir desta pasta (`docuparse-project`), valide a configuração:

```bash
docker compose config --quiet
```

4.  Suba os serviços:

```bash
docker compose up --build
```

5.  Acesse:

```text
Frontend:       http://127.0.0.1:5173
Backend Core:   http://127.0.0.1:8000/api/ocr/health
Backend COM:    http://127.0.0.1:8070/health
Backend OCR:    http://127.0.0.1:8080/health
Layout:         http://127.0.0.1:8090/health
LangExtract:    http://127.0.0.1:8091/health
MinIO Console:  http://127.0.0.1:9001
```

6.  Para parar tudo:

```bash
docker compose down
```

## Observações de Desenvolvimento

- O `backend-core` executa `python manage.py migrate --noinput` antes de iniciar no compose.
- `backend-com` e `backend-core` compartilham o volume `docuparse-storage`; isso permite que o core leia arquivos recebidos por email, WhatsApp ou upload manual.
- `backend-com` publica `document.received` e sincroniza o evento com `backend-core` por `BACKEND_CORE_DOCUMENT_RECEIVED_URL`.
- As telas de configuração de OCR, Email, WhatsApp e Integrações ainda são estruturais no frontend; a persistência definitiva dessas áreas depende dos modelos/APIs correspondentes.
