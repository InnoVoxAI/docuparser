# Phase 1 — Data Model

Sem novas tabelas/migrações. A feature reusa o modelo `Document` existente e
introduz **estruturas de transporte** (paginação) e **tipos de frontend**. Não há
alteração de schema de banco.

## Entidades de domínio (existentes — reuso)

### `Document` (sem mudança)
Campos relevantes já serializados por `DocumentListSerializer`: `id`, `status`,
`channel`, `original_filename`, `content_type`, `document_type`, `layout`,
`received_at`, `updated_at`, `metadata_channel`, `extraction_result`,
`rejection_notes`, `decision_date`, `approved_at`, `rejected_at`. Arquivo original
acessível por `file_uri` através do endpoint de arquivo.

## Estrutura de transporte — Paginação (backend → frontend)

Envelope retornado por `GET /documents`:

```jsonc
{
  "results": [ /* DocumentListSerializer[] (até page_size) */ ],
  "count": 137,          // total de registros que satisfazem filtros+busca
  "page": 2,             // página atual (1-based)
  "page_size": 25,       // tamanho da página aplicado (cap 25)
  "total_pages": 6       // ceil(count / page_size); 0 ou 1 quando vazio
}
```

Regras:
- `page_size` é limitado a **25** (RF-02); valores maiores são reduzidos a 25.
- `page` inválida/fora do intervalo recai de forma segura (ex.: clamp para a
  última página válida, ou página vazia com `count` correto — definir no contrato).
- `count`, `page`, `page_size`, `total_pages` sempre presentes (mesmo em lista
  vazia: `count=0`, `total_pages=0`, `results=[]`).

## Parâmetros de consulta (query) — `GET /documents`

| Param | Tipo | Default | Descrição |
|------|------|---------|-----------|
| `page` | int ≥ 1 | 1 | Página solicitada (1-based). |
| `page_size` | int 1–25 | 25 | Tamanho da página (cap 25). |
| `status` | string\|CSV | — | Um ou mais status (ex.: `APPROVED` ou `RECEIVED,OCR_COMPLETED`). |
| `tenant` | string | — | Slug do tenant (filtro já existente). |
| `search` | string | — | Busca `icontains` em nome/status/tipo/canal, **e também nos valores de `extraction_result.fields`** (+ mapeamento de rótulos de status). |

Ordenação mantida: `-received_at` (mais recentes primeiro), como hoje.

## Tipos de frontend (`src/types.ts`)

```ts
// Envelope paginado genérico (espelha o backend).
interface Paginated<T> {
  results: T[]
  count: number
  page: number
  page_size: number
  total_pages: number
}

// Parâmetros de uma requisição de listagem.
interface DocumentListParams {
  page: number
  page_size?: number          // default 25
  status?: string             // single ou CSV
  search?: string
  tenant?: string
}
```

- `api.get<Paginated<Document>>('/documents', { params })` substitui o
  `api.get<Document[]>('/documents')` atual.
- Estado de UI por tela: `page: number`, `search: string`, e o `Paginated<Document>`
  carregado. `search` alterado ⇒ `page = 1`.

## Métricas do Dashboard

Derivadas de contagens por bucket (ver research D4): `total`, `pending`,
`approved`, `failed`. Obtidas do `count` de consultas filtradas por `status`
(sem materializar os registros) — sem nova entidade persistida.

## Visualização — sem novo dado

A pré-visualização consome o **arquivo já existente** via
`GET /documents/{id}/file` (blob autenticado). Nenhum dado novo é persistido; o
`EmailModalDoc` do frontend (id, filename, channel, metadata_channel) ganha o uso
do `id` para buscar o blob de preview.
