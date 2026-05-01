# Analise do backend-ocr contra as especificacoes

## Resumo executivo

O diretorio `docuparse-project/backend-ocr` esta mais proximo das especificacoes do que o `backend-com`: ja existe um microservico FastAPI funcional, com Docker de runtime, arquitetura em camadas, contrato comum de engines, endpoint `/api/v1/process`, endpoint `/api/v1/engines`, health check, testes basicos e adaptadores para OpenRouter e Docling.

Mesmo assim, ele ainda nao atende integralmente ao PRD fechado. O principal desalinhamento e que o servico ainda funciona como API HTTP sincrona de OCR + extracao de campos, enquanto a especificacao define o `backend-ocr` como modulo autonomo de OCR no pipeline distribuido por eventos:

```text
document.received -> backend-ocr -> ocr.completed -> layout-service
```

Como o LangExtract sera um microservico separado, o `backend-ocr` deve concentrar-se em classificacao basica, conversao/OCR, normalizacao de ruido e publicacao do texto bruto. A extracao de campos estruturados deve sair do caminho principal ou ficar apenas como modo legado/debug.

## O que ja atende ou pode ser reaproveitado

1. **Microservico FastAPI funcional**
   - `api/app.py` cria o app `DocuParse OCR Backend`.
   - `api/routes/document.py` expoe `POST /api/v1/process` e `GET /api/v1/engines`.
   - `GET /health` existe e os testes basicos passam.

2. **Arquitetura em camadas**
   - `api/`: camada HTTP.
   - `application/`: orquestracao do processamento.
   - `domain/`: classificacao, resolucao de engine e extracao de campos.
   - `infrastructure/`: engines OCR e fallback.
   - `shared/`: preprocessing e validators.

3. **Contrato comum de OCR engine**
   - `infrastructure/engines/base_engine.py` define `BaseOCREngine`.
   - Isso atende bem ao requisito de modulo autonomo e extensivel.

4. **OpenRouter existente**
   - `infrastructure/engines/openrouter_engine.py` implementa OCR multimodal via OpenRouter.
   - Suporta PDF com camada de texto, PDF como imagem e arquivo de imagem.
   - Para PDF com texto, delega para `DoclingEngine`; para PDF/imagem raster, renderiza imagem e chama OpenRouter.

5. **DoclingEngine existente**
   - `infrastructure/engines/docling_engine.py` extrai texto por pagina de PDFs com camada textual usando `pypdfium2`.
   - Retorna `raw_text`, metadados, blocos e tabelas heuristicas.

6. **Docker de runtime**
   - Existe `docuparse-project/backend-ocr/Dockerfile`.
   - O servico ja esta incluido no `docuparse-project/docker-compose.yml`.

7. **Testes basicos**
   - `tests/test_main.py` e `tests/test_ocr_flow.py` validam root, health e listagem de engines.
   - Rodado localmente:

```text
python -m pytest tests/test_main.py tests/test_ocr_flow.py -q
5 passed
```

## Lacunas em relacao as especificacoes

### 1. Falta operacao por eventos e filas

O PRD define comunicacao normal entre modulos por fila/event bus. O `backend-ocr` atual so oferece API HTTP sincrona para upload direto de arquivo.

Alteracoes necessarias:

- Criar consumidor de `document.received`.
- Buscar o arquivo pelo `file_uri` publicado pelo `backend-com`.
- Processar OCR.
- Armazenar `raw_text` e artefatos em storage.
- Publicar `ocr.completed` ou `ocr.failed`.
- Manter `POST /api/v1/process` apenas para testes isolados, reprocessamento administrativo e chamadas futuras externas.

Evento esperado de entrada:

```json
{
  "event": "document.received",
  "version": "v1",
  "document_id": "uuid",
  "tenant_id": "uuid",
  "source": "email|whatsapp|manual|watched_folder",
  "file_uri": "s3://bucket/file.pdf",
  "metadata": {},
  "correlation_id": "uuid"
}
```

Evento esperado de saida:

```json
{
  "event": "ocr.completed",
  "version": "v1",
  "document_id": "uuid",
  "tenant_id": "uuid",
  "raw_text_uri": "s3://bucket/raw_text.json",
  "document_type": "boleto|fatura|unknown",
  "content_type": "pdf_text|scanned_pdf|image|paper_scan",
  "engine_used": "openrouter|docling",
  "confidence": 0.91,
  "correlation_id": "uuid"
}
```

### 2. O fluxo inicial OpenRouter + Docling precisa virar default explicito

