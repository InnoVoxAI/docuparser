# Handoff para o próximo agente

## Comece por aqui
1. Leia, nesta ordem: [README.md](README.md), [decisions-pending.md](decisions-pending.md),
   [work_in_progress.md](work_in_progress.md) e [tasks.md](tasks.md).
   [findings.md](findings.md) e [target-architecture.md](target-architecture.md) servem de
   referência.
2. Rode `git status` e `git log --oneline -10`. A revisão foi feita sobre `dev` @ `36e5fd96`.
   Se o código mudou, confira as linhas citadas antes de editar.
3. Recupere contexto no basic-memory, projeto **`docuparser`** (nunca `main`). Notas-chave:
   - `decisions/Remoção do pipeline por eventos e do Camunda.md`
   - `reference/Bug conhecido- threads de fundo perdem a conexão quando o Postgres reinicia.md`
   - `reference/Revisão de arquitetura 2026-11.md` (aponta para esta pasta)
   - `Preferências de trabalho do usuário.md`

## Regras que valem aqui
- **Não implementar sem ordem explícita do usuário** ("comece a implementação"). Aprovar
  um plano não autoriza implementar. Isso está registrado como preferência dele.
- As tarefas marcadas com ⚠️ tocam prod, credenciais ou migrations. Pergunte antes.
  Agentes **não** editam segredos (guardrail do CLAUDE.md).
- O repo `innovox-kubernetes-deployments/` é **outro repositório git**, com commits e
  branches próprios.
- Testes de backend: use `run_script.sh` (ele injeta as env vars). Rode primeiro o teste
  mais específico e depois a suíte. Para suítes longas, delegue e traga só as falhas
  (CLAUDE.md, "Context hygiene").
- Exploração que toque mais de 3 arquivos vai para o subagente `code-scout`.
- Ao concluir uma tarefa: atualize [work_in_progress.md](work_in_progress.md), escreva ou
  atualize uma nota no basic-memory (`docuparser`) e, se mudou arquitetura, atualize
  `docs/architecture.md` e o CLAUDE.md (a lista de backends muda se o langextract for
  fundido).
- Commits só quando o usuário pedir, e numa branch (não em `dev` nem em `main`).

## Armadilhas conhecidas (não "consertar")
- `SuperlogicaMode.DISABLED` deixa o documento em ERP_INTEGRATION_REQUESTED. **É de
  propósito**: existe uma chave de produção e nada pode enviar por engano.
- `operations.access` **continua** como permissão do dashboard de processos e do retry de
  etapa. Não remover as checagens do front (`app/router.tsx:22`,
  `modules/processes/routes/ProcessStatsRoute.tsx:21`).
- `consume_document_received` e `consume_erp_*` **são usados** (HTTP e em processo), apesar
  do nome "consumer".
- Toda thread de fundo com ORM precisa de `close_old_connections()` no início,
  `connection.close()` no fim e `logger.exception`. Use `_with_fresh_connection`.
- Ao trocar para gunicorn (AR-04) antes da fila durável: **cada worker do gunicorn cria seu
  próprio pool de processamento.** Use 1 worker com threads até a fase 2.
- A tag de imagem em hml e prod é a 0.0.15 (`main` @ `b497651d`), que **já** não tem os
  workers de eventos (conferido no AR-11). Não há tags git: compare o commit do CI Bot no repo
  k8s ("Updating the image tag") com o `git log origin/main`.
- Os testes do backend-com **falham com 401 quando rodados pelo `run_script.sh`**: o `.env`
  injeta credenciais que ativam a autenticação. Rode-os com `uv run --frozen --all-extras
  pytest -q`, sem o `.env`, como faz o CI (22 passed em 2026-11-27).
- Afirmação incorreta de um scout, já corrigida: `process_document_view` é POST e não GET.
  O problema dele é estar sem autenticação.

## Próxima sessão (estado em 2026-11-27, 14ª sessão)

**Ritmo pedido pelo usuário:** uma AR-* por sessão, não uma fase inteira.

