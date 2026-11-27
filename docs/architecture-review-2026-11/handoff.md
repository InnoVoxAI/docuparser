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

## Próxima sessão (estado em 2026-11-27, 5ª sessão)

**Ritmo pedido pelo usuário:** uma AR-* por sessão, não uma fase inteira.

AR-01, AR-02, AR-03 (código, #73), AR-04 (imagem e compose), AR-07 (#75), AR-20, AR-24 e
AR-25 já estão em `dev`. Na 5ª sessão foi feito o **AR-23** (output `SKIP` morto removido
de `ci.yaml`), em `ci/ar-23-remove-skip-output`, a partir de `dev`, commitado; o usuário abre o PR.

Pendentes no repo k8s, sem push: `chore/docuparser-debug-off` @ ceebf26 (AR-03) e
`chore/docuparser-core-release` (AR-04).

**Deploy só no final** (pedido do usuário em 2026-11-27): nada vai para hml a cada AR. O
agente faz o commit na branch, a partir de `dev`, e o usuário abre o PR. Ao fim da sessão,
entregar um prompt pronto para a próxima tarefa.

Por onde continuar, em ordem:
1. Fase 1, uma por sessão: **AR-21** (o build depende dos testes do AR-20), AR-26, AR-27 e
   a limpeza (AR-10..AR-14). As decisões D-01, D-02 e D-03 já foram tomadas (ver
   [decisions-pending.md](decisions-pending.md)), então as fases 2 e 3 também estão
   destravadas.
2. AR-05 (probes e resources, repo k8s, **perguntar antes**). Pode ser preparado em branch
   sem push e ir junto no deploy final.
3. **Deploy final em hml** (perguntar antes), quando o usuário disser que as modificações
   acabaram:
   a. gerar a tag a partir de `dev`;
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