Voce definiu que, inicialmente, usaremos OCR do OpenRouter e Docling para conversao dos PDFs e imagens. Hoje o resolver default e:

```python
ENGINE_DEFAULTS = {
    "digital_pdf": "docling",
    "scanned_image": "paddle",
    "handwritten_complex": "handwritten_region",
}
```

Isso significa que imagens/PDFs escaneados nao usam OpenRouter por padrao.

Alteracoes necessarias:

- Alterar defaults iniciais para:

```python
ENGINE_DEFAULTS = {
    "digital_pdf": "docling",
    "scanned_image": "openrouter",
    "handwritten_complex": "openrouter",
}
```

- Adicionar feature flag, por exemplo:

```text
OCR_INITIAL_ENGINE_PROFILE=openrouter_docling
OCR_ENABLE_LEGACY_ENGINES=false
```

- Permitir override por `selected_engine`, mas validar contra engines realmente habilitados.
- Atualizar `CAPABILITIES` para incluir `openrouter`, `docling` e os aliases corretos.

### 3. DoclingEngine nao usa o pacote Docling real

O arquivo chama `DoclingEngine`, mas a implementacao atual usa `pypdfium2` para extrair texto do PDF. Isso pode ser aceitavel como adaptador interno, mas se a especificacao "docling" significa usar a biblioteca Docling real para conversao de PDFs e imagens, falta incluir e integrar essa dependencia.

Alteracoes necessarias:

- Decidir explicitamente se `DoclingEngine` e:
  - um adaptador interno baseado em `pypdfium2`; ou
  - um wrapper da biblioteca Docling real.
- Se for Docling real:
  - adicionar dependencia no `requirements.txt`;
  - implementar conversao via Docling para PDF e imagens;
  - registrar metadados de paginas, tabelas e layout quando disponiveis;
  - testar PDFs digitais, PDFs escaneados e imagens.

### 4. O backend-ocr ainda extrai campos estruturados

`application/process_document.py` chama `FieldExtractor()` e retorna `fields`, `field_confidence`, `low_confidence_fields`, `totals`, etc. Essa responsabilidade conflita com a arquitetura fechada, onde:

- `backend-ocr`: texto bruto, normalizacao e classificacao basica.
- `layout-service`: classificacao de layout.
- `langextract-service`: extracao semantica estruturada.

Alteracoes necessarias:

- Remover `FieldExtractor` do fluxo principal de OCR.
- Retornar apenas OCR e metadados necessarios para o layout-service.
- Manter extracao de campos apenas como modo legado, por exemplo `?legacy_extract_fields=true`, se ainda for necessaria para compatibilidade.
- Ajustar schema de resposta para nao prometer campos estruturados como saida principal.

### 5. Classificacao atual nao produz os tipos exigidos pelo PRD

O PRD espera:

- `document_type`: `boleto | fatura | unknown`
- `content_type`: `pdf_text | scanned_pdf | image | paper_scan`

O classificador atual retorna:

- `digital_pdf`
- `scanned_image`
- `handwritten_complex`

Esses valores sao uteis para roteamento de OCR, mas nao sao o contrato do pipeline.

Alteracoes necessarias:

- Separar dois conceitos:
  - `content_type`: tipo tecnico do arquivo/conteudo.
  - `document_type`: tipo de documento de negocio.
- Exemplo de saida:

```json
{
  "document_type": "boleto",
  "content_type": "scanned_pdf",
  "ocr_route": "openrouter",
  "confidence": 0.91
}
```

- Renomear ou mapear os tipos atuais:
  - `digital_pdf` -> `content_type=pdf_text`
  - `scanned_image` com PDF -> `content_type=scanned_pdf`
  - `scanned_image` com imagem -> `content_type=image`
  - documento vindo de upload manual com origem paper -> `content_type=paper_scan`

### 6. Bugs concretos encontrados no caminho de processamento

Foram encontrados problemas de codigo que podem afetar `/api/v1/process`:

1. **Chamada incorreta de `classify_document`**

`domain/classifier.py` define:

```python
def classify_document(filename: str, content: bytes) -> str:
```

Mas `application/process_document.py` chama:

```python
doc_type = classify_document(file_bytes)
```

Isso gera erro de assinatura e faz o fluxo cair sempre no fallback `scanned_image`.

Correcao:

```python
doc_type = classify_document(filename=filename, content=file_bytes)
```

2. **Fallback chama `merge_fallback_result` com assinatura errada**

