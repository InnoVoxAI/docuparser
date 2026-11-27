# Work in progress

Atualize a cada sessão. Estados: `todo` · `doing` · `blocked (motivo)` · `done (PR/commit)` · `dropped (motivo)`.

## Sessões
| Data | Agente | O que foi feito |
|---|---|---|
| 2026-11-26 | Claude (revisão) | Varredura completa e criação desta pasta. Nenhum código alterado. |
| 2026-11-27 | Claude | AR-01, AR-02, AR-04 (parte da imagem) e AR-20, uma branch local por tarefa a partir de `dev`. Sem push: o container não tem chave SSH do GitHub, e o `gh` não está instalado. Ver "Próxima sessão" no handoff. |
| 2026-11-27 (2ª) | Claude | PRs #67, #68, #69 e #71 já mergeados em `dev`. AR-24 em `fix/ar-24-erp-dispatch-fresh-connection` @ ec58d281 (uma AR por sessão, a pedido do usuário). |
| 2026-11-27 (3ª) | Claude | AR-24 já mergeado em `dev` local (merge 6872daea, `dev` 4 commits à frente de `origin/dev`). AR-25 em `chore/ar-25-remove-ocr-thread` @ cbf04ce6. |
| 2026-11-27 (4ª) | Claude | AR-25 já em `dev` (PR #72). AR-03: código em `fix/ar-03-debug-bool` @ dda55d1c; k8s em `chore/docuparser-debug-off` @ ceebf26 (a partir de `origin/main`). AR-07 (`/admin/` removido) em `chore/ar-07-remove-admin` @ 094ed6cd. |
| 2026-11-27 (5ª) | Claude | AR-03 e AR-07 já em `dev` (#73, #75). AR-23 em `ci/ar-23-remove-skip-output`. |
| 2026-11-27 (6ª) | Claude | AR-21 em `ci/ar-21-build-needs-tests`, a partir de `dev`. Inclui as atualizações de docs do AR-23, para os dois PRs não entrarem em conflito. |

## Estado das tarefas

| ID | Título | Estado | Nota |
|---|---|---|---|
| AR-01 | Fechar `POST /api/ocr/process` | done (PR #67) | Nenhum cliente usava: rota removida. Teste `documents/tests/test_removed_routes.py`. Suíte do core: 569 passed. |
| AR-02 | Token interno falhando fechado | done (PR #68) | Sem token: aberto só com `DEPLOYMENT_ENVIRONMENT` dev; fora disso, anônimo recebe 503 e o boot loga erro. JWT e service token como antes. "teste456" removido. hml e prod já têm o token. Testes: gate em `test_api.py` e `test_startup_config.py`; documents, users, catalog, accounting e tenants: 443 passed. |
| AR-03 | DEBUG=False em prod ⚠️ | doing (código: PR #73 em `dev`; k8s: `chore/docuparser-debug-off` @ ceebf26, sem push) | `core/env.py:env_flag`; `DEBUG` desligado por padrão, só `1/true/yes/on` ligam. Teste `core/tests/test_debug_setting.py` (18 passed, inclui import real do settings). ConfigMap hml e prod com `DEBUG: "False"`, **sem efeito até a imagem ter o fix** (na 0.0.15 "False" é verdadeiro). Nada depende de DEBUG=True além do CSS do `/admin/` (ver AR-07). Falta: smoke em hml. |
| AR-04 | gunicorn + migrations fora do boot ⚠️ | doing (imagem e compose: PR #69; falta o k8s) | gunicorn 1 worker/4 threads; entrypoint `web`/`release`; compose com `backend-core-release`. `DOCUPARSE_MIGRATE_ON_BOOT=true` por padrão porque o CI grava a tag no k8s sozinho. **Falta (repo k8s, perguntar):** initContainer `release` + `DOCUPARSE_MIGRATE_ON_BOOT=false`. Testado: imagem contra Postgres descartável e `docker compose config`; `compose up` completo não testado. |
| AR-05 | Probes e resources ⚠️ | todo | repo k8s |
| AR-06 | Segredos versionados (usuário) | dropped (D-06: ignorar) | |
| AR-07 | Destino do `/admin/` ⚠️ | done (PR #75) | Opção (a), escolhida pelo usuário: saem a rota e o app `django.contrib.admin`. Nenhuma migration depende dele (`makemigrations --check`: sem mudanças); a tabela `django_admin_log` fica órfã no schema public, inofensiva. Teste em `documents/tests/test_removed_routes.py`; users, tenants e core: 91 passed. |
| AR-10 | Redis/barramento fora de ocr e langextract + MAXLEN | todo | |
| AR-11 | Flags de worker no ConfigMap ⚠️ | todo | conferir a tag em prod |
| AR-12 | Contratos e scripts mortos | todo | |
| AR-13 | Renomear pyprojects `atoms` | todo | |
| AR-14 | Diretórios e arquivos sem uso | todo | perguntar sobre `not-used-with-s3/` e o OLMOCR |
| AR-15 | Reescrever docs/architecture.md | todo | |
| AR-16 | Docs desatualizados | todo | |
| AR-17 | Tabela de env vars | todo | |
| AR-20 | CI de backend | done (PR #71) | `.github/workflows/backend-ci.yaml`: ruff, pytest por serviço, `makemigrations --check` com Postgres. Corrigiu testes desatualizados de com e ocr. **Não validado no runner**: a simulação em ambiente limpo foi interrompida pelo reinício da máquina. O primeiro run no PR é a validação; o mais provável de falhar é o job do core (env vars que o `.env` local fornece). |
| AR-21 | Build depende dos testes | done (`ci/ar-21-build-needs-tests`, commitado, falta PR) | `backend-ci.yaml` ganhou `workflow_call`, e seu push agora só dispara em `dev`. Em main e staging os testes rodam dentro do `ci.yaml`: job `backend-tests`, com `pre-deploy` em `needs`. O grupo de concorrência inclui `github.workflow`. Válvula de escape: `workflow_dispatch` com `skip_tests` (só main/staging). Os deploys têm `if: !cancelled() && <anterior> == success`, porque o skip de um ancestral se propagaria. YAML validado com pyyaml; actionlint não rodou (bloqueado no container). **A validação real é o primeiro run no PR**: o PR mexe em `backend-ci.yaml` e dispara o Backend CI. Só mergear com ele verde, ou estar ciente de que o próximo push em main/staging fica barrado até os testes passarem (ou usar o `skip_tests`). |
| AR-22 | Tags imutáveis | todo | |
| AR-23 | Corrigir ci.yaml:18 | done (`ci/ar-23-remove-skip-output`, commitado, falta PR) | Linha removida: o output `SKIP` apontava para o step `check_version`, que não existe mais, e nenhum job o lia (grep em `.github/`). YAML validado; o comportamento do deploy não muda. |
| AR-24 | Conexões nas threads restantes | done (mergeado em `dev` local, 6872daea; falta push) | O langextract já usava `_with_fresh_connection`; faltava só `submit_erp_dispatch`. Teste novo em `test_processing_queue.py`; `test_processing_queue` e `test_erp_flow`: 44 passed. |
| AR-25 | Remover start_document_ocr_thread | done (`chore/ar-25-remove-ocr-thread` @ cbf04ce6, falta PR) | Sem chamadores (grep). Saíram também `_run_ocr_safely`, o `_tracer` do módulo e 3 imports órfãos. `manage.py check` ok; test_classification_pipeline, test_processing_queue, test_tracing_propagation e test_api: 43 passed. |
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
