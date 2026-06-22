# Implementation Plan: Edição e Versionamento de Campos Extraídos

**Branch**: `007-extracted-field-versioning` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/007-extracted-field-versioning/spec.md`

## Summary

Permitir que usuários com acesso à validação editem, removam e adicionem campos extraídos de um documento, salvando as alterações de forma explícita (com confirmação) e gerando uma nova versão imutável da lista de campos a cada salvamento. O versionamento também é acionado automaticamente em cada extração/processamento/reprocessamento. Sempre há exatamente uma versão ativa (a mais recente) por documento; o histórico completo fica disponível somente para leitura.

Abordagem técnica: introduzir um novo modelo `ExtractionFieldVersion` no `backend-core` (Django) que armazena snapshots completos da lista de campos, com numeração sequencial por documento, tipo de geração, ponteiro para a versão anterior, autoria e flag de versão ativa. O atual `ExtractionResult` (OneToOne) é mantido como ponteiro de leitura para a versão ativa para preservar compatibilidade com serializers/consumidores existentes, passando a ser sempre sincronizado com a versão ativa. Os pontos que hoje sobrescrevem `ExtractionResult.fields` (`document_langextract_view` e `document_validation_view`) passam a criar versões. Adiciona-se um endpoint dedicado de "Salvar Alterações" (`PUT .../fields`) com checagem otimista de concorrência (FR-024) e um endpoint de histórico (`GET .../field-versions`). No frontend (`main.jsx`), o `LangExtractPanel`/`ValidationView` ganha botão "Salvar Alterações" com diálogo de confirmação e uma visualização de histórico somente leitura.

## Technical Context

**Language/Version**: Python 3.11+ (backend-core, Django); JavaScript/JSX (React 18 + Vite) no frontend

**Primary Dependencies**: Django + Django REST Framework, PostgreSQL (backend-core); React + Vite, axios (frontend)

**Storage**: PostgreSQL — nova tabela `documents_extractionfieldversion`; reuso de `documents_document`, `documents_extractionresult`, `documents_validationdecision`

**Testing**: pytest + Django test runner (backend-core: `documents/tests/`); sem suíte de testes JS configurada no frontend (validação manual via quickstart)

**Target Platform**: Linux server (containers Docker Compose); navegador moderno (frontend)

**Project Type**: Web (microsserviço backend-core Django + SPA React); a feature é local ao `backend-core` e ao `frontend`

**Performance Goals**: Endpoints não-processamento ≤ 200 ms p95 (constituição). Criação de versão e leitura de histórico são operações de banco simples, bem dentro do orçamento.

**Constraints**: Envelope de resposta `{ "data", "error", "meta" }`; mensagens de erro humanas e acionáveis; estados loading/success/error explícitos no frontend; multi-tenant (toda query filtrada por tenant); imutabilidade de versões (nenhuma sobrescrita/exclusão automática).

**Scale/Scope**: Volume de versões por documento esperado baixo (unidades a dezenas). Snapshot completo por versão é aceitável dado o tamanho típico das listas de campos (poucas dezenas de campos).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|-----------|-----------|--------|
| I. Code Quality | Funções ≤ 50 linhas, arquivos ≤ 400 linhas, type hints no Python, sem dead code, lint limpo (ruff/ESLint). Entrada validada nos boundaries (payload de campos, número de versão base). Sem SQL injection (ORM). | PASS |
| II. Testing Standards | Testes unitários para regra de criação de versão, versão ativa única, conflito de versão (FR-024) e confiança 100% (FR-025). Testes de integração de API para os endpoints novos (salvar/histórico) e para os pontos alterados (langextract/validate criando versão). Regressão para o comportamento de sobrescrita removido. Alvo ≥ 80% de cobertura nos arquivos tocados. | PASS |
| III. UX Consistency | Respostas seguem o envelope; termos "documento"/"extração"/"campo"/"versão" consistentes; frontend com loading/confirmação/sucesso/erro explícitos; histórico somente leitura; acessibilidade do diálogo de confirmação. | PASS |
| IV. Performance | Operações de DB simples e indexadas (índice por documento + flag ativa); muito abaixo de 200 ms p95. Sem chamadas externas no caminho de salvar/histórico. | PASS |
| Technology Standards | Usa stack travada (Django/PostgreSQL, React/Vite). Nenhum novo serviço, engine ou dependência. | PASS |

**Resultado**: PASS — nenhuma violação. Sem entradas em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
docs/specs/007-extracted-field-versioning/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 (/speckit-plan)
├── data-model.md        # Phase 1 (/speckit-plan)
├── quickstart.md        # Phase 1 (/speckit-plan)
├── contracts/           # Phase 1 (/speckit-plan)
│   └── field-versions-api.md
├── checklists/
│   └── requirements.md  # criado por /speckit-specify
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
docuparse-project/
├── backend-core/                      # Django — alvo principal da feature
│   └── documents/
│       ├── models.py                  # + ExtractionFieldVersion; sync ExtractionResult
│       ├── serializers.py             # + ExtractionFieldVersionSerializer; ajustes
│       ├── views.py                   # + save fields / history views; alterar langextract + validate
│       ├── urls.py                    # + rotas field-versions / fields
│       ├── services/
│       │   └── field_versioning.py    # NOVO — regra de criação/ativação de versão
│       ├── migrations/                # NOVA migration para ExtractionFieldVersion
│       └── tests/
│           ├── test_field_versioning.py   # NOVO — unit (serviço + regras)
│           └── test_field_versions_api.py # NOVO — integração (endpoints)
└── frontend/
    └── src/
        └── main.jsx                   # LangExtractPanel/ValidationView: "Salvar Alterações",
                                       # diálogo de confirmação, "Visualizar Histórico" (read-only)
```

**Structure Decision**: Web app multi-serviço já existente. A feature é contida no microsserviço `backend-core` (Django, app `documents`) e no SPA `frontend` (`src/main.jsx`). A lógica de versionamento é isolada em `documents/services/field_versioning.py` para manter views finas e funções ≤ 50 linhas (Princípio I). Nenhum outro serviço é afetado.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
