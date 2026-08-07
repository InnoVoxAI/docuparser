****# CLAUDE.md

## Princípios Gerais

- Carregar apenas os arquivos necessários para a tarefa atual.
- Antes de editar, checar o `git status` atual e preservar mudanças não relacionadas do usuário.
- Quando a tarefa envolver comportamento de API, rodar primeiro o teste mais específico, depois a suíte mais ampla se necessário.
- Sempre que finalizar uma tarefa lembre-se de documentar.

## Projetos
Existem 4 backends nas seguintes pastas:
backend-com: docuparse-project/backend-com
backend-core: docuparse-project/backend-core
backend-ocr: docuparse-project/backend-ocr
langextract-service: docuparse-project/langextract-service

estes dependem de código em outras pastas como:
docuparse-project/contracts
docuparse-project/layout-service
docuparse-project/shared

Existe um frontend na pasta:
docuparse-project/frontend

No arquivo docuparse-project/frontend/frontend_rules.md poderá encontrar regras a seguir para criar ou modificar código no frontend.

You can use run_script.sh with arguments to run any command to test the backend, as it injects enviroment variables.

## Geração de código
Para geração de código estamos utilizando speckit, que lê as instruções abaixo:

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at docs/specs/020-opentelemetry-tracing/plan.md
<!-- SPECKIT END -->

- Sempre que houver modificações verifique a necessidade de atualizar documentos acima descritos, ou memorias.

## Guardrails

- Não editar secrets, credenciais de produção ou arquivos listados em `.aiignore`.
- Perguntar antes de alterar migrations de banco de dados que já podem ter rodado em produção.
- Manter mudanças de formatação não relacionadas fora do patch.

## Memória Persistente do Projeto
Este projeto roda em **dev containers** que podem ser recriados a qualquer momento, apagando `~/.claude/` e `~/.basic-memory/`. Por isso, **toda memória relevante ao projeto deve ser salva dentro do próprio repositório**.

Memória de projeto é gerenciada pelo **basic-memory** (MCP server), projeto `docuparser`, com arquivos em `./memories` — dentro do repo, versionado no git.

> Nota: **Usar sempre `docuparser`**, que é o projeto correto (aponta para `./memories`
> dentro do repo) e já é o default local. Confirme com `list_memory_projects` se houver dúvida — pode existir um projeto `main` configurado apontando para fora do repo (`~/.basic-memory` ou similar); **nunca** escrever nele.

### Regras

- Ao aprender algo relevante sobre o projeto (decisões de design, bugs conhecidos, contexto de features implementadas), registre como nota no basic-memory (`write_note`), no projeto `docuparser`.
- Ao iniciar uma conversa, use `recent_activity` / `search_notes` / `build_context` do basic-memory para recuperar contexto de sessões anteriores.
- **Nunca** dependa de memória fora do repositório (`~/.claude/`, `~/.basic-memory/` sem o path fixado) — ela será perdida na recriação do container.
- Antes de recomendar algo com base numa nota antiga, confira se o que ela descreve (arquivo, função, endpoint) ainda existe no código — notas podem ficar desatualizadas.
- Organize notas por diretório temático (`decisions/`, `features/`, `reference/`) e linke notas relacionadas com `[[Título da Nota]]` em vez de duplicar conteúdo.

### Estrutura adotada

| Diretório | Conteúdo |
|---|---|
| `/` (raiz) | Visão geral do projeto, preferências do usuário |
| `decisions/` | Decisões de arquitetura/design |
| `features/` | Status e detalhes de features implementadas |
| `reference/` | Endpoints, bugs conhecidos, tabelas de referência |

Documentos normativos versionados (`datamodel_reference.md`, `business_rules.md`, `posicionamento_estrategico.md`, `business_intelligence.md`, este `CLAUDE.md`) **não** são migrados para o basic-memory — continuam como arquivos referenciados por path fixo na tabela do topo deste documento, revisados via diff/PR.

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