`fallback_handler.py` define:

```python
merge_fallback_result(primary_data, fallback_data, primary_engine, fallback_engine)
```

Mas `process_document.py` chama:

```python
merge_fallback_result(ocr_result, fallback_result)
```

Correcao:

```python
ocr_result = merge_fallback_result(
    primary_data=ocr_result,
    fallback_data=fallback_result,
    primary_engine=engine_name,
    fallback_engine=fallback_engine_name,
)
```

3. **`ocr_result` pode estar indefinido no bloco de fallback**

Se `engine.process(...)` levantar excecao antes de atribuir `ocr_result`, o bloco `except` tenta usar `ocr_result` no merge.

Correcao:

- Inicializar `ocr_result = {}` antes do `try`; ou
- Se a engine primaria falhar por excecao, usar diretamente o resultado do fallback sem merge.

4. **Schema `OCRResponse` tem campo `debug` fora da classe**

Em `api/schemas/ocr_schema.py`, o campo `debug` esta sem indentacao dentro de `OCRResponse`:

```python
# Debug info
debug: Optional[Dict[str, Any]] = Field(...)
```

Isso cria uma variavel de modulo, nao um campo do modelo. Alem disso, `process_document.py` retorna `_debug`, nao `debug`.

Correcao:

- Indentar `debug` dentro de `OCRResponse`; ou
- Remover do contrato publico.
- Padronizar `debug` versus `_debug`.

5. **HTTPException de validacao vira 500**

`process_document_endpoint` levanta `HTTPException(400)` dentro de um `try`, mas o `except Exception` captura tudo e transforma em 500.

Correcao:

```python
except HTTPException:
    raise
except Exception as e:
    ...
```

### 7. `GET /engines` nao reflete o registry real

`EngineResolver.list_all_engines()` le apenas `CAPABILITIES`. Essa lista nao inclui `openrouter`, `deepseek`, `tesseract` nem `docling` de forma completa para todos os casos. Tambem mistura `paddleocr` nas capabilities, enquanto o registry usa `paddle`.

Alteracoes necessarias:

- Tornar `GET /api/v1/engines` derivado do registry real de engines habilitados.
- Incluir status: `enabled`, `available`, `missing_dependency`, `requires_api_key`.
- Para o perfil inicial, listar claramente `docling` e `openrouter`.
- Nao listar engines desabilitados ou indisponiveis como se estivessem prontos.

### 8. Engines pesadas sao instanciadas no import

`application/process_document.py` registra varias engines no import do modulo:

- DeepSeek
- Docling
- EasyOCR
- LlamaParse
- OpenRouter
- Paddle
- Tesseract
- TrOCR

Apesar do comentario dizer "lazy loading", o codigo instancia todas as classes no startup. Isso aumenta tempo de boot, uso de memoria e risco de falha por dependencia, especialmente se inicialmente vamos usar apenas OpenRouter e Docling.

Alteracoes necessarias:

- Criar registry lazy real: registrar factories, instanciar somente quando a engine for usada.
- Habilitar engines por configuracao.
- No perfil inicial, instanciar apenas:
  - `docling`
  - `openrouter`
- Mover engines legadas para dependencias opcionais.

### 9. OpenRouter deve falhar de forma operacionalmente clara

`OpenRouterOCREngine.process` captura excecoes e retorna `raw_text=""` com `_meta.error`. O pipeline superior pode tratar isso como sucesso parcial, extrair campos vazios e publicar resultado de baixa qualidade.

Alteracoes necessarias:

- Distinguir falha operacional de baixa confianca.
- Para ausencia de `OPENROUTER_API_KEY` ou `OPENROUTER_MODEL`, marcar engine como indisponivel no readiness e evitar processar.
- Publicar `ocr.failed` quando nao houver texto util e o erro for operacional.
- Registrar `error_code`, `retryable`, `provider_status_code` e `provider_message`.

### 10. Falta storage para raw_text e artefatos

O PRD usa `raw_text_uri` no evento `ocr.completed`. Hoje a API retorna `raw_text` inline.

Alteracoes necessarias:

- Criar `StorageService` para gravar:
  - `raw_text.json`
  - imagens renderizadas de paginas, se necessario
  - metadados da engine
  - logs de qualidade por pagina
- Publicar URI no evento, nao payload grande inline.
- Manter retorno inline apenas no endpoint de teste isolado.

### 11. Observabilidade precisa ser reforcada

Existe logging basico, mas falta o padrao definido no PRD.

