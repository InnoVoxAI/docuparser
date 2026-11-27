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
- A tag de imagem em prod (0.0.14) pode ser anterior à remoção dos workers. Confira antes de
  tirar as flags `*_WORKER_ENABLED` (AR-11).
- Afirmação incorreta de um scout, já corrigida: `process_document_view` é POST e não GET.
  O problema dele é estar sem autenticação.

## Próxima sessão (estado em 2026-11-27, 8ª sessão)

**Ritmo pedido pelo usuário:** uma AR-* por sessão, não uma fase inteira.

Já estão em `dev`: AR-01, AR-02, AR-03 (código, #73), AR-04 (imagem e compose), AR-07 (#75),
AR-20, AR-21 (#77), AR-23 (#76), AR-24, AR-25 e AR-26 (código do sweeper, #78). Commitado e
aguardando o PR do usuário: **AR-27** (retry classificado), em `fix/ar-27-retry-classificado`.

Como ficou o AR-27 (opções A + 2 + padrão vazio, escolhidas pelo usuário):
- `@task(..., retry_on=(...))`: o retry é opt-in e o padrão `()` não repete nada. Só o
  `ocr_task` e o `extraction_task` declaram `retry_on=(TransientServiceError,)`.
- A classificação fica nos clientes do core: `documents/services/service_errors.py`
  (`request_json`). São transitórios `ConnectTimeout`, `ConnectionError`, 429, 502, 503 e
  504. O resto é permanente, **inclusive o 500 e o `ReadTimeout`**. O backend-ocr transforma
  qualquer erro do OpenRouter (até 400/401) em 500, e um `ReadTimeout` quer dizer que o OCR
  pago provavelmente já rodou. **Não "conserte" o 500 para transitório** sem antes fazer o
  backend-ocr repassar o status real (é uma melhoria possível, sem AR aberta).
- No `TaskExecution` e no `metadata.extraction`, o `error_type` passa a ser
  `TransientServiceError` ou `PermanentServiceError`, e a mensagem traz o serviço e o status
  HTTP.

Como ficou o AR-26: `sweep_stuck_processing` também fecha a extração parada em
`metadata.extraction.state="running"`. **Falta agendar**: é o CronJob a cada 10 min no repo
k8s (AR-70, perguntar antes), com o manifesto de exemplo em `docuparse-project/docs/TECHNICAL.md`
(`args: ["uv", "run", "--frozen", "python", "manage.py", "sweep_stuck_documents", ...]`).
Agende junto com a tag nova do deploy final (que leva o AR-04 e o AR-26).

O Backend CI no runner (AR-20/AR-21): confira no GitHub se o run do PR #77 passou. Se o job
do core falhou por falta de env var, conserte o `env:` do job `test-core`.

Pendentes no repo k8s, sem push: `chore/docuparser-debug-off` @ ceebf26 (AR-03) e
`chore/docuparser-core-release` (AR-04).

**Deploy só no final** (pedido do usuário em 2026-11-27): nada vai para hml a cada AR. O
agente faz o commit na branch, a partir de `dev`, e o usuário abre o PR. Ao fim da sessão,
entregar um prompt pronto para a próxima tarefa.

Por onde continuar, em ordem:
1. Fase 1, uma por sessão: a limpeza (AR-10..AR-14), começando pelo **AR-10**. As decisões D-01, D-02 e D-03 já foram tomadas (ver
   [decisions-pending.md](decisions-pending.md)), então as fases 2 e 3 também estão
   destravadas.
2. AR-05 (probes e resources) e o CronJob do sweeper (parte do AR-70), ambos no repo k8s e
   **perguntando antes**. Podem ser preparados em branch sem push e ir junto no deploy final.
3. **Deploy final em hml** (perguntar antes), quando o usuário disser que as modificações
   acabaram:
   a. gerar a tag a partir de `dev`. Desde o AR-21 o push em main/staging só faz o build
      se o Backend CI passar; em emergência use `workflow_dispatch` com `skip_tests`;
   b. com essa tag em hml, mergear `chore/docuparser-core-release` (AR-04: initContainer
      `args: ["release"]`, que quebra na 0.0.15 por falta de ENTRYPOINT) e
      `chore/docuparser-debug-off` (AR-03). Na 0.0.15 a string `"False"` ainda conta como
      verdadeira, então a ConfigMap só vale com a tag nova;
   c. smoke em hml (login, upload, validação, `/admin/` com 404;
      `kubectl logs <pod> -c docuparser-core-release`), depois prod.
   A tabela `django_admin_log` ficou órfã: só apagar com migration e com o usuário de acordo.

Notas práticas:
- A suíte inteira do backend-core leva cerca de 30 min. Rode o teste específico e os módulos
  afetados, e deixe a suíte inteira para o CI.
- O hook `ruff format` do pre-commit reformata arquivos inteiros. Se ele mexer em trecho não
  relacionado, descarte essa parte e use `--no-verify` (foi o caso do commit do AR-20).

## Sugestão de primeira sessão
Se o usuário mandar começar: faça a **fase 0** (AR-01, AR-02 no código do core, AR-04 no
Dockerfile e entrypoint) e o **AR-20** (CI de backend), em PRs pequenos. AR-03 e AR-05 ficam
no repo k8s, com confirmação. Ao mesmo tempo, peça ao usuário as decisões D-01 a D-03, que
destravam as fases 2 e 3.
