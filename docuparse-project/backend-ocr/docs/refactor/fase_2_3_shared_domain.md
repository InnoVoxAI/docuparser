# Fases 2 e 3 — Shared e Domain

**Data:** 2026-04-29  
**Status:** Concluídas  
**Branch:** `fix/architeture-refactor`

---

## O que foi feito

### Fase 2 — Shared (sem dependências)

Criação da camada `shared/` com utilitários genéricos extraídos de `utils/`.

| Ação | Arquivo origem | Arquivo destino |
|------|---------------|-----------------|
| Mover lógica | `utils/preprocessing.py` | `shared/preprocessing.py` |
| Converter em shim | `utils/preprocessing.py` | re-exporta de `shared/preprocessing.py` |
| Extrair validações | `utils/validate_fields.py` (lógica) | `shared/validators.py` (nova API pública) |

### Fase 3 — Domain

Criação da camada `domain/` com regras de negócio puras.

| Ação | Arquivo origem | Arquivo destino |
|------|---------------|-----------------|
| Mover lógica | `agent/classifier.py` | `domain/classifier.py` |
| Converter em shim | `agent/classifier.py` | re-exporta de `domain/classifier.py` |
| Criar (novo) | — | `domain/engine_resolver.py` — Strategy Pattern |
| Criar (novo) | — | `domain/field_extractor.py` — interface de domínio |

---

## Arquivos criados

```
shared/
├── preprocessing.py   ← lógica movida de utils/preprocessing.py (760 linhas)
└── validators.py      ← novo: validate_cnpj, parse_currency_value, is_valid_date_format

domain/
├── classifier.py      ← lógica movida de agent/classifier.py (430 linhas)
├── engine_resolver.py ← novo: EngineResolver (Strategy Pattern)
└── field_extractor.py ← novo: FieldExtractor (interface de domínio)
```

## Arquivos modificados (shims)

```
utils/preprocessing.py  ← convertido em shim (re-exporta de shared/)
agent/classifier.py     ← convertido em shim (re-exporta de domain/)
```

---

## Detalhe: o que cada arquivo novo contém

### `shared/preprocessing.py`

Cópia idêntica do conteúdo de `utils/preprocessing.py`. Inclui:
- Primitivas de imagem: `decode_image`, `encode_png_bytes`
- Operações geométricas: `deskew_simple`, `warp_perspective_if_photo`, `crop_document_roi`
- Filtros: `apply_clahe_local_contrast`, `denoise_light`, `denoise_moderate`, `sharpen_moderate`
- Segmentação: `segment_handwritten_regions`, `segment_text_lines`
- Pipelines por engine: `preprocess_for_paddle_engine`, `preprocess_for_easyocr_engine`, etc.

### `shared/validators.py`

Nova API pública de validações genéricas (extraída da lógica de `validate_fields.py`):

```python
normalize_digits(value: str) -> str
# "12.345.678/0001-95" → "12345678000195"

validate_cnpj(cnpj: str | None) -> bool
# Algoritmo Módulo 11 oficial — sequências repetidas retornam False

parse_currency_value(value: str) -> float | None
# "R$ 1.234,56" → 1234.56 | "0,00" → None

is_valid_date_format(value: str) -> bool
# "29/04/2026" → True | "invalid" → False
```

### `domain/classifier.py`

Cópia idêntica de `agent/classifier.py`. Classifica o documento **UMA única vez** no fluxo:
- `classify_document(filename, content) → str`
- Retorna: `"digital_pdf"` | `"scanned_image"` | `"handwritten_complex"`

### `domain/engine_resolver.py`

**Novo** — Strategy Pattern que substitui o bloco `if/elif` do `router.py`:

```python
class EngineResolver:
    def get_engine(classification, selected_engine=None) -> str
    def get_capabilities(classification) -> list[str]
    def list_all_engines() -> list[str]

# Instância pronta para uso:
resolver = EngineResolver()
resolve_engine(classification, selected_engine) -> str  # função de conveniência
```

