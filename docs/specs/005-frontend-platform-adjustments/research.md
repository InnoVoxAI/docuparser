# Research: Front-end e Ajustes de Plataforma

**Branch**: `005-frontend-platform-adjustments` | **Date**: 2026-06-15

## 1. Sessão de Autenticação — Token JWT

**Decision**: Alterar `ACCESS_TOKEN_LIFETIME` de `timedelta(minutes=15)` para `timedelta(hours=12)` em `core/settings.py`.

**Rationale**: O projeto usa `djangorestframework-simplejwt`. O acesso já está configurado via `SIMPLE_JWT` no settings. O frontend armazena `access_token` e `refresh_token` no `localStorage`. Não há lógica de auto-refresh no frontend (sem interceptor de 401), então o token de acesso expira e o usuário é deslogado. Aumentar o lifetime do access token para 12 horas é a forma mais direta de resolver o problema sem introduzir complexidade de refresh automático.

**Alternatives considered**:
- Adicionar interceptor de 401 no frontend para chamar `/token/refresh` automaticamente — introduz complexidade desnecessária, fora do escopo da feature.
- Aumentar apenas o `REFRESH_TOKEN_LIFETIME` — não resolve porque o access token continua expirando.

**File affected**: `docuparse-project/backend-core/core/settings.py` linha 41.

---

## 2. Modelos Padrão de Extração — Seed na Inicialização

**Decision**: Adicionar seeding de `nota_fiscal_default` e `conta_agua_default` ao comando `seed_data` existente.

**Rationale**: O Dockerfile do backend-core já executa `python manage.py seed_data` antes de `runserver`. Este comando é idempotente (usa `get_or_create`). Adicionar o seeding dos `SchemaConfig` padrão dentro do mesmo comando é o padrão do projeto — clean, sem nova infraestrutura. O `SchemaConfig` é scoped por `Tenant`; o tenant padrão ("default") é criado no mesmo comando, portanto estará disponível quando o seeding dos schemas rodar.

**Schema structure** (de `documents/models.py`):
- `schema_id`: identificador único por tenant (ex: `nota_fiscal_default`)
- `version`: string de versão (ex: `v1`)
- `definition`: JSONField com os campos e prompt de extração
- `is_active`: flag de ativação

**Constraint**: `UniqueConstraint(fields=["tenant", "schema_id", "version"])` garante idempotência via `get_or_create`.

**Alternatives considered**:
- Usar `AppConfig.ready()` com sinal `post_migrate` — mais complexo, o padrão do projeto é management commands.
- Criar management command separado `seed_schemas` — desnecessário, `seed_data` já cobre o caso.

**Files affected**:
- `docuparse-project/backend-core/users/management/commands/seed_data.py`

---

## 3. Abas de Configuração — Rename e Reordenação

**Decision**: Editar o array `SETTINGS_TABS` em `main.jsx` (linha 1637): renomear `'OCR referencia'` → `'Documento'` e movê-la para o índice 0 (antes de `'Modelo'`).

**Rationale**: A mudança é puramente no array de definição de tabs. Não há lógica dependente da ordem — os tabs são mapeados por `id` (não por índice) nos helpers `SETTINGS_TAB_HELP`. A navegação `goToNextStep` usa `findIndex` no array, portanto a reordenação funcionará automaticamente.

**Files affected**: `docuparse-project/frontend/src/main.jsx` linha ~1637.

---

## 4. Remoção de "Vincular layout ao schema"

**Decision**: Remover o bloco `<section>` que contém "Vincular layout ao schema" na aba `publish` (linhas 2468–2494 de `main.jsx`).

**Rationale**: A seção contém um formulário para criar `LayoutConfig`. Após remoção, o restante do conteúdo da aba `publish` ("Salvar modelo como schema") permanece intacto. O state `layoutForm` e a função `createLayout` podem ser mantidos no código para não gerar erros de dependência ou removidos — como não há outro uso deles na aba publish após a remoção, eles devem ser mantidos para evitar análise de impacto desnecessária nesta feature.

**Files affected**: `docuparse-project/frontend/src/main.jsx` linhas 2468–2494.

---

## 5. Remoção Visual de "Transcrição Completa"

**Decision**: Remover o uso do componente `<ReadOnlyTranscription>` na linha 1350 de `main.jsx`. Manter o componente `ReadOnlyTranscription` e o acesso aos dados (`full_transcription`) intactos.

**Rationale**: A linha 1350 é o único local onde `<ReadOnlyTranscription value={selectedDocument.full_transcription} />` é renderizado. Removê-la elimina a seção da UI sem afetar o armazenamento dos dados nem a função `ReadOnlyTranscriptionFormatted` (linha 1608), que deve permanecer.

**Files affected**: `docuparse-project/frontend/src/main.jsx` linha 1350.
