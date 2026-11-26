# Arquitetura-alvo proposta

Princípio: **manter o monólito modular e reduzir infraestrutura.** O produto é um SaaS
multi-tenant de processamento documental para condomínios, com time pequeno. Toda peça de
infra precisa justificar o próprio custo operacional. A remoção de hoje confirmou isso:
foram três gerações de arquitetura empilhadas, e só uma estava em uso.

## 1. Componentes: fica, sai, funde, entra

| Componente | Hoje | Proposta | Por quê |
|---|---|---|---|
| frontend | React/Vite, Cloudflare Pages | **Fica** | Saudável. Só ajustes pontuais (refresh de token, lazy routes). |
| backend-core | Django, monólito modular | **Fica, e ganha um worker** | É o dono do domínio e dos dados. O processamento sai do processo web e vai para um processo worker (a mesma imagem, com outro comando). |
| backend-com | FastAPI, entrada IMAP/Twilio/manual | **Fica** | O código é específico de cada canal e tem ciclo próprio. A entrega para o core precisa virar durável (§4). |
| backend-ocr | FastAPI, motores OCR e LLM | **Fica, e absorve o langextract** | É computação sem estado e com dependências pesadas (tesseract, opencv, modelos), o que justifica um container separado. Vira o "AI/compute service": OCR e extração. |
| langextract-service | FastAPI, 574 LOC | **Funde no backend-ocr** (D-02) | Tem um único chamador, duplica o cliente OpenRouter e não tem retry. Como rota `/api/v1/extract` do backend-ocr, ganha o mesmo rate limiter e o mesmo cliente. |
| Redis | Barramento de eventos sem leitor | **Sai**, ou **fica só como broker de fila** (D-01) | Hoje acumula streams sem limite. Só se justifica se a fila escolhida for baseada em Redis. |
| `shared/docuparse_events` | publish no barramento | **Reduz** a um registro de eventos de domínio (auditoria em `DocumentEvent`) ou **sai** | O fluxo do ERP já usa as mensagens em processo. O publish no barramento não tem consumidor. |
| `contracts/events` | pydantic | **Reduz** às classes em uso | Remover as 4 classes mortas. Avaliar se o que sobra é contrato entre serviços ou só DTO interno do core. |
| `shared/docuparse_orchestrator` | runs e tasks + retry | **Fica**, com retry classificado e acoplado à fila | O rastreio de runs e tasks é útil (dashboard de processos). O retry precisa distinguir erro transitório de erro permanente. |
| `shared/docuparse_storage`, `docuparse_observability` | | **Ficam** | Têm uso real em vários serviços. |
| Postgres, MinIO/S3, OTel/Jaeger | | **Ficam** | Ganham backup (Postgres e S3) e métricas e alertas (OTel). |

## 2. Componentes que faltam

| Falta | Proposta mínima | Prioridade |
|---|---|---|
| **Fila de jobs durável** | Ver §3. Fila persistente, com worker separado, idempotência por (documento, etapa) e retry com backoff só para erros transitórios. | Alta |
| **Agendador** | k8s `CronJob`s (mesma imagem do core): `sweep_stuck_documents`, poll de IMAP e Twilio do backend-com, `reconcile_storage`. Se a fila escolhida tiver agendador embutido, usá-lo. | Alta |
| **Servidor WSGI de produção** | `gunicorn` (ou uvicorn com ASGI) no core, com `migrate_schemas` + `seed_data` num **initContainer ou Job** separado, e não no CMD. | Alta |
| **CI de backend** | Por serviço: ruff, pytest, `makemigrations --check`. Tags de imagem imutáveis (sha + versão). | Alta |
| **Rate limiter e circuit breaker do OpenRouter** | Um cliente único no backend-ocr: limite de concorrência e de taxa, backoff para 429/5xx, breaker que pausa a fila quando o provedor cai. Métrica de custo e tokens por tenant. | Média-alta |
| **Entrega durável backend-com → core** | Ver §4. | Alta |
| **Métricas e alertas** | Pipeline de métricas no otel-collector (ou Prometheus). Alertas para: fila parada, documentos presos > N min, taxa de erro do OCR, 429 do OpenRouter, pod reiniciando. | Média |
| **Backups** | `pg_dump` agendado (CronJob) com retenção. Versionamento e lifecycle no bucket S3. | Média |
| **Endurecimento k8s** | Probes, resources, `DEBUG=False`, NetworkPolicy (só o core fala com ocr e com), usuário não-root. | Alta |
| **OpenAPI** (opcional) | drf-spectacular no core para gerar os tipos do frontend. | Baixa |

## 3. Processamento: opções para a fila durável (decisão D-01)

