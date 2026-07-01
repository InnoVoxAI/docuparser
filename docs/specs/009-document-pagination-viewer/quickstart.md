# Quickstart — Validação da feature 009 (Paginação + Visualização)

Como exercitar e validar a feature localmente (Docker Compose).

## Pré-requisitos

```bash
cd docuparse-project
docker compose up -d            # postgres, minio, backend-core, backend-com, frontend
```

Frontend em `http://localhost:5173/`. É necessário ter uma base com **> 25**
documentos para ver a paginação em ação (envie documentos pela tela de Upload ou
use dados de seed).

## Backend — checagens rápidas

```bash
# Listagem paginada (envelope)
curl -s "http://localhost:8000/api/ocr/documents?page=1&page_size=25" \
  -H "Authorization: Bearer <JWT>" | jq '{count, page, page_size, total_pages, n: (.results|length)}'

# Página 2
curl -s "http://localhost:8000/api/ocr/documents?page=2" -H "Authorization: Bearer <JWT>" | jq '.page'

# Busca + filtro de status
curl -s "http://localhost:8000/api/ocr/documents?search=nota&status=APPROVED" -H "Authorization: Bearer <JWT>" | jq '.count'

# Arquivo com permissão de usuário (deve responder 200)
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/ocr/documents/<id>/file" -H "Authorization: Bearer <JWT>"
```

Esperado: `page_size` nunca > 25; `count`/`total_pages` coerentes; arquivo 200
para usuário com permissão e 403 sem permissão.

## Frontend — checklist de regressão (visual + funcional)

### Paginação
- [ ] **Dashboard / Inbox / Aprovados / Rejeitados**: cada tela mostra ≤ 25
      documentos por página.
- [ ] Controles de navegação (anterior/próxima) funcionam e desabilitam nos
      limites (primeira/última página).
- [ ] Posição exibida corretamente: "Página X de Y" e total de registros.
- [ ] Buscar/filtrar retorna resultados de **todo** o conjunto e reinicia na
      página 1.
- [ ] Na aba com poucos itens (≤ 25), não há navegação além da única página.
- [ ] A atualização automática (documentos em processamento) mantém a página e os
      filtros atuais.
- [ ] Métricas do Dashboard (Total/Pendentes/Aprovados/Falhas) corretas mesmo com
      a base paginada.

### Visualização do documento original
- [ ] Clicar no olho de um registro abre o modal com as **informações já
      existentes preservadas**.
- [ ] Ao lado das informações, aparece a **pré-visualização do documento original**
      correspondente (PDF em iframe, imagem em `<img>`).
- [ ] A consulta ocorre **sem download** do arquivo.
- [ ] Todos os formatos suportados (PDF, PNG, JPG, TIFF, WebP) são exibidos;
      formato sem preview mostra mensagem amigável.
- [ ] Usuário sem permissão não visualiza o documento.
- [ ] Fechar o modal volta ao mesmo ponto da listagem (página/busca/filtros).
- [ ] Console sem novos erros/warnings.

## Testes automatizados

```bash
# Backend
docker compose exec backend-core python manage.py test documents

# Frontend (tipos + suíte + cobertura)
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run test:run
docker compose exec frontend npm run coverage
```

**Critério de sucesso**: testes de backend (paginação/busca/limites + auth do
arquivo) e a suíte do frontend (controles de paginação + preview) verdes; `tsc`
sem erros; cobertura ≥ piso; checklist visual sem divergências.

## Estado final da implementação

**Backend** (`documents/`):
- `pagination.py` (novo): `paginate_queryset` + envelope `{results, count, page, page_size, total_pages}` (cap de `page_size` = 25).
- `views.py`: `documents_inbox_view` agora pagina e aplica `status` (single/CSV),
  `tenant` e `search` server-side — `icontains` em nome/status/tipo/canal **e**
  nos valores de `extraction_result.fields` (via cast JSON→texto), com
  mapeamento de rótulos de status ("aprovado"→`APPROVED` etc.). Removido o corte
  fixo `[:200]`. `document_file_view` passou a dual-auth: token interno **ou**
  JWT do usuário + `require_permission("inbox.view")`.
- Testes: `tests/test_documents_pagination.py` (18 casos: contrato, filtros,
  busca incl. campos extraídos, e auth do arquivo) — todos verdes.

**Frontend** (`src/`):
- `types.ts`: `Paginated<T>` e `DocumentListParams`.
- `main.tsx`: hook `useDocumentPage` (estado `page`/`search` por tela, reset em 1
  ao buscar, auto-refresh preservando a página), componente `Pagination`
  reutilizável e `fetchDocumentCount` (métricas do Dashboard por bucket via
  `count`). As 4 telas (Dashboard/Inbox/Aprovados/Rejeitados) consomem páginas
  server-side; deixou de carregar a base inteira e filtrar no cliente
  (`filterDocuments`/`buildMetrics` removidos). O seletor de referência em
  Configurações ficou fora da paginação (Clarifications), mas agora também busca
  server-side (primeira página). `EmailMetadataModal` ganhou a seção
  **Documento original** (`DocumentBlobPreview`): blob autenticado →
  `URL.createObjectURL` → iframe/`<img>`/fallback, sem download, ao lado das
  informações já existentes.
- Testes: `pagination.test.tsx` (3) + preview em `flows.test.tsx` (2) — suíte com
  28 testes verdes; cobertura ~69% (linhas).

**Desvios documentados** (ver `plan.md` → Complexity Tracking): envelope
`{results, count, ...}` em vez de `{data, error, meta}` (consistência interna);
`main.tsx` permanece > 400 linhas (dívida pré-existente da 008, sem split aqui).

> Nota: a suíte de backend possui falhas **pré-existentes** (não relacionadas à
> 009) em `test_api`/`test_models`/`test_dlq`/`test_validation_view`/`test_e2e`,
> herdadas de um refactor anterior de auth/modelo (ex.: `UserProfile.Role`
> removido, testes sem autenticação). Esta feature não as introduz; ao contrário,
> corrigiu 2 testes de `test_documents_inbox_view` e o `test_document_file_*`.
