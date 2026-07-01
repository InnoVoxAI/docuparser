# Quickstart — Edição e Versionamento de Campos Extraídos

Guia para desenvolver e validar a feature localmente. Stack: `backend-core` (Django) + `frontend` (React/Vite), via Docker Compose.

## Pré-requisitos

- Ambiente Docker Compose do projeto subindo (`docuparse-project/docker-compose.yml`).
- Pelo menos um `Document` com `ExtractionResult` (rode uma extração LangExtract pela tela de Validação para gerar dados reais).

## Subir o ambiente

```bash
cd docuparse-project
docker compose up -d
# backend-core e frontend ficam acessíveis conforme o compose
```

## Backend — onde implementar

| Arquivo | Mudança |
|---------|---------|
| `backend-core/documents/models.py` | Adicionar `ExtractionFieldVersion` (ver data-model.md) |
| `backend-core/documents/services/field_versioning.py` | NOVO — `create_version(...)`, `get_active_version(...)`, regra de confiança e concorrência |
| `backend-core/documents/serializers.py` | NOVO `ExtractionFieldVersionSerializer` |
| `backend-core/documents/views.py` | Novas views `document_save_fields_view` (PUT) e `document_field_versions_view` (GET); alterar `document_langextract_view` e `document_validation_view` para criar versões |
| `backend-core/documents/urls.py` | Rotas `documents/<uuid>/fields` e `documents/<uuid>/field-versions` |
| `backend-core/documents/migrations/` | `makemigrations` (schema + data migration de backfill) |

### Migrations

```bash
# dentro do container backend-core
python manage.py makemigrations documents
python manage.py migrate
```

A data migration de backfill cria uma versão inicial (`version_number=1`, `INITIAL_EXTRACTION`, `is_active=True`) para cada `ExtractionResult` já existente (ver research.md D8).

## Frontend — onde implementar (`frontend/src/main.jsx`)

- `LangExtractPanel`: adicionar botão **"Salvar Alterações"** abaixo da lista de campos (FR-006), abrindo um **diálogo de confirmação** (FR-007). Ao confirmar, `PUT /documents/{id}/fields` com `base_version_number` + `fields`. Exibir loading/sucesso/erro (Princípio III).
- Adicionar ação **"Visualizar Histórico"** (FR-018) que busca `GET /documents/{id}/field-versions` e mostra um modal/painel **somente leitura** com cada versão (número, tipo, data, autor) e seus campos/valores/confiança (FR-019–FR-021).
- Tratar `409 Conflict`: mostrar aviso e oferecer recarregar a versão ativa antes de reaplicar edições (FR-024).
- Campos editados/adicionados exibem confiança 100% após salvar (FR-025/FR-027).

## Testes (backend-core)

```bash
# dentro do container backend-core
python manage.py test documents.tests.test_field_versioning
python manage.py test documents.tests.test_field_versions_api
```

### Cenários mínimos de teste

**Unit (`test_field_versioning.py`)**
- Primeira versão criada como `INITIAL_EXTRACTION`, `version_number=1`, `is_active=True`.
- Nova versão desativa a anterior; só uma ativa (constraint) — FR-014.
- `previous_version` aponta para a versão anterior — FR-017.
- Edição manual: campo alterado → `confidence=1.0`; campo inalterado mantém confiança — FR-025.
- Campo adicionado → `confidence=1.0` — FR-027.
- Conflito: `base_version` desatualizada → não cria versão, sinaliza conflito — FR-024.
- Lista vazia → rejeitada (Edge Case).
- Nenhuma versão é sobrescrita/excluída — FR-013/FR-016.

**Integração (`test_field_versions_api.py`)**
- `PUT /fields` confirma → 201 + nova versão ativa + `ExtractionResult` sincronizado.
- `PUT /fields` com `base_version_number` obsoleto → 409.
- `PUT /fields` lista vazia → 422.
- `GET /field-versions` → todas as versões, desc, somente leitura, `meta.active_version_number`.
- `POST /langextract` em documento já versionado → cria `REPROCESSING`, preserva anteriores.
- `POST /validate` com `corrected_fields` → cria versão `MANUAL_EDIT`, não sobrescreve.
- Sem permissão `documents.validate` → 403 (FR-026).

## Roteiro de validação manual (mapeado aos fluxos da spec)

1. **Fluxo 1 (Editar)**: abrir Validação → editar valor de um campo → "Salvar Alterações" → confirmar → ver mensagem de sucesso e confiança 100% no campo editado.
2. **Fluxo 2 (Remover)**: remover um campo → salvar → confirmar → campo some da versão ativa; conferir no histórico que a versão anterior ainda o contém.
3. **Fluxo 3 (Histórico)**: "Visualizar Histórico" → ver todas as versões, identificáveis, somente leitura.
4. **Cancelar**: editar → "Salvar Alterações" → cancelar no diálogo → nada persistido; edições continuam na tela.
5. **Conflito (FR-024)**: editar; em paralelo disparar reprocessamento; tentar salvar → aviso de conflito; recarregar e reaplicar.

## Critérios de pronto

- Todos os FRs cobertos por testes verdes; ≥ 80% de cobertura nos arquivos tocados (Princípio II).
- Lint limpo (ruff no backend; ESLint no frontend).
- Validação manual dos 5 fluxos acima OK.
