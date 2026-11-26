# DocuParse Experimental

Sistema para validação de extração de dados estruturados de documentos complexos.

## Arquitetura

O projeto é dividido em microserviços:

1. **frontend**: React + Vite (porta 5173)
2. **backend-com**: FastAPI de captura manual/email/WhatsApp (porta 8070)
3. **backend-core**: Django + DRF para orquestração, validação e configuração (porta 8000)
4. **backend-ocr**: FastAPI de OCR (porta 8080)
5. **langextract-service**: extração estruturada (porta 8091)
6. **postgres**, **redis** e **minio** como infraestrutura local
7. **otel-collector** e **jaeger**: coleta e visualização de rastreamento distribuído (ver [docs/TECHNICAL.md](docs/TECHNICAL.md#observabilidade-e-rastreamento-distribuído))

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
LangExtract:    http://127.0.0.1:8091/health
MinIO Console:  http://127.0.0.1:9001
Jaeger UI:      http://127.0.0.1:16686
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

### Backup em servidor proprio

Para instalacao em servidor proprio, o caminho operacional atual e manter Postgres e arquivos nos volumes Docker persistentes. S3 externo nao e necessario por enquanto; MinIO fica disponivel como servico self-hosted caso a operacao precise de object storage separado.

Gere backup local com:

```bash
./scripts/backup_local_data.sh
```

O script cria `backups/<timestamp>/` com:

- `postgres.sql`: dump logico do banco.
- `docuparse-storage.tar.gz`: documentos originais e artefatos locais.
- `docuparse-events.tar.gz`: eventos locais/auditoria em arquivo.
- `redis-data.tar.gz`: dados persistidos do Redis.
- `minio-data.tar.gz`: dados do MinIO self-hosted, se usado.

Copie esse diretorio para armazenamento externo ao servidor, por exemplo outro disco, NAS ou rotina de backup do provedor.

## Observações de Desenvolvimento

- Todos os serviços exportam traces (OpenTelemetry) para o `otel-collector`, visualizáveis no Jaeger (`http://127.0.0.1:16686`), desde que `USE_TELEMETRY=true` (padrão `false` fora do `docker-compose.yml` local — em servidores sem Collector instalado, deixe desligado). Variáveis relevantes: `USE_TELEMETRY`, `DEPLOYMENT_ENVIRONMENT` e `OTEL_TAIL_SAMPLING_PERCENTAGE` (as duas últimas com default de dev, configuráveis no `.env` — ver `.env.example`). Detalhes completos (propagação, redação de dados sensíveis, tail sampling) em [docs/TECHNICAL.md](docs/TECHNICAL.md#observabilidade-e-rastreamento-distribuído).
- O `backend-core` executa `python manage.py migrate --noinput` antes de iniciar no compose.
- `backend-com` e `backend-core` compartilham o volume `docuparse-storage`; isso permite que o core leia arquivos recebidos por email, WhatsApp ou upload manual.
- `backend-com` publica `document.received` e sincroniza o evento com `backend-core` por `BACKEND_CORE_DOCUMENT_RECEIVED_URL`.
- O Redis interno usa `redis:6379` entre containers e expõe `6380` no host para evitar conflito com um Redis local já rodando em `6379`.
- O processamento roda dentro do `backend-core`: ao receber um documento (`DOCUPARSE_AUTO_PROCESS_OCR=true`), ele chama o `backend-ocr` e o `langextract-service` por HTTP num pool de threads, com o orquestrador leve (`docuparse_orchestrator`) registrando cada etapa. O pipeline antigo por Redis Streams (workers de OCR, layout e extração e o `consume_events`) e o Camunda foram removidos. O `backend-com` ainda publica `document.received` e o core publica os eventos de ERP, mas nenhum serviço consome esses streams.
- Documentos que ficam parados no processamento são marcados como falhos pelo comando `sweep_stuck_documents` (ver [docs/TECHNICAL.md](docs/TECHNICAL.md)).
- A aba `Configuracoes > OCR` persiste os campos operacionais nao sensiveis no backend-core:
  - engine por classificacao (`digital_pdf`, `scanned_image`, `handwritten_complex`);
  - engine de fallback tecnico;
  - modelo OpenRouter primario/secundario;
  - timeout, retry quando texto vier vazio e minimo de blocos de texto para PDF textual.
  - a chave OpenRouter continua no `.env` e nao e gravada no banco.
- A aba `Configuracoes > Email` persiste os campos operacionais nao sensiveis no backend-core:
  - provider, pasta monitorada, host/porta IMAP e usuario;
  - URL de webhook, tipos aceitos, tamanho maximo e remetentes bloqueados;
  - senha/app password continua fora da persistencia e deve ser configurada no servidor com `DOCUPARSE_IMAP_PASSWORD` ou, para compatibilidade local, `imap_reader_password`.
  - o botao `Testar captura IMAP` chama `backend-com` em `POST /api/v1/email/poll`, busca as configuracoes salvas no backend-core e importa anexos aceitos como documentos.
- A aba `Configuracoes > Integracoes` persiste os campos nao sensiveis no backend-core:
  - exportacao aprovada ativa/inativa;
  - diretorio e formato do export intermediario (`json` ou `jsonl`);
  - Base URL e modo futuro da Superlogica.
  - credenciais continuam fora da persistencia por enquanto.
- A tela de configuração de WhatsApp ainda é estrutural no frontend; a persistência definitiva depende do modelo/API correspondente.