Mapeamentos configuráveis:
- `ENGINE_DEFAULTS`: `digital_pdf → docling`, `scanned_image → paddle`, `handwritten_complex → handwritten_region`
- `ENGINE_ALIASES`: `paddleocr → paddle`, `llama-parse → llamaparse`, etc.
- `CAPABILITIES`: engines disponíveis por tipo (usado por `GET /engines`)

### `domain/field_extractor.py`

**Novo** — Interface de domínio que encapsula `utils/validate_fields.py`:

```python
class FieldExtractor:
    def extract(data) -> dict              # pipeline completo: extração + scoring
    def extract_candidates(raw_text) -> dict
    def extract_dynamic(data, ...) -> dict
    def should_run_llm(low_conf_fields) -> bool
    def merge_fields(...) -> tuple
    def get_fallback_engine(classification, engine) -> str | None
    field_extractor.required_fields        # ["fornecedor", "tomador", ...]

# Instância pronta para uso:
field_extractor = FieldExtractor()
```

A implementação concreta permanece em `utils/validate_fields.py` por backward compat.
Na **Fase 7**, o código será migrado para cá e `validate_fields.py` virará shim.

---

## Padrão dos shims

Ambos os shims seguem o mesmo padrão — re-export explícito com `__all__`:

```python
# utils/preprocessing.py (SHIM)
from shared.preprocessing import decode_image, encode_png_bytes, ...

__all__ = ["decode_image", "encode_png_bytes", ...]  # suprime hints de linter
```

`__all__` garante que:
- Imports existentes (`from utils.preprocessing import decode_image`) continuam funcionando
- Linters/type-checkers entendem que os símbolos são re-exports intencionais (não imports não utilizados)

---

## Código existente — situação após Fases 2 e 3

| Arquivo/Pasta | Status |
|--------------|--------|
| `main.py` | Intacto — entrypoint da aplicação |
| `agent/router.py` | Intacto — lógica preservada |
| `agent/classifier.py` | **Shim** — re-exporta de `domain/classifier.py` |
| `engines/*.py` (8 engines) | Intactos |
| `utils/preprocessing.py` | **Shim** — re-exporta de `shared/preprocessing.py` |
| `utils/validate_fields.py` | Intacto — será fragmentado na Fase 7 |
| `utils/ocr_fallback.py` | Intacto |

**Verificação executada:**

```
✓ shared.validators OK          (validate_cnpj, parse_currency_value, etc.)
✓ domain.engine_resolver OK     (get_engine, aliases, capabilities, fallback)
✓ main.py OK                    (['/process', '/engines', '/docs', ...])

Sintaxe OK:
✓ shared/preprocessing.py
✓ shared/validators.py
✓ utils/preprocessing.py (shim)
✓ domain/classifier.py
✓ domain/engine_resolver.py
✓ domain/field_extractor.py
✓ agent/classifier.py (shim)
```

> Os módulos `shared/preprocessing.py`, `domain/classifier.py` e `domain/field_extractor.py`
> dependem de `cv2`, `paddle`, `torch` etc. — não disponíveis no venv leve de dev.
> A verificação de sintaxe e a importação dos módulos leves confirma que a estrutura está correta.
> O teste de integração completo deve ser feito no ambiente Docker com todas as dependências.

---

## Próximas fases

| Fase | O que será feito |
|------|-----------------|
| **Fase 4** | Criar `infrastructure/engines/base_engine.py` (ABC), mover engines para `infrastructure/engines/`, limpar classificação interna do `openrouter_engine.py`, mover `fallback_handler.py` |
| **Fase 5** | Criar `application/process_document.py` usando `domain/classifier`, `domain/engine_resolver` e `domain/field_extractor` |
| **Fase 6** | Criar `api/schemas/`, `api/routes/`, `api/app.py`; remover `main.py` e `agent/router.py` antigos |
| **Fase 7** | Remover shims e pastas legadas (`agent/`, `utils/`), migrar lógica restante, atualizar Dockerfile |
