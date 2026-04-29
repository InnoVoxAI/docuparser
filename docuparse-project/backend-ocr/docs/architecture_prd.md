# PRD — Reestruturação de Arquitetura: DocuParser Backend OCR

**Versão:** 1.0  
**Data:** 2026-04-29  
**Status:** Planejamento

---

## 1. Objetivo

Reestruturar o backend de OCR do DocuParser para uma arquitetura em camadas clara, eliminando responsabilidades misturadas, lógica duplicada e arquivos monolíticos. O resultado deve ser um código que qualquer engenheiro consiga navegar em minutos, com cada componente fazendo apenas uma coisa.

---

## 2. Estado Atual (As-Is)

### 2.1 Estrutura de Diretórios Atual

```
backend-ocr/
├── main.py                      ← FastAPI app + lógica de endpoint
├── agent/
│   ├── router.py                ← MONOLITO: resolução de engine + orquestração OCR +
│   │                               extração de posições de campos + normalização de output
│   └── classifier.py            ← Classificação de documentos
├── engines/
│   ├── openrouter_engine.py     ← OCR + classificação própria (PDF texto vs PDF imagem)
│   ├── tesseract_engine.py
│   ├── paddle_engine.py
│   ├── easyocr_engine.py
│   ├── trocr_engine.py
│   ├── docling_engine.py
│   ├── llamaparse_engine.py
│   └── deepseek_engine.py
├── utils/
│   ├── preprocessing.py         ← Pipelines de pré-processamento por engine
│   ├── validate_fields.py       ← 2000+ linhas: extração + validação + scoring
│   └── ocr_fallback.py          ← Lógica de fallback entre engines
└── tests/
```

### 2.2 Fluxo Atual

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FLUXO ATUAL                                 │
└──────────────────────────────────────────────────────────────────────────┘

  HTTP POST /process
        │
        ▼
  ┌─────────────┐
  │   main.py   │  FastAPI endpoint — chama router diretamente
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                         agent/router.py                              │
  │                                                                      │
  │  route_and_process()  ◄──── FUNÇÃO PRINCIPAL QUE FAZ TUDO           │
  │  │                                                                   │
  │  ├── 1. Chama classifier.py para classificar o documento             │
  │  ├── 2. Decide qual engine usar (bloco de ifs)                       │
  │  ├── 3. Prepara o conteúdo (preprocessing)                           │
  │  ├── 4. Chama o engine (OpenRouter, Paddle, etc.)                    │
  │  ├── 5. Extrai campos críticos (validate_fields.py)                  │
  │  ├── 6. Valida campos extraídos                                      │
  │  ├── 7. Calcula score de qualidade                                   │
  │  ├── 8. Extrai campos dinâmicos                                      │
  │  ├── 9. Calcula posições dos campos no documento                     │
  │  └── 10. Normaliza e monta o response final                          │
  └──────────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────┐
  │  openrouter_engine  │  ← Também classifica internamente
  │  .py                │    (pdf com texto? pdf com imagem? imagem pura?)
  └─────────────────────┘
