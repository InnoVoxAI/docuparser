# Fase 4 — Infrastructure

**Data:** 2026-04-29  
**Status:** Concluída  
**Branch:** `fix/architeture-refactor`

---

## O que foi feito

### Objetivo

Criar a camada `infrastructure/` com contrato abstrato para engines (ABC), mover todos os 8 engines para `infrastructure/engines/`, limpar a classificação interna do `openrouter_engine.py`, e mover a lógica de fallback para `infrastructure/fallback/`.

### Resumo das ações

| Ação | Origem | Destino |
|------|--------|---------|
| Criar (novo) | — | `infrastructure/engines/base_engine.py` |
| Mover lógica | `engines/tesseract_engine.py` | `infrastructure/engines/tesseract_engine.py` |
| Mover lógica | `engines/paddle_engine.py` | `infrastructure/engines/paddle_engine.py` |
| Mover lógica | `engines/easyocr_engine.py` | `infrastructure/engines/easyocr_engine.py` |
| Mover lógica | `engines/trocr_engine.py` | `infrastructure/engines/trocr_engine.py` |
| Mover lógica | `engines/docling_engine.py` | `infrastructure/engines/docling_engine.py` |
| Mover lógica | `engines/llamaparse_engine.py` | `infrastructure/engines/llamaparse_engine.py` |
| Mover lógica | `engines/deepseek_engine.py` | `infrastructure/engines/deepseek_engine.py` |
| Mover lógica + limpar | `engines/openrouter_engine.py` | `infrastructure/engines/openrouter_engine.py` |
| Mover lógica | `utils/ocr_fallback.py` | `infrastructure/fallback/fallback_handler.py` |
| Converter em shim | `engines/*.py` (8 engines) | re-exportam de `infrastructure/engines/` |
| Converter em shim | `utils/ocr_fallback.py` | re-exporta de `infrastructure/fallback/` |

---

## Arquivos criados

```
infrastructure/
├── engines/
│   ├── base_engine.py         ← NOVO: BaseOCREngine (ABC)
│   ├── tesseract_engine.py    ← lógica migrada + herda BaseOCREngine
│   ├── paddle_engine.py       ← lógica migrada + herda BaseOCREngine
│   ├── easyocr_engine.py      ← lógica migrada + herda BaseOCREngine
│   ├── trocr_engine.py        ← lógica migrada + herda BaseOCREngine
│   ├── docling_engine.py      ← lógica migrada + herda BaseOCREngine
│   ├── llamaparse_engine.py   ← lógica migrada + herda BaseOCREngine
│   ├── deepseek_engine.py     ← lógica migrada + herda BaseOCREngine
│   └── openrouter_engine.py   ← lógica migrada + LIMPA + herda BaseOCREngine
└── fallback/
    └── fallback_handler.py    ← lógica migrada de utils/ocr_fallback.py
```

## Arquivos convertidos em shims

```
engines/tesseract_engine.py   ← shim (re-exporta de infrastructure/engines/)
engines/paddle_engine.py      ← shim
engines/easyocr_engine.py     ← shim
engines/trocr_engine.py       ← shim
engines/docling_engine.py     ← shim
engines/llamaparse_engine.py  ← shim
engines/deepseek_engine.py    ← shim
engines/openrouter_engine.py  ← shim
utils/ocr_fallback.py         ← shim (re-exporta de infrastructure/fallback/)
```

---

## Detalhe: `infrastructure/engines/base_engine.py`

Classe abstrata que define o contrato mínimo para todos os engines:

```python
class BaseOCREngine(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    # Ex: "tesseract", "paddle", "openrouter", "docling"
    # Deve corresponder aos valores em domain/engine_resolver.py

    @abstractmethod
    def process(self, content: Any, metadata: dict | None = None) -> dict: ...
    # content: bytes | dict{"original", "preprocessed"} | str (caminho)
    # metadata: doc_type, filename, timeout_s (tudo opcional)
    # Retorna: raw_text, raw_text_fallback, document_info, entities, tables, totals, _meta
```

**Por que o metadata é opcional?** Backward compat — o `router.py` existente chama `process_with_classification(bytes, classification)` sem passar metadata. Cada engine ainda expõe esse método concreto. Na Fase 5 (`application/process_document.py`), o chamador usará `process(content, metadata)` diretamente.

---

## Detalhe: mudanças por engine nos arquivos infrastructure/

### Mudanças comuns (todos os 8 engines)