Alteracoes necessarias:

- Logs JSON estruturados com:
  - `service=backend-ocr`
  - `document_id`
  - `tenant_id`
  - `correlation_id`
  - `engine_used`
  - `content_type`
- Adicionar `GET /ready`, verificando:
  - fila/event bus
  - storage
  - OpenRouter configurado quando habilitado
  - Docling disponivel
- Instrumentar OpenTelemetry.
- Emitir metricas:
  - tempo de OCR por engine
  - documentos processados por content_type
  - falhas por engine
  - taxa de fallback
  - tokens/chamadas OpenRouter, se disponivel

### 12. Docker precisa refletir o perfil inicial

O Dockerfile atual instala varias engines locais pesadas:

- Tesseract
- PaddleOCR/PaddlePaddle
- EasyOCR
- OpenCV

Se o perfil inicial for OpenRouter + Docling, a imagem pode ser reduzida e simplificada.

Alteracoes necessarias:

- Criar requirements por perfil:

```text
requirements-base.txt
requirements-openrouter-docling.txt
requirements-local-ocr.txt
requirements-dev.txt
```

- No Dockerfile inicial, instalar apenas o necessario para:
  - FastAPI
  - OpenRouter client
  - renderizacao/conversao PDF/imagem
  - Docling ou adaptador definido
  - storage/event bus
- Manter engines locais como extras opcionais.

### 13. Testes ainda nao cobrem o que importa para o PRD

Os testes atuais passaram, mas cobrem somente root, health e listagem de engines. Eles nao exercitam OCR, OpenRouter, Docling, contratos de evento nem o endpoint `/api/v1/process`.

Alteracoes necessarias:

- Testes unitarios:
  - `classify_document(filename, content)`
  - resolver com perfil `openrouter_docling`
  - `DoclingEngine` com PDF textual fixture
  - `OpenRouterOCREngine` com mock HTTP
  - erro de OpenRouter sem API key/model
  - serializacao de `ocr.completed`
- Testes de contrato:
  - entrada `document.received`
  - saida `ocr.completed`
  - saida `ocr.failed`
- Testes de integracao:
  - PDF digital -> Docling -> `ocr.completed`
  - PDF escaneado -> OpenRouter mock -> `ocr.completed`
  - imagem -> OpenRouter mock -> `ocr.completed`
  - falha OpenRouter -> retry/failure controlado
- Teste E2E local com fila e storage mockados.

## Proposta de plano de alteracao

### Prioridade 0 - Corrigir bugs que afetam o fluxo atual

- Corrigir chamada de `classify_document`.
- Corrigir chamada de `merge_fallback_result`.
- Corrigir uso de `ocr_result` indefinido no fallback.
- Corrigir `debug`/`_debug` em `OCRResponse`.
- Preservar `HTTPException` 400 no endpoint.

### Prioridade 1 - Definir perfil inicial OpenRouter + Docling

- Ajustar `ENGINE_DEFAULTS`.
- Atualizar `CAPABILITIES`.
- Criar configuracao de engines habilitadas.
- Fazer registry lazy real.
- Atualizar README e Docker para refletir o perfil inicial.

### Prioridade 2 - Separar OCR de extracao semantica

- Remover `FieldExtractor` do caminho principal.
- Retornar/publicar apenas texto bruto, classificacao tecnica e metadados.
- Deixar extracao estruturada para `langextract-service`.

### Prioridade 3 - Event-driven

- Implementar consumidor de `document.received`.
- Implementar publisher de `ocr.completed` e `ocr.failed`.
- Integrar storage para `raw_text_uri`.
- Manter `/api/v1/process` como modo isolado.

### Prioridade 4 - Observabilidade e testes

- Adicionar readiness.
- Logs JSON com correlation ids.
- Metricas por engine.
- Testes unitarios, contrato e integracao para OpenRouter/Docling/eventos.

## Veredito

O `backend-ocr` tem boa base arquitetural e e reaproveitavel. Para o recorte inicial OpenRouter + Docling, ele precisa de ajustes objetivos: tornar OpenRouter o default para imagens/PDFs escaneados, esclarecer ou substituir o `DoclingEngine` por Docling real, corrigir bugs do fluxo atual, remover extracao estruturada do caminho principal e adicionar o modo event-driven com `document.received` e `ocr.completed`.

Depois desses ajustes, o servico ficara alinhado com o papel definido no PRD: modulo OCR autonomo, testavel isoladamente e conectado ao restante do sistema pelo orquestrador/event bus.