```

### 2.3 Problemas Identificados

| # | Problema | Onde aparece | Impacto |
|---|----------|-------------|---------|
| P1 | `router.py` faz orquestração, resolução de engine, extração de campos, posições e normalização — tudo junto | `agent/router.py` | Impossível testar partes isoladas; arquivo enorme e difícil de ler |
| P2 | `openrouter_engine.py` tem lógica de classificação própria (texto vs imagem) separada do `classifier.py` | `engines/openrouter_engine.py` | Classificação acontece duas vezes, de formas diferentes |
| P3 | `validate_fields.py` mistura extração de campos, validação de CNPJ, scoring de qualidade e decisão de LLM em 2000+ linhas | `utils/validate_fields.py` | Impossível de manter ou substituir uma parte sem afetar as outras |
| P4 | `main.py` e `router.py` são redundantes — o main só chama o router | `main.py`, `agent/router.py` | Camada desnecessária sem responsabilidade própria |
| P5 | Engines sem contrato comum (sem classe base abstrata) | `engines/*.py` | Cada engine tem interface diferente; difícil adicionar novos |
| P6 | Lógica de fallback misturada com orquestração no router | `agent/router.py`, `utils/ocr_fallback.py` | Não fica claro quando e por que o fallback é acionado |

---

## 3. Estado Alvo (To-Be)

### 3.1 Nova Estrutura de Diretórios

```
backend-ocr/
│
├── api/                            ← Camada HTTP: só recebe e devolve requests
│   ├── app.py                      ← FastAPI setup (unifica main.py + configuração)
│   ├── routes/
│   │   └── document.py             ← Endpoints: POST /process, GET /engines
│   └── schemas/
│       └── ocr_schema.py           ← OCRResponse, Transcription, etc.
│
├── application/                    ← Camada de orquestração (Use Cases)
│   └── process_document.py         ← Serviço principal: classifica → resolve → processa → extrai
│
├── domain/                         ← Regras de negócio puras
│   ├── classifier.py               ← Classificação de documentos (migrado de agent/)
│   └── engine_resolver.py          ← Strategy Pattern: doc_type → engine correto
│
├── infrastructure/                 ← Integrações externas
│   ├── engines/
│   │   ├── base_engine.py          ← Classe abstrata: contrato comum para todos os engines
│   │   ├── openrouter_engine.py    ← Limpo: só OCR, sem classificação própria
│   │   ├── tesseract_engine.py
│   │   ├── paddle_engine.py
│   │   ├── easyocr_engine.py
│   │   ├── trocr_engine.py
│   │   ├── docling_engine.py
│   │   ├── llamaparse_engine.py
│   │   └── deepseek_engine.py
│   └── fallback/
│       └── fallback_handler.py     ← Lógica de fallback isolada (vem de utils/ocr_fallback.py)
│
├── shared/                         ← Utilitários reutilizáveis
│   ├── preprocessing.py            ← Pipelines de imagem (migrado de utils/)
│   └── validators.py               ← Validações genéricas: CNPJ, moeda, datas
│
└── tests/
    ├── test_classifier.py
    ├── test_engine_resolver.py
    ├── test_process_document.py
    └── test_engines/
```

### 3.2 Novo Fluxo de Processamento

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            NOVO FLUXO                                    │
└──────────────────────────────────────────────────────────────────────────┘

  HTTP POST /process
        │
        ▼
  ┌─────────────────────────────────────┐
  │         api/routes/document.py      │
  │                                     │
  │  @router.post("/process")           │
  │  def process(file):                 │
  │      result = process_document(file)│
  │      return result                  │
  └──────────────┬──────────────────────┘
                 │  delega para o Use Case
                 ▼
  ┌─────────────────────────────────────┐
  │   application/process_document.py   │
  │                                     │
  │  def process_document(file):        │
  │    1. doc_type = classifier(file)   │
  │    2. engine = resolver(doc_type)   │
  │    3. raw = engine.process(file)    │
  │    4. fields = extractor(raw)       │
  │    5. return build_response(...)    │
  └──────┬──────────┬───────────────────┘
         │          │
         │          │ usa
         ▼          ▼
  ┌──────────┐  ┌──────────────────┐
  │ domain/  │  │ domain/          │
  │classifier│  │engine_resolver   │
  │          │  │                  │
  │ Classifica  │ Recebe doc_type  │
  │ UMA vez: │  │ e retorna o      │
  │ digital_ │  │ engine correto   │
  │ pdf      │  │ (Strategy)       │
  │ scanned_ │  └────────┬─────────┘
  │ image    │           │
  │ handwrit │           │ instancia
  └──────────┘           ▼
                  ┌──────────────────────────────────────────────────────┐
                  │              infrastructure/engines/                  │
                  │                                                        │
                  │  ┌────────────────┐   Todos implementam:              │
                  │  │  base_engine   │   process(file) → raw_text        │
                  │  │  (abstrata)    │                                    │
                  │  └───────┬────────┘                                   │
                  │          │ herda                                       │
                  │   ┌──────┴──────────────────────────────────────┐    │
                  │   │  openrouter │ paddle │ tesseract │ trocr │...│    │
                  │   └─────────────────────────────────────────────┘    │
                  └──────────────────────────────────────────────────────┘
```

### 3.3 Responsabilidades por Camada

| Camada | Arquivo(s) | Responsabilidade |
|--------|-----------|-----------------|
| **api/** | `routes/document.py` | Receber HTTP, extrair arquivo do request, devolver response |
| **api/** | `schemas/ocr_schema.py` | Modelos Pydantic de entrada e saída |
| **application/** | `process_document.py` | Orquestrar o fluxo completo: classifier → resolver → engine → extractor |
| **domain/** | `classifier.py` | Classificar documento UMA vez (digital, scanned, handwritten) |
| **domain/** | `engine_resolver.py` | Mapear `doc_type` para o engine correto (Strategy Pattern) |
| **infrastructure/engines/** | `base_engine.py` | Contrato abstrato que todos os engines implementam |
| **infrastructure/engines/** | `*_engine.py` | Executar OCR — apenas isso, sem classificação |
| **infrastructure/fallback/** | `fallback_handler.py` | Decidir quando e como acionar engine de fallback |
| **shared/** | `preprocessing.py` | Pipelines de pré-processamento de imagem reutilizáveis |
| **shared/** | `validators.py` | Validações genéricas: CNPJ checksum, moeda, datas |

---

## 4. Mapa de Migração

### 4.1 Onde cada coisa vai parar

```
╔══════════════════════════════════════════════════════════════════════════╗
║                        MAPA DE MIGRAÇÃO                                 ║
╚══════════════════════════════════════════════════════════════════════════╝

ORIGEM (atual)                        DESTINO (novo)
─────────────────────────────────────────────────────────────────────────

main.py                          ──►  api/app.py
  (FastAPI setup, CORS)               (mantém setup, sem lógica de negócio)

main.py (endpoint /process)      ──►  api/routes/document.py
  (OCRResponse, Transcription)        (schemas movidos para api/schemas/)

agent/router.py                  ──►  FRAGMENTADO em:
  _classify_document()           ──►    domain/classifier.py  (já existia)
  _resolve_engine()              ──►    domain/engine_resolver.py  (NOVO)
  route_and_process()            ──►    application/process_document.py  (NOVO)
  _normalize_output()            ──►    application/process_document.py

agent/classifier.py              ──►  domain/classifier.py
  (sem mudança de lógica,              (novo local, remove do pacote agent)
   só muda de pasta)

engines/openrouter_engine.py     ──►  infrastructure/engines/openrouter_engine.py
  (lógica OCR permanece)              + classificação interna (texto vs imagem)
  (classificação interna)        ──►    removida — usa domain/classifier.py

engines/*.py                     ──►  infrastructure/engines/*.py
  (todos os engines)                  + implementam base_engine.py

utils/preprocessing.py           ──►  shared/preprocessing.py
  (sem mudança de lógica)

utils/ocr_fallback.py            ──►  infrastructure/fallback/fallback_handler.py
```

### 4.2 O que o `router.py` vira

O `router.py` atual é o maior ponto de reestruturação. Cada responsabilidade sua vai para um lugar específico:

```
agent/router.py (ATUAL)
┌─────────────────────────────────────────────────────────┐
│  route_and_process()                                     │
│    ├── classifica                  ──►  domain/classifier│
│    ├── resolve engine              ──►  domain/resolver  │
│    ├── prepara conteúdo            ──►  application/svc  │
│    ├── chama engine                ──►  infra/engines    │
│    ├── extrai campos               ──►  domain/extractor │
│    ├── valida campos               ──►  shared/validators│
│    ├── calcula score               ──►  domain/extractor │
│    ├── extrai dinâmicos            ──►  domain/extractor │
│    ├── calcula posições            ──►  application/svc  │
│    └── normaliza output            ──►  application/svc  │
└─────────────────────────────────────────────────────────┘

application/process_document.py (NOVO)
┌─────────────────────────────────────────────────────────┐
│  process_document()                                      │
│    1. doc_type = classifier.classify(file)     ◄ domain │
│    2. engine   = resolver.get_engine(doc_type) ◄ domain │
│    3. raw_text = engine.process(file)          ◄ infra  │
│    4. return   build_response(fields, raw_text)          │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Contrato da Classe Base (Base Engine)

Todo engine deve respeitar este contrato:

```python
# infrastructure/engines/base_engine.py

from abc import ABC, abstractmethod

class BaseOCREngine(ABC):
    
    @abstractmethod
    def process(self, file_bytes: bytes, metadata: dict) -> dict:
        """
        Executa OCR no arquivo recebido.
        
        Args:
            file_bytes: Bytes do arquivo (PDF ou imagem)
            metadata:   Informações do documento (doc_type, filename, etc.)
        
        Returns:
            {
                "raw_text": str,
                "confidence": float,
                "pages": list[dict],
                "engine_used": str,
            }
        """
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador do engine (ex: 'openrouter', 'paddle')"""
        ...
```

---

## 6. Checklist de Implementação

### Fase 1 — Estrutura de Diretórios
- [ ] Criar `api/`, `api/routes/`, `api/schemas/`
- [ ] Criar `application/`
- [ ] Criar `domain/`
- [ ] Criar `infrastructure/`, `infrastructure/engines/`, `infrastructure/fallback/`
- [ ] Criar `shared/`
- [ ] Criar `__init__.py` em cada pacote

### Fase 2 — Shared (sem dependências)
- [ ] Mover `utils/preprocessing.py` → `shared/preprocessing.py`

### Fase 3 — Domain
- [ ] Mover `agent/classifier.py` → `domain/classifier.py` (sem mudança de lógica)
- [ ] Criar `domain/engine_resolver.py` com Strategy Pattern
  - Extrair lógica de `if doc_type == ...` do `router.py`
  - Registrar engines disponíveis


### Fase 4 — Infrastructure
- [ ] Criar `infrastructure/engines/base_engine.py` com ABC
- [ ] Mover todos os engines para `infrastructure/engines/`
- [ ] Atualizar `openrouter_engine.py`: remover classificação interna, usar `metadata` recebido
- [ ] Garantir que todos os engines herdam de `BaseOCREngine`
- [ ] Mover `utils/ocr_fallback.py` → `infrastructure/fallback/fallback_handler.py`

### Fase 5 — Application
- [ ] Criar `application/process_document.py`
  - Orquestrar: classify → resolve → engine.process → field_extractor.extract
  - Incorporar `_compute_field_positions()` do router
  - Incorporar `_normalize_output()` do router

### Fase 6 — API
- [ ] Criar `api/schemas/ocr_schema.py` com `OCRResponse`, `Transcription`
- [ ] Criar `api/routes/document.py` com endpoints limpos
- [ ] Criar `api/app.py` unificando `main.py` + setup FastAPI
- [ ] Remover `main.py` e `agent/router.py` antigos

### Fase 7 — Limpeza
- [ ] Remover pasta `agent/` (tudo foi migrado)
- [ ] Remover pasta `utils/` (tudo foi migrado)
- [ ] Atualizar imports em todos os arquivos
- [ ] Rodar testes e verificar que o comportamento é idêntico
- [ ] Atualizar `Dockerfile` com novo entrypoint

---

## 7. Resultado Esperado

```
ANTES                                 DEPOIS
─────────────────────────────────     ─────────────────────────────────────

router.py — 600+ linhas               process_document.py — ~50 linhas
fazendo tudo                          orchestrating tudo

openrouter classifica por conta       classificação acontece UMA vez,
própria                               em domain/classifier.py

validate_fields.py — 2000+ linhas     field_extractor.py — extração
misturando extração + validação        validators.py — validação separada

engines sem contrato comum            todos herdam BaseOCREngine

main.py redundante                    api/app.py + routes/document.py
                                      com responsabilidades claras
```

**Fluxo final:**

```
[ HTTP Request ]
      │
      ▼
[ api/routes/document.py ]         ← só HTTP
      │
      ▼
[ application/process_document.py ] ← só orquestração
      │
      ├──► [ domain/classifier.py ]      ← só classificação
      │
      ├──► [ domain/engine_resolver.py ] ← só decisão de engine
      │
      ├──► [ infra/engines/*_engine.py ] ← só OCR
      │
      └──► [ domain/field_extractor.py ] ← só extração de campos
```
