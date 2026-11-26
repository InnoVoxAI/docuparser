# Work in progress

Atualize a cada sessão. Estados: `todo` · `doing` · `blocked (motivo)` · `done (PR/commit)` · `dropped (motivo)`.

## Sessões
| Data | Agente | O que foi feito |
|---|---|---|
| 2026-11-26 | Claude (revisão) | Varredura completa e criação desta pasta. Nenhum código alterado. |

## Estado das tarefas

| ID | Título | Estado | Nota |
|---|---|---|---|
| AR-01 | Fechar `POST /api/ocr/process` | todo | |
| AR-02 | Token interno falhando fechado | todo | |
| AR-03 | DEBUG=False em prod ⚠️ | todo | repo k8s |
| AR-04 | gunicorn + migrations fora do boot ⚠️ | todo | 1 worker até a fase 2 |
| AR-05 | Probes e resources ⚠️ | todo | repo k8s |
| AR-06 | Segredos versionados (usuário) | blocked (usuário) | D-06 |
| AR-10 | Redis/barramento fora de ocr e langextract + MAXLEN | todo | |
| AR-11 | Flags de worker no ConfigMap ⚠️ | todo | conferir a tag em prod |
| AR-12 | Contratos e scripts mortos | todo | |
| AR-13 | Renomear pyprojects `atoms` | todo | |
| AR-14 | Diretórios e arquivos sem uso | todo | perguntar sobre `not-used-with-s3/` e o OLMOCR |
| AR-15 | Reescrever docs/architecture.md | todo | |
| AR-16 | Docs desatualizados | todo | |
| AR-17 | Tabela de env vars | todo | |
| AR-20 | CI de backend | todo | |
| AR-21 | Build depende dos testes | todo | depende de AR-20 |
| AR-22 | Tags imutáveis | todo | |
| AR-23 | Corrigir ci.yaml:18 | todo | |
| AR-24 | Conexões nas threads restantes | todo | |
| AR-25 | Remover start_document_ocr_thread | todo | |
| AR-26 | Ampliar e agendar o sweeper | todo | paliativo |
| AR-27 | Retry classificado | todo | |
| AR-30..36 | Fila durável | blocked (D-01) | |
| AR-40 | Remover Redis | blocked (D-01, D-04) | |
| AR-50..53 | Fundir langextract | blocked (D-02) | |
| AR-54..55 | Cliente OpenRouter + custo | todo | melhor depois de D-02 |
| AR-60..62 | Entrega com → core | blocked (D-03) | AR-60 pode sair antes |
| AR-63 | Remover `_auth` morto do com | todo | |
| AR-64 | Auth no backend-ocr | todo | |
| AR-65 | Dono da classificação | blocked (D-07) | |
| AR-70..77 | Operação | todo | |
| AR-80..87 | Qualidade contínua | todo | baixa prioridade |

## Decisões
| ID | Estado |
|---|---|
| D-01 Fila durável | pendente |
| D-02 Fundir langextract | pendente |
| D-03 Entrega com → core | pendente |
| D-04 Barramento de eventos | pendente |
| D-05 Renomear operations.access | pendente |
| D-06 Segredos no repo k8s | pendente |
| D-07 Dono da classificação | pendente |
