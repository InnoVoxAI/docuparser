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
    Mantenha `COMPOSE_PROJECT_NAME=docuparse-project` para o Compose reutilizar sempre os mesmos volumes nomeados.
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

### Persistencia de dados local

Os dados locais ficam em volumes nomeados do Docker:

- `docuparse-project_postgres-data`: banco Postgres do backend-core.
- `docuparse-project_docuparse-storage`: arquivos recebidos e artefatos locais.
- `docuparse-project_minio-data`: dados do MinIO.
- `docuparse-project_redis-data`: dados persistidos do Redis.

Use `docker compose stop` para desligar temporariamente e `docker compose start` ou `docker compose up -d` para retomar. `docker compose down` remove containers e rede, mas preserva volumes. Nao use `docker compose down -v`, `docker volume prune` ou remocao manual desses volumes se quiser manter os dados.

## Observações de Desenvolvimento

- O `backend-core` executa `python manage.py migrate --noinput` antes de iniciar no compose.
- `backend-com` e `backend-core` compartilham o volume `docuparse-storage`; isso permite que o core leia arquivos recebidos por email, WhatsApp ou upload manual.
- `backend-com` publica `document.received` e sincroniza o evento com `backend-core` por `BACKEND_CORE_DOCUMENT_RECEIVED_URL`.
- O Redis interno usa `redis:6379` entre containers e expõe `6380` no host para evitar conflito com um Redis local já rodando em `6379`.
- O fluxo atual mantém `DOCUPARSE_AUTO_PROCESS_OCR=true`, portanto o OCR automático ainda é disparado pelo `backend-core` ao receber um documento.
- O profile `async-workers` prepara a virada para o pipeline por Redis Streams com serviços dedicados:

```bash
docker compose --profile async-workers up -d backend-core-events backend-ocr-worker layout-worker langextract-worker
```

- Para smoke isolado, aponte os workers para outro banco Redis sem alterar o fluxo principal:

```bash
env REDIS_URL=redis://redis:6379/13 DOCUPARSE_AUTO_PROCESS_OCR=false DOCUPARSE_OCR_WORKER_ALLOW_MOCK=true \
  docker compose --profile async-workers up -d backend-core-events backend-ocr-worker layout-worker langextract-worker
```

- Para smoke tests controlados, os workers tambem aceitam `--once`:

```bash
docker compose exec -T layout-service python -m application.run_worker --once
docker compose exec -T langextract-service python -m application.run_worker --once
```

- O `backend-ocr-worker` possui um modo de mock operacional para smoke sem API externa. Ele só é aceito quando `DOCUPARSE_OCR_WORKER_ALLOW_MOCK=true` e o evento contém `data.metadata.ocr_mock_raw_text`.
- Eventos que falham dentro dos workers sao publicados em uma dead-letter queue no padrao `<stream>.dlq`, preservando payload original, erro e origem do worker.
- Para inspecionar DLQs pelo backend-core:

```bash
docker compose exec -T backend-core python manage.py inspect_dlq --summary
docker compose exec -T backend-core python manage.py inspect_dlq --stream ocr.completed.dlq --json --limit 5
```

- Para reenfileirar um item revisado da DLQ, primeiro simule e depois execute. O registro original permanece na DLQ para auditoria; a acao publica uma trilha em `<stream>.dlq.requeued`:

```bash
docker compose exec -T backend-core python manage.py requeue_dlq --stream ocr.completed.dlq --id 1
docker compose exec -T backend-core python manage.py requeue_dlq --stream ocr.completed.dlq --id 1 --execute --note "revisado"
```

- A tela `Operacoes` tambem permite simular e reenfileirar eventos selecionados na DLQ.
- A aba `Configuracoes > OCR` persiste os campos operacionais nao sensiveis no backend-core:
  - engine por classificacao (`digital_pdf`, `scanned_image`, `handwritten_complex`);
  - engine de fallback tecnico;
  - modelo OpenRouter primario/secundario;
  - timeout, retry quando texto vier vazio e minimo de blocos de texto para PDF textual.
  - a chave OpenRouter continua no `.env` e nao e gravada no banco.
- A aba `Configuracoes > Email` persiste os campos operacionais nao sensiveis no backend-core:
  - provider, pasta monitorada, host/porta IMAP e usuario;
  - URL de webhook, tipos aceitos, tamanho maximo e remetentes bloqueados;
  - senha/app password continua fora da persistencia por enquanto.
- A aba `Configuracoes > Integracoes` persiste os campos nao sensiveis no backend-core:
  - exportacao aprovada ativa/inativa;
  - diretorio e formato do export intermediario (`json` ou `jsonl`);
  - Base URL e modo futuro da Superlogica.
  - credenciais continuam fora da persistencia por enquanto.
- Antes de usar o profile assíncrono em fluxo real, defina `DOCUPARSE_AUTO_PROCESS_OCR=false` para evitar OCR duplicado pelo caminho HTTP atual.
- A tela de configuração de WhatsApp ainda é estrutural no frontend; a persistência definitiva depende do modelo/API correspondente.

- DLQ significa Dead Letter Queue.

É uma fila onde o sistema coloca eventos que falharam ao serem processados. Em vez de perder o evento ou travar o fluxo inteiro, o sistema guarda ali:

  - o payload original;
  - qual worker tentou processar;
  - qual erro ocorreu;
  - data/hora da falha;
  - stream original.

No DocuParse, por exemplo, se um evento ocr.completed falhar no próximo passo, ele pode ir para ocr.completed.dlq.

A tela Operacoes serve para o administrador ver essas falhas, entender o motivo e, quando fizer sentido, reenfileirar o evento para tentar processar novamente.