Requisitos: sobreviver a restart, não reprocessar etapa paga já concluída, escalar
horizontalmente, funcionar com schema-por-tenant (o job carrega `tenant_schema`) e caber
num time pequeno.

| Opção | Infra nova | Prós | Contras |
|---|---|---|---|
| **A. Fila em Postgres** (procrastinate, django-q2 com ORM broker, ou uma tabela própria com `SELECT … FOR UPDATE SKIP LOCKED`) | Nenhuma | Remove o Redis. A transação do job é a mesma do documento, então o outbox sai de graça. Simples de operar. | Throughput menor (de sobra para o volume atual). |
| **B. Celery + Redis** | Redis passa a ser obrigatório | Padrão de mercado, beat embutido, muita documentação. | Mais peças. Integração com django-tenants exige cuidado (tenant-schemas-celery). Exige outbox à parte. |
| **C. Manter o pool e só endurecer** (sweeper agendado, idempotência, retry classificado) | Nenhuma | Menor mudança. | Continua perdendo trabalho em restart e não escala além de 1 réplica. Só adia o problema. |

**Recomendação: A.** O volume é de documentos de condomínio (centenas a poucos milhares
por dia), o Postgres já existe e é crítico, e a transação única elimina a classe de bug
"arquivo sem linha no banco" e "job sem documento". A tabela `OrchestrationRun/TaskExecution`
já existe e pode evoluir para servir de estado do job.

Desenho resumido (opção A):
1. O upload ou a ingestão cria o `Document` e um `ProcessingJob(step="ocr", status=queued)`
   na **mesma transação**.
2. Um worker (`manage.py run_worker`, mesma imagem, Deployment próprio) faz polling com
   `SKIP LOCKED`, troca para o schema do tenant e executa a etapa.
3. Ao concluir uma etapa, o worker grava o resultado e enfileira a próxima etapa na mesma
   transação.
4. Retry: erros transitórios (timeout, 429, 5xx) usam backoff exponencial e `max_attempts`.
   Erros permanentes vão direto para FAILED, com o motivo, e ficam visíveis no dashboard,
   onde existe o retry manual.
5. Etapa já concluída não é refeita: há idempotência por `(document_id, step)`, e o OCR
   reaproveita o texto salvo no storage.
6. Um job "em execução" com heartbeat vencido volta para a fila (isso substitui o sweeper
   para jobs; o sweeper fica para documentos legados).

## 4. Entrega backend-com → core (decisão D-03)

Hoje o backend-com grava no storage, faz XADD sem leitor e chama `POST` no core com timeout
de 2 s, sem retry. Opções:

- **(a) Retry com backoff e reconciliação.** O backend-com tenta de novo com backoff e
  marca a pendência num manifesto no storage. Um job de reconciliação no core (CronJob)
  varre o storage em busca de arquivos sem `Document`. Já existe `reconcile_storage`:
  verificar se cobre esse caso.
- **(b) Ingestão chamando o core primeiro.** O backend-com envia os bytes ao core, e o
  core grava no storage e cria o `Document` + job numa transação. O backend-com vira um
  adaptador puro de canal, sem acesso ao storage.

**Recomendação: (b)** no médio prazo, porque elimina a escrita em dois lugares. **(a)**
serve como paliativo imediato: aumentar o timeout e pôr retry já fecha a maior parte do
buraco.

## 5. Diagrama-alvo

```
 IMAP/Twilio/manual ─► backend-com (adaptador de canal) ──HTTP c/ retry──► backend-core (web, gunicorn)
                                                                            │ cria Document + Job (1 tx)
                                                                            ▼
                                                     Postgres ◄── backend-core-worker (mesma imagem)
                                                     (dados, jobs,          │  SKIP LOCKED, por tenant
                                                      runs/tasks)           ├─► backend-ocr: /process, /extract
                                                                            │     (cliente OpenRouter único,
                                                                            │      rate limit + breaker)
                                                                            └─► Superlógica (travado)
 CronJobs: sweep · polls do com · reconcile_storage · pg_dump
 OTel: traces + métricas → alertas
 Redis: removido (opção A)
```

## 6. O que deliberadamente **não** propomos

- **Não** voltar a usar um barramento de eventos nem um motor de workflow (Camunda e
  similares). O fluxo é linear e curto, e o `docs/orchestrator-poc-vs-camunda.md` já
  concluiu isso.
- **Não** quebrar o backend-core em microserviços. Os subdomínios (accounting, erp,
  payments, catalog) dividem transações e o tenant. Basta organizar melhor em apps e
  módulos (B6).
- **Não** trocar de framework (Django/FastAPI/React).
