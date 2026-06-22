# Phase 1 — Data Model: Edição e Versionamento de Campos Extraídos

Modelo de dados para o app `documents` do `backend-core` (Django + PostgreSQL). Convenções seguem `documents/models.py` (UUID PK, `TimeStampedModel`, multi-tenant via `Document.tenant`).

## Nova entidade: `ExtractionFieldVersion`

Snapshot imutável da lista de campos extraídos de um documento em um dado momento.

| Campo | Tipo | Regras / Notas |
|-------|------|----------------|
| `id` | UUID (PK) | `default=uuid.uuid4`, não editável |
| `document` | FK → `Document` | `on_delete=CASCADE`, `related_name="field_versions"` |
| `version_number` | PositiveInteger | Sequencial por documento, inicia em 1. Único por documento (ver constraints) |
| `source_type` | Char (choices) | `SourceType`: `INITIAL_EXTRACTION`, `PROCESSING`, `REPROCESSING`, `MANUAL_EDIT` (FR-011, FR-017) |
| `fields` | JSON | Snapshot completo. Formato: `{ "<nome_campo>": { "value": <str>, "confidence": <float 0..1> } }` |
| `confidence` | Float | Confiança agregada da versão (média/score de origem); default `0.0` |
| `previous_version` | FK → `self` | `null=True`, `on_delete=SET_NULL`, `related_name="next_versions"` (FR-017) |
| `created_by` | FK → `AUTH_USER_MODEL` | `null=True, blank=True`, `on_delete=PROTECT`. Preenchido em `MANUAL_EDIT` (FR-017) |
| `is_active` | Boolean | `default=False`. Exatamente uma `True` por documento (FR-014) |
| `created_at` | DateTime | de `TimeStampedModel` (FR-017: data/hora) |
| `updated_at` | DateTime | de `TimeStampedModel` |

### Constraints e índices

- `UniqueConstraint(fields=["document", "version_number"], name="unique_field_version_per_document")` — numeração sequencial sem colisão.
- `UniqueConstraint(fields=["document"], condition=Q(is_active=True), name="unique_active_field_version_per_document")` — no máximo uma versão ativa por documento (constraint parcial PostgreSQL) (FR-014).
- `Index(fields=["document", "version_number"])` — leitura ordenada do histórico.
- `Index(fields=["document", "is_active"])` — lookup rápido da versão ativa.

### Imutabilidade

- Versões nunca são atualizadas em `fields`/`source_type`/`version_number` após criadas (FR-013). O único campo que muda após criação é `is_active` (de `True`→`False` quando uma versão mais nova é ativada). Nenhuma exclusão automática (FR-016).

## Entidade existente alterada: `ExtractionResult`

Permanece como ponteiro de leitura (OneToOne com `Document`) **sincronizado com a versão ativa**.

- A cada criação/ativação de versão, `ExtractionResult.fields` e `ExtractionResult.confidence` são atualizados a partir da nova versão ativa (FR-015, FR-023).
- Campo lógico de referência: a versão ativa é sempre `document.field_versions.get(is_active=True)`. (Opcional, fora do escopo mínimo: adicionar FK `active_version` em `ExtractionResult` — não necessário, pois `is_active` já resolve.)
- Pontos que hoje fazem `update_or_create`/atribuição direta em `fields` deixam de sobrescrever e passam a chamar o serviço de versionamento (ver `services/field_versioning.py`).

## Entidades reutilizadas (sem alteração de schema)

- **`Document`**: dono das versões; `transition_to` de status permanece inalterado.
- **`ValidationDecision`**: continua registrando aprovação/rejeição. "Salvar Alterações" é independente da decisão de aprovar/rejeitar e **não** cria `ValidationDecision`; cria uma `ExtractionFieldVersion` `MANUAL_EDIT`.

## Regras de criação de versão (serviço `field_versioning.create_version`)

Entrada: `document`, `fields` (dict snapshot), `source_type`, `created_by` (opcional), `base_version` (opcional, para checagem de concorrência).

1. **Concorrência (FR-024)**: se `base_version` for informado e não for a versão ativa atual do documento → erro de conflito (não cria versão).
2. Calcular `version_number = (max(version_number do documento) or 0) + 1`.
3. Definir `previous_version = versão ativa atual` (ou `null` se for a primeira).
4. Em transação atômica:
   a. `is_active=False` na versão ativa atual (se existir).
   b. Criar nova versão com `is_active=True`.
   c. Sincronizar `ExtractionResult` (fields/confidence) com a nova versão.
5. Para `source_type=MANUAL_EDIT`: aplicar regra de confiança (FR-025/FR-027) — campos alterados/adicionados recebem `confidence=1.0`; campos inalterados mantêm a confiança da `base_version`.

### Validações de entrada

- Lista vazia ao salvar manualmente → **rejeitada** com aviso (Edge Case "Remover todos os campos"); não cria versão.
- Salvar sem alterações em relação à versão ativa → não cria versão; informa "nenhuma alteração a salvar" (Edge Case).
- Nome de campo vazio é descartado (consistente com o frontend atual, que filtra `row.name.trim()`).

## Diagrama de relacionamento (texto)

```
Document 1 ──< ExtractionFieldVersion (N)   [field_versions]
   │                  │  previous_version (self-FK, opcional)
   │                  └─ created_by → User (opcional)
   └─ 1:1 ExtractionResult  (espelho da versão ativa)
```

## Estados de uma versão

```
(criada) ─is_active=True─▶ ATIVA ──(nova versão criada)──▶ HISTÓRICA (is_active=False)
                                                              │
                                                              └─ permanece imutável e legível (FR-016, FR-022)
```
