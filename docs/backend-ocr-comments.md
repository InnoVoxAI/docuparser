# Analise do backend-ocr contra as especificacoes

## Resumo executivo

O diretorio `docuparse-project/backend-ocr` avancou consideravelmente desde a analise anterior. O microservico FastAPI esta funcional e o pipeline event-driven ja foi implementado: o worker consome `document.received`, processa OCR, persiste o resultado em storage e publica `ocr.completed` ou `ocr.failed`. Os defaults de engine foram corrigidos para o perfil OpenRouter + Docling, o registry usa lazy loading com tolerancia a falhas, o `FieldExtractor` foi removido do fluxo principal, a observabilidade foi reforcada com `/ready` e logging estruturado, e a suite de testes esta bem mais abrangente.

As lacunas remanescentes sao mais localizadas: o `DoclingEngine` ainda usa `pypdfium2` em vez da biblioteca Docling real; a classificacao ainda retorna tipos internos de roteamento (`digital_pdf`, `scanned_image`, `handwritten_complex`) sem produzir o contrato `content_type` / `document_type` esperado pelo PRD; e o Docker e os `requirements` continuam instalando engines pesadas que nao fazem parte do perfil inicial.

## O que ja atende

### 1. Microservico FastAPI funcional com todos os endpoints

- `GET /`: info do servico.
- `POST /api/v1/process`: upload de arquivo para OCR sincrono.
- `GET /api/v1/engines`: lista engines com capacidades.
- `GET /health`: liveness probe.
- `GET /ready`: readiness probe — verifica se OpenRouter esta configurado quando habilitado.
- CORS configuravel via `CORS_ALLOWED_ORIGINS`.
- Handler global de excecoes: log estruturado e resposta padrao.

### 2. Arquitetura em camadas

- `api/`: camada HTTP.
- `application/`: orquestracao do processamento e worker de eventos.
- `domain/`: classificacao, resolucao de engine e extracao de campos.
- `infrastructure/`: engines OCR e fallback.
- `shared/`: preprocessing e validators.

### 3. Contrato comum de OCR engine

`infrastructure/engines/base_engine.py` define `BaseOCREngine` com interface padrao: `name`, `process(content, metadata)` retornando `raw_text`, `document_info`, `entities`, `tables`, `totals` e `_meta`.

### 4. ENGINE_DEFAULTS alinhados ao perfil inicial

Os defaults foram corrigidos:

```python
ENGINE_DEFAULTS = {
    "digital_pdf": "docling",
    "scanned_image": "openrouter",
    "handwritten_complex": "openrouter",
}
```

Imagens e PDFs escaneados agora roteiam para OpenRouter por padrao. Tesseract permanece como fallback final sempre disponivel.

### 5. Registry lazy real com tolerancia a falhas

`application/process_document.py` usa lazy loading com `try/except` por engine. Engines com dependencias ausentes ou chaves nao configuradas sao ignoradas no startup sem derrubar o servico.

### 6. OpenRouterEngine robusto

- Arvore de decisao: PDF com texto -> Docling; PDF como imagem -> renderiza + OpenRouter; Imagem -> OpenRouter.
- Recebe `doc_type` via metadata para evitar reclassificacao.
- Retry automatico para texto vazio com modelo fallback (`OPENROUTER_FALLBACK_MODEL`).
- Retry para modelos sem suporte a imagem.
- Rastreamento de confianca por pagina.

### 7. DoclingEngine funcional

Extrai texto da camada textual de PDFs via `pypdfium2` (fallback: `pymupdf`). Preserva layout por mapeamento de grade de caracteres. Detecta campos obrigatorios (data, moeda, numero de documento) e sinaliza `fallback_recommended = true` quando ausentes.

### 8. Pipeline event-driven implementado

`application/ocr_event_worker.py` e `application/run_worker.py` entregam o fluxo:

```text
document.received -> backend-ocr -> ocr.completed / ocr.failed
```

- Consome stream `document.received` (Redis Streams ou JSONL local).
- Busca arquivo no storage via `file_uri`.
- Chama `process_document()` com `legacy_extraction=False`.
- Persiste `raw_text_formatted` em object storage com chave `documents/{tenant_id}/{document_id}/ocr/raw_text.json`.
- Publica `ocr.completed` com `raw_text_uri` ou `ocr.failed` com `error_reason`.
- Dead-letter queue para eventos que falharam.
- Variaveis de controle: `DOCUPARSE_OCR_WORKER_ENABLED`, `DOCUPARSE_OCR_WORKER_POLL_SECONDS`, `DOCUPARSE_OCR_WORKER_START_AT_LATEST`.
- `POST /api/v1/process` mantido para testes isolados e reprocessamento administrativo.

### 9. FieldExtractor removido do fluxo principal

`domain/field_extractor.py` e `domain/field_extractor_impl.py` ainda existem, mas nao sao chamados no pipeline HTTP nem no worker de eventos (`semantic_extraction_enabled: False`). A extracao estruturada foi delegada ao `langextract-service`.

### 10. Storage integrado

Storage via pacote externo `docuparse_storage` (`LocalStorage`). O worker persiste `raw_text_formatted` antes de publicar `ocr.completed`, de forma que o evento carrega `raw_text_uri` em vez de payload inline.

### 11. Observabilidade reforcada