Já estão em `dev`: AR-01, AR-02, AR-03 (código, #73), AR-04 (imagem e compose), AR-07 (#75),
AR-20, AR-21 (#77), AR-23 (#76), AR-24, AR-25, AR-26 (código do sweeper, #78), AR-27 (#79), AR-10 (código, #80), AR-11 (docs, #81; o k8s segue em
`chore/docuparser-worker-flags-off` @ ac61b87, sem push), AR-12 (#82), AR-13 (#83) e AR-14 (#84).
**A fase 1 está encerrada.** Aguardando PR: AR-05 (k8s, `chore/docuparser-probes-resources` @ 59d1aab,
sobre o `core-release`) e o CronJob do sweeper (AR-70: k8s em `chore/docuparser-sweep-cronjob` @ f4df0d8,
e o sed da tag em `ci/ar-70-cronjob-image-tag`, neste repo).

**Fase 2 detalhada (14ª sessão)** em [tasks.md](tasks.md), na branch `docs/fase-2-fila-duravel`.
Nada foi implementado. Decisões do usuário: tabela nova `ProcessingJob` (o `OrchestrationRun` fica
como auditoria), tabela própria com SKIP LOCKED (sem lib), fila global no `public` com
`tenant_schema`, 5 tentativas reagendadas por `run_after` (30 s, 2 min, 8 min, 30 min, com jitter),
backfill `enqueue_pending_documents` no deploy, retry de etapa e reprocess na fila (202) e, no AR-33,
o status na falha definitiva e o duplicado por sha256 (advisory lock, **sem** índice único).
Ordem: AR-30 → (AR-31 ∥ AR-32) → AR-33 → AR-34 → AR-35; AR-36 no fim. Até o AR-34, tudo fica
atrás de `DOCUPARSE_PROCESSING_MODE=thread|queue` (padrão `thread`).
Achados da sessão, que o AR-33 resolve: (1) o `@task` nunca levanta exceção, então uma falha de
OCR ou de extração deixa o documento em `RECEIVED` com o run `FAILED`; (2) o duplicado é detectado
pelo nome do arquivo, sem trava. `submit_document_langextract` é código morto (sai no AR-34).
**O `erp_dispatch` nunca volta para a fila sozinho** (`max_attempts=1`; heartbeat perdido →
`ERP_FAILED`).

Como ficou o AR-14 (opções escolhidas pelo usuário):
- `camunda-workers/` e `layout-service/` apagados do disco (só `.pyc`, nunca versionados).
- `backend-core/not-used-with-s3/` **fica**: é a saída do `approved_exporter` nos testes
  locais (o `/docuparser/.env` aponta `DOCUPARSE_APPROVED_EXPORT_DIR` para ele) e está no
  `.gitignore`. Não apagar.
- `/docuparser/scripts/` saiu inteiro (experimentos de OCR, incluindo o compose do OLMOCR).
- `tests/load/simulate_module_load.py` foi consertado e roda no venv do com
  (`cd backend-com && uv run --frozen --all-extras python ../tests/load/simulate_module_load.py`).
- O `pyproject.toml` da raiz ficou sem dependências. **Não apagar o arquivo nem o
  `version`**: o `ci.yaml` lê a tag da imagem dali.
- O volume `docuparse-events` continua no compose até o D-04 ser decidido.

Como ficou o AR-13 (#83; opções escolhidas pelo usuário: nome = nome do diretório e incluir o
core): os pyprojects agora se chamam `backend-ocr`, `langextract-service` e `backend-core`
(o core também era `atoms`), com descrições corretas. Nada dependia do nome (grep em
Dockerfiles, compose, CI, `run_script.sh`, docs e repo k8s). Os `uv.lock` só mudaram o nome,
sem upgrades. O `pyproject.toml` da raiz (`name = "docuparser"`, descrição "Add your
description here") foi limpo no AR-14.

Como ficou o AR-12 (opções escolhidas pelo usuário): saíram os quatro contratos mortos
(`ocr.completed`, `ocr.failed`, `layout.classified`, `extraction.completed`), o exemplo JSON
deles, os dois scripts fake do shared e os três cenários mock do simulador de carga que
publicavam esses eventos. O `EventBus` agora só tem `publish`, e o `RedisStreamEventBus` não
lê mais nada (para depurar, `XRANGE` no redis-cli). **O `LocalJsonlEventBus` mantém
`consume`/`consume_entries` de propósito**: os testes do com, do core e do shared conferem os
eventos publicados com ele. Não remover sem trocar esses testes por outro helper.
O `simulate_module_load.py`, que já estava quebrado, foi consertado no AR-14.

Como ficou o AR-11: a 0.0.15 (hml e prod) saiu de `main` @ `b497651d`, depois da remoção dos
workers (#66). Nada em `dev` lê `DOCUPARSE_OCR_WORKER_ENABLED` /
`DOCUPARSE_EXTRACTION_WORKER_ENABLED`. A branch k8s tira as duas flags e o comentário de hml e
prod. Vale com a 0.0.15, mas vai junto no deploy final. Merge simulado com as outras três
branches k8s: sem conflito.

Como ficou o AR-10 (opções escolhidas pelo usuário: `MAXLEN ~` 10000 por env var e ConfigMap
separada no k8s):
- ocr e langextract não têm mais Redis: saíram o `RedisInstrumentor`, as dependências e, no
  compose, as env vars do barramento e o `depends_on: redis`.
- `RedisStreamEventBus.publish` usa `xadd(..., maxlen=N, approximate=True)`, com
  N = `DOCUPARSE_EVENT_STREAM_MAXLEN` (padrão 10000; `0` desliga o corte). **Ninguém lê as
  streams**: elas só guardam um histórico recente até o D-04 decidir se o publish sai.
- No k8s, `chore/docuparser-events-config` @ eae066f (sem push) cria a ConfigMap
  `docuparser-events-config`, só para core e com. **Mergear junto com a tag nova** no deploy
  final: com a imagem antiga o MAXLEN é ignorado, mas não quebra nada.

Como ficou o AR-27: o retry é opt-in (`@task(..., retry_on=...)`). Só `ocr_task` e
`extraction_task` repetem `TransientServiceError` (`ConnectTimeout`, `ConnectionError`, 429,
502, 503 e 504). O 500 e o `ReadTimeout` são permanentes: **não "conserte" o 500** sem antes
fazer o backend-ocr repassar o status real do OpenRouter.

Como ficou o AR-26: `sweep_stuck_processing` também fecha a extração presa em
`metadata.extraction.state="running"`. **Falta agendar** o CronJob a cada 10 min no repo k8s
(AR-70, perguntar antes). O manifesto de exemplo está em `docuparse-project/docs/TECHNICAL.md`
(`args: ["uv", "run", "--frozen", "python", "manage.py", "sweep_stuck_documents", ...]`).

Pendentes no repo k8s, sem push: `chore/docuparser-debug-off` @ ceebf26 (AR-03),
`chore/docuparser-core-release` (AR-04), `chore/docuparser-events-config` @ eae066f (AR-10) e
`chore/docuparser-worker-flags-off` @ ac61b87 (AR-11). As quatro mexem na `config-map.yaml` ou
no deployment do core; o merge em sequência foi simulado sem conflito.

**Deploy só no final** (pedido do usuário em 2026-11-27): nada vai para hml a cada AR. O
agente faz o commit na branch, a partir de `dev`, e o usuário abre o PR. Ao fim da sessão,
entregar um prompt pronto para a próxima tarefa.

Por onde continuar, em ordem:
1. **AR-30** (modelo `ProcessingJob`, app `jobqueue`, migration nova ⚠️). Depois AR-31 ou AR-32,
   uma por sessão, conforme o tasks.md. O deploy da fase 2 segue a ordem do AR-35.
2. **Deploy final em hml** (perguntar antes), quando o usuário disser que as modificações
   acabaram:
   a. gerar a tag a partir de `dev`. Desde o AR-21, o push em main/staging só faz o build
      se o Backend CI passar. Em emergência, use `workflow_dispatch` com `skip_tests`;
   b. com essa tag em hml, mergear `chore/docuparser-core-release` (AR-04: initContainer
      `args: ["release"]`, que quebra na 0.0.15 por falta de ENTRYPOINT),
      `chore/docuparser-debug-off` (AR-03), `chore/docuparser-events-config` (AR-10) e
      `chore/docuparser-worker-flags-off` (AR-11, este independe da tag). Na
      0.0.15 a string `"False"` ainda conta como verdadeira, então a ConfigMap do DEBUG só
      vale com a tag nova. O AR-04 e o AR-10 mexem no `envFrom`/deployment do core: confira
      os conflitos no merge;
   c. smoke em hml (login, upload, validação, `/admin/` com 404,
      `kubectl logs <pod> -c docuparser-core-release`, `XLEN document.received` no Redis
      parando perto de 10000), depois prod.
   A tabela `django_admin_log` ficou órfã: só apagar com migration e com o usuário de acordo.

Notas práticas:
- A suíte inteira do backend-core leva cerca de 30 min. Rode o teste específico e os módulos
  afetados, e deixe a suíte inteira para o CI. A do backend-ocr leva uns 20 s (16 passed, 4 skipped no AR-13).
- O hook `ruff format` do pre-commit reformata arquivos inteiros. Se ele mexer em trecho não
  relacionado, descarte essa parte e use `--no-verify` (foi o caso do commit do AR-20).
- `docker compose config` precisa de um `.env` em `docuparse-project/` (que não existe no
  container). Valide com uma cópia do compose no scratchpad mais o `/docuparser/.env`, e use
  `-p docuparse` (o `COMPOSE_PROJECT_NAME` do `.env` tem maiúscula).

## Sugestão de primeira sessão
Se o usuário mandar começar: faça a **fase 0** (AR-01, AR-02 no código do core, AR-04 no
Dockerfile e entrypoint) e o **AR-20** (CI de backend), em PRs pequenos. AR-03 e AR-05 ficam
no repo k8s, com confirmação. Ao mesmo tempo, peça ao usuário as decisões D-01 a D-03, que
destravam as fases 2 e 3.