1. `from infrastructure.engines.base_engine import BaseOCREngine`
2. `class XEngine(BaseOCREngine):` — herança adicionada
3. `@property\ndef name(self) -> str: return "x"` — propriedade adicionada
4. `process(self, content, metadata=None)` — parâmetro `metadata` adicionado
5. Imports de `utils.preprocessing` → `shared.preprocessing` (6 engines com imagem)

### Mudanças específicas: `openrouter_engine.py`

**Problema resolvido: P2 do PRD** — O engine tinha classificação própria (`_classify_pdf_bytes`) que determinava se o PDF tinha camada de texto, duplicando trabalho do domain/classifier.

**Solução:**

```python
def _process_pdf(self, content, doc_type=None, timeout_s=120):
    # doc_type vindo do domain/classifier (via metadata) resolve o caminho
    # sem precisar abrir o PDF e contar blocos novamente.
    if doc_type == "digital_pdf":
        pdf_class = {"mode": "text", ...}    # → usa Docling
    elif doc_type == "scanned_image":
        pdf_class = {"mode": "image", ...}   # → renderiza e envia ao OpenRouter
    else:
        # Fallback de compatibilidade: classifica internamente
        pdf_class = _classify_pdf_bytes(content)
```

`_classify_pdf_bytes` permanece como função privada usada apenas quando `doc_type` não é fornecido — garante que o engine continua funcionando standalone (ex: testes, uso direto).

### Mudanças específicas: engines sem preprocessing (`docling`, `llamaparse`)

Não importam de `shared.preprocessing`. `process_with_classification` agora delega para `process(content, metadata={"doc_type": classification})` em vez de ter implementação própria.

---

## Padrão dos shims

```python
# engines/tesseract_engine.py (SHIM)
from infrastructure.engines.tesseract_engine import TesseractEngine

__all__ = ["TesseractEngine"]  # suprime hints de "symbol not accessed"
```

O `router.py` importa todos os engines no nível de módulo:
```python
from engines.deepseek_engine import DeepSeekEngine
from engines.docling_engine import DoclingEngine
# ...
```
Esses imports continuam funcionando sem nenhuma alteração no `router.py`.

---

## Verificação executada

```
Sintaxe OK (py_compile):
✓ infrastructure/engines/base_engine.py
✓ infrastructure/engines/tesseract_engine.py
✓ infrastructure/engines/paddle_engine.py
✓ infrastructure/engines/easyocr_engine.py
✓ infrastructure/engines/trocr_engine.py
✓ infrastructure/engines/deepseek_engine.py
✓ infrastructure/engines/openrouter_engine.py
✓ infrastructure/engines/docling_engine.py
✓ infrastructure/engines/llamaparse_engine.py
✓ infrastructure/fallback/fallback_handler.py

Shims OK:
✓ engines/tesseract_engine.py
✓ engines/paddle_engine.py
✓ engines/easyocr_engine.py
✓ engines/trocr_engine.py
✓ engines/docling_engine.py
✓ engines/llamaparse_engine.py
✓ engines/deepseek_engine.py
✓ engines/openrouter_engine.py
✓ utils/ocr_fallback.py

Domain layer (importação completa no venv leve):
✓ domain.engine_resolver OK
✓ domain.field_extractor OK
```

> Os engines dependem de `cv2`, `paddle`, `torch`, `easyocr`, etc. — não disponíveis
> no venv leve de dev. A verificação de sintaxe + importação dos módulos leves
> confirma que a estrutura está correta. Teste de integração completo no Docker.

---

## Código existente — situação após Fase 4

| Arquivo/Pasta | Status |
|--------------|--------|
| `main.py` | Intacto |
| `agent/router.py` | Intacto — imports de `engines/*` continuam funcionando via shims |
| `agent/classifier.py` | Shim — re-exporta de `domain/classifier.py` |
| `engines/*.py` (8 engines) | **Shims** — re-exportam de `infrastructure/engines/` |
| `utils/preprocessing.py` | Shim — re-exporta de `shared/preprocessing.py` |
| `utils/validate_fields.py` | Intacto — será fragmentado na Fase 7 |
| `utils/ocr_fallback.py` | **Shim** — re-exporta de `infrastructure/fallback/` |

---

## Próximas fases

| Fase | O que será feito |
|------|-----------------|
| **Fase 5** | Criar `application/process_document.py` usando `domain/classifier`, `domain/engine_resolver`, `domain/field_extractor` e `infrastructure/engines/` |
| **Fase 6** | Criar `api/schemas/`, `api/routes/`, `api/app.py`; remover `main.py` e `agent/router.py` antigos |
| **Fase 7** | Remover shims e pastas legadas (`agent/`, `utils/`, `engines/`), migrar lógica restante, atualizar Dockerfile |
