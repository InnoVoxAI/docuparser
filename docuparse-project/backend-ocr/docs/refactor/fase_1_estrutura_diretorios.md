# Fase 1 — Estrutura de Diretórios

**Data:** 2026-04-29  
**Status:** Concluída  
**Branch:** `fix/architeture-refactor`

---

## O que foi feito

Esta fase criou o **esqueleto da nova arquitetura em camadas** — os diretórios e seus arquivos `__init__.py` com documentação. Nenhum código existente foi alterado, movido ou removido. A aplicação continua funcionando exatamente como antes.

---

## Diretórios e arquivos criados

```
backend-ocr/
│
├── api/                        ← NOVO: camada HTTP
│   ├── __init__.py             ← documenta responsabilidade da camada
│   ├── routes/
│   │   └── __init__.py         ← documenta o que virá (endpoints)
│   └── schemas/
│       └── __init__.py         ← documenta o que virá (modelos Pydantic)
│
├── application/                ← NOVO: camada de orquestração (Use Cases)
│   └── __init__.py             ← documenta responsabilidade da camada
│
├── domain/                     ← NOVO: regras de negócio puras
│   └── __init__.py             ← documenta o que virá (classifier, resolver, extractor)
│
├── infrastructure/             ← NOVO: integrações externas
│   ├── __init__.py             ← documenta responsabilidade da camada
│   ├── engines/
│   │   └── __init__.py         ← documenta o que virá (base_engine + 8 engines)
│   └── fallback/
│       └── __init__.py         ← documenta o que virá (fallback_handler)
│
├── shared/                     ← NOVO: utilitários reutilizáveis
│   └── __init__.py             ← documenta o que virá (preprocessing, validators)
│
└── docs/
    └── refactor/               ← NOVO: pasta de documentação do refactor
        └── fase_1_*.md         ← este arquivo
```

**Total criado:** 9 arquivos `__init__.py` + 1 markdown de summary.

---

## Código existente — situação atual

| Arquivo/Pasta | Status |
|--------------|--------|
| `main.py` | Intacto — ainda é o entrypoint da aplicação |
| `agent/router.py` | Intacto — ainda contém `route_and_process()` |
| `agent/classifier.py` | Intacto |
| `engines/*.py` (8 engines) | Intactos |
| `utils/preprocessing.py` | Intacto |
| `utils/validate_fields.py` | Intacto |
| `utils/ocr_fallback.py` | Intacto |

Verificação executada após a fase:

```
$ .venv/bin/python -c "import main; print([r.path for r in main.app.routes])"
['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/', '/engines', '/process']
```

Todas as rotas continuam registradas e funcionando.

---

## O que cada `__init__.py` documenta

Cada `__init__.py` criado contém um bloco de comentários que explica:

1. **Responsabilidade única** da camada — o que ela faz
2. **O que pertence aqui** — lista de arquivos esperados com descrição
3. **O que NÃO pertence aqui** — fronteiras explícitas para evitar mistura de responsabilidades
4. **Estado atual** — nota indicando que é placeholder e em qual fase será populado

Exemplo do `application/__init__.py`:

```python
# CAMADA: application/
# Responsabilidade ÚNICA: orquestração do fluxo de processamento.
#
# O que pertence aqui:
#   - process_document.py → o coração da aplicação.
#     def process_document(file):
#         doc_type = classifier.classify(file)      # domain/
#         engine   = resolver.get_engine(doc_type)  # domain/
#         raw_text = engine.process(file)           # infrastructure/
#         fields   = extractor.extract(raw_text)    # domain/
#         return build_response(fields, raw_text)
#
# O que NÃO pertence aqui:
#   - Regras de classificação (domain)
#   - Implementação de OCR (infrastructure)
#   - Parsing de HTTP request (api/)
```

---

## Por que começar pela estrutura?

Criar os diretórios e documentá-los antes de mover qualquer código estabelece o **contrato visual da arquitetura** — qualquer engenheiro que abrir o projeto já vê as camadas e entende onde cada tipo de código deve viver, mesmo que as pastas ainda estejam vazias.

Isso também protege o refactor nas próximas fases: ao mover um arquivo, já existe um destino documentado e sem ambiguidade.

---

## Próximas fases

| Fase | O que será feito |
|------|-----------------|
| **Fase 2** | Mover `utils/preprocessing.py` → `shared/` e extrair `shared/validators.py` de `validate_fields.py` |
| **Fase 3** | Mover `agent/classifier.py` → `domain/` e criar `domain/engine_resolver.py` e `domain/field_extractor.py` |
| **Fase 4** | Criar `infrastructure/engines/base_engine.py`, mover engines e limpar `openrouter_engine.py` |
| **Fase 5** | Criar `application/process_document.py` |
| **Fase 6** | Criar `api/` com schemas, routes e `app.py`; remover `main.py` e `router.py` antigos |
| **Fase 7** | Remover pastas legadas (`agent/`, `utils/`), atualizar imports, rodar testes |
