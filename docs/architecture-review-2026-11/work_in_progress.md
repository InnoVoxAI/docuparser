# Work in progress

Atualize a cada sessão. Estados: `todo` · `doing` · `blocked (motivo)` · `done (PR/commit)` · `dropped (motivo)`.

## Sessões
| Data | Agente | O que foi feito |
|---|---|---|
| 2026-11-26 | Claude (revisão) | Varredura completa e criação desta pasta. Nenhum código alterado. |
| 2026-11-27 | Claude | AR-01, AR-02, AR-04 (parte da imagem) e AR-20, uma branch local por tarefa a partir de `dev`. Sem push: o container não tem chave SSH do GitHub, e o `gh` não está instalado. Ver "Próxima sessão" no handoff. |
| 2026-11-27 (2ª) | Claude | PRs #67, #68, #69 e #71 já mergeados em `dev`. AR-24 em `fix/ar-24-erp-dispatch-fresh-connection` @ ec58d281 (uma AR por sessão, a pedido do usuário). |

## Estado das tarefas

| ID | Título | Estado | Nota |
|---|---|---|---|
| AR-01 | Fechar `POST /api/ocr/process` | done (PR #67) | Nenhum cliente usava: rota removida. Teste `documents/tests/test_removed_routes.py`. Suíte do core: 569 passed. |
| AR-02 | Token interno falhando fechado | done (PR #68) | Sem token: aberto só com `DEPLOYMENT_ENVIRONMENT` dev; fora disso, anônimo recebe 503 e o boot loga erro. JWT e service token como antes. "teste456" removido. hml e prod já têm o token. Testes: gate em `test_api.py` e `test_startup_config.py`; documents, users, catalog, accounting e tenants: 443 passed. |
| AR-03 | DEBUG=False em prod ⚠️ | todo | repo k8s |
| AR-04 | gunicorn + migrations fora do boot ⚠️ | doing (imagem e compose: PR #69; falta o k8s) | gunicorn 1 worker/4 threads; entrypoint `web`/`release`; compose com `backend-core-release`. `DOCUPARSE_MIGRATE_ON_BOOT=true` por padrão porque o CI grava a tag no k8s sozinho. **Falta (repo k8s, perguntar):** initContainer `release` + `DOCUPARSE_MIGRATE_ON_BOOT=false`. Testado: imagem contra Postgres descartável e `docker compose config`; `compose up` completo não testado. |
| AR-05 | Probes e resources ⚠️ | todo | repo k8s |
| AR-06 | Segredos versionados (usuário) | dropped (D-06: ignorar) | |
| AR-10 | Redis/barramento fora de ocr e langextract + MAXLEN | todo | |
| AR-11 | Flags de worker no ConfigMap ⚠️ | todo | conferir a tag em prod |
| AR-12 | Contratos e scripts mortos | todo | |
| AR-13 | Renomear pyprojects `atoms` | todo | |
| AR-14 | Diretórios e arquivos sem uso | todo | perguntar sobre `not-used-with-s3/` e o OLMOCR |
| AR-15 | Reescrever docs/architecture.md | todo | |
| AR-16 | Docs desatualizados | todo | |
| AR-17 | Tabela de env vars | todo | |
| AR-20 | CI de backend | done (PR #71) | `.github/workflows/backend-ci.yaml`: ruff, pytest por serviço, `makemigrations --check` com Postgres. Corrigiu testes desatualizados de com e ocr. **Não validado no runner**: a simulação em ambiente limpo foi interrompida pelo reinício da máquina. O primeiro run no PR é a validação; o mais provável de falhar é o job do core (env vars que o `.env` local fornece). |
| AR-21 | Build depende dos testes | todo | depende de AR-20 |
| AR-22 | Tags imutáveis | todo | |
| AR-23 | Corrigir ci.yaml:18 | todo | |
| AR-24 | Conexões nas threads restantes | done (`fix/ar-24-erp-dispatch-fresh-connection` @ ec58d281, falta PR) | O langextract já usava `_with_fresh_connection`; faltava só `submit_erp_dispatch`. Teste novo em `test_processing_queue.py`; `test_processing_queue` e `test_erp_flow`: 44 passed. |
| AR-25 | Remover start_document_ocr_thread | todo | |
| AR-26 | Ampliar e agendar o sweeper | todo | paliativo |
| AR-27 | Retry classificado | todo | |
| AR-30..36 | Fila durável | todo | D-01 = A (Postgres) |
| AR-40 | Remover Redis | blocked (D-04) | |
| AR-50..53 | Fundir langextract | todo | D-02 = a |
| AR-54..55 | Cliente OpenRouter + custo | todo | melhor depois de D-02 |
| AR-60..62 | Entrega com → core | todo | D-03: AR-60/61 agora, AR-62 depois |
| AR-63 | Remover `_auth` morto do com | todo | |
| AR-64 | Auth no backend-ocr | todo | |
| AR-65 | Dono da classificação | blocked (D-07) | |
| AR-70..77 | Operação | todo | |
| AR-80..87 | Qualidade contínua | todo | baixa prioridade |

## Decisões
| ID | Estado |
|---|---|
| D-01 Fila durável | decidida: A (fila em Postgres) |
| D-02 Fundir langextract | decidida: a (fundir no backend-ocr) |
| D-03 Entrega com → core | decidida: a agora, b depois |
| D-04 Barramento de eventos | pendente |
| D-05 Renomear operations.access | pendente |
| D-06 Segredos no repo k8s | decidida: ignorar (repo de referência, no .gitignore) |
| D-07 Dono da classificação | pendente |