- Logging estruturado com `docuparse_observability.log_event()`.
- Campos de contexto: `tenant_id`, `document_id`, `correlation_id`, `event_type`, `engine_used`, `content_type`.
- `GET /ready` verifica OpenRouter configurado quando habilitado e docling disponivel.
- Worker thread iniciado condicionalmente via lifespan do FastAPI.

### 12. Suite de testes abrangente

```text
tests/
  test_main.py                  # endpoints FastAPI
  test_ocr_event_worker.py      # fluxo completo do worker de eventos
  test_classifier.py            # classificador (testes unitarios)
  test_process_document_bugs.py # casos de borda do pipeline
  test_ocr_flow.py              # fluxo OCR end-to-end
  test_real_pdf_ocr.py          # PDFs reais
  conftest.py                   # fixtures e configuracao
```

### 13. Preprocessing classification-aware

`shared/preprocessing.py` define pipelines por engine e por tipo de documento. Handwriting detection e region segmentation implementados. Cada engine tem funcao de preprocessing dedicada: `preprocess_for_paddle_engine`, `preprocess_for_easyocr_engine`, `preprocess_for_docling_engine`, etc.

## Lacunas remanescentes

### 1. DoclingEngine nao usa o pacote Docling real

O `DoclingEngine` atual extrai texto via `pypdfium2`, nao via a biblioteca Docling. O nome sugere Docling real, mas a implementacao e um adaptador interno baseado em pypdfium2.

Essa lacuna deve ser resolvida de forma explicita:

- Se o objetivo e manter `pypdfium2` como backend, renomear para `PdfTextEngine` ou `PypdfiumEngine` e documentar a escolha.
- Se o objetivo e usar Docling real:
  - adicionar `docling` ao `requirements.txt`;
  - reimplementar conversao via Docling para PDF e imagens;
  - registrar metadados de paginas, tabelas e layout quando disponiveis;
  - testar PDFs digitais, PDFs escaneados e imagens.

### 2. Classificacao nao produz o contrato `content_type` / `document_type` do PRD

O classificador retorna tipos internos de roteamento (`digital_pdf`, `scanned_image`, `handwritten_complex`). Esses valores sao usados corretamente para selecionar a engine, mas o contrato do evento `ocr.completed` exige:

```json
{
  "document_type": "boleto|fatura|unknown",
  "content_type": "pdf_text|scanned_pdf|image|paper_scan"
}
```

Os tipos internos nao sao publicados nesse formato. O mapeamento necessario e:

- `digital_pdf` → `content_type=pdf_text`
- `scanned_image` com PDF → `content_type=scanned_pdf`
- `scanned_image` com imagem → `content_type=image`
- documento de origem paper → `content_type=paper_scan`
- `document_type` ainda nao e inferido (retorna `unknown` por padrao)

Separar os dois conceitos no classificador ou no worker antes de publicar `ocr.completed`.

### 3. Docker e requirements incluem engines pesadas desnecessarias para o perfil inicial

O `Dockerfile` instala Tesseract, libgl e dependencias de OpenCV. O `requirements.txt` inclui `PaddleOCR`, `PaddlePaddle` e `EasyOCR`, que somam varios GB e nao fazem parte do perfil inicial OpenRouter + Docling.

Alteracoes necessarias:

- Criar requirements por perfil:

```text
requirements-base.txt              # FastAPI, pypdfium2, OpenRouter client, shared utils
requirements-openrouter-docling.txt
requirements-local-ocr.txt         # paddle, easyocr, tesseract
requirements-dev.txt               # trocr, torch, transformers
```

- No Dockerfile inicial, instalar apenas o necessario para o perfil ativo.
- Manter engines locais como extras opcionais instalados condicionalmente.

## Proposta de plano de alteracao

### Prioridade 1 - Decidir e documentar o backend do DoclingEngine

- Renomear para `PypdfiumEngine` se o backend for `pypdfium2`; ou
- Integrar Docling real se o requisito exigir.
- Atualizar `ENGINE_DEFAULTS` e `CAPABILITIES` para refletir o nome correto.

### Prioridade 2 - Produzir `content_type` e `document_type` no contrato de saida

- Separar classificacao de roteamento OCR (`digital_pdf`, `scanned_image`) de classificacao de conteudo para o pipeline (`pdf_text`, `scanned_pdf`, `image`, `paper_scan`).
- Mapear e publicar `content_type` correto no evento `ocr.completed`.
- Adicionar inferencia basica de `document_type` (boleto, fatura, unknown) a partir de sinais do texto bruto.

### Prioridade 3 - Reduzir Docker e requirements ao perfil inicial

- Criar `requirements-base.txt` e `requirements-openrouter-docling.txt`.
- Atualizar Dockerfile para instalar apenas o perfil ativo.
- Mover PaddleOCR, EasyOCR e TrOCR para extras opcionais.

## Veredito

O `backend-ocr` esta em bom estado operacional. O pipeline event-driven esta implementado, o perfil OpenRouter + Docling e o default, a extracao estruturada foi removida do fluxo principal, o storage e a observabilidade estao integrados, e os testes cobrem os fluxos criticos. As lacunas remanescentes sao objetivas e localizadas: esclarecer e potencialmente substituir o backend do `DoclingEngine`, produzir o contrato correto de `content_type` / `document_type` no evento de saida, e enxugar o Docker e os requirements para refletir o perfil inicial sem as engines pesadas.
