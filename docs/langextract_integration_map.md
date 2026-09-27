# LangExtract front-end <-> back-end map

Este documento descreve como a UI de "Configuracoes > Extracao" se relaciona com os servicos atuais e quais integracoes ja existem.

## Contexto rapido

- O front-end possui a UI de configuracao do LangExtract na aba "Configuracoes > Extracao" com sub-abas: Modelo, OCR referencia, Schema, Instrucoes, Exemplos, Teste visual, Regras, Publicacao.
- O back-end possui dois blocos relevantes:
  - Backend core (Django REST): fornece APIs de documentos, schemas, layouts, settings e fila operacional.
  - LangExtract service (FastAPI): faz extracao basica e publica eventos, mas nao recebe as configuracoes da UI.

## Fluxo atual (alto nivel)

1. Documento entra no sistema -> backend-com envia evento -> backend-ocr gera OCR.
2. layout-service classifica layout e publica "layout.classified".
3. langextract-service consome "layout.classified" e publica "extraction.completed".
4. backend-core consome "extraction.completed" e grava ExtractionResult no banco.
5. UI de validacao consome o resultado para o operador aprovar/corrigir.

O langextract-service extrai via LLM usando o SchemaConfig.definition do catalogo: no fluxo sincrono o backend-core envia a definition; no worker ela e buscada pelo LayoutConfig do layout. Nao ha regras de extracao fixas em codigo (ver memories/decisions "Extração catálogo-only").

## Front-end (Configuracoes > Extracao) -> Backend core

### Endpoints usados diretamente pela UI

- Schema configs
  - GET /api/ocr/schema-configs
  - POST /api/ocr/schema-configs
  - PATCH /api/ocr/schema-configs/{schema_id}
  - Arquivo: [docuparse-project/backend-core/documents/urls.py](docuparse-project/backend-core/documents/urls.py#L34-L43)
  - Implementacao: [docuparse-project/backend-core/documents/views.py](docuparse-project/backend-core/documents/views.py#L225-L264)

- Layout configs
  - GET /api/ocr/layout-configs
  - POST /api/ocr/layout-configs
  - Arquivo: [docuparse-project/backend-core/documents/urls.py](docuparse-project/backend-core/documents/urls.py#L40-L44)
  - Implementacao: [docuparse-project/backend-core/documents/views.py](docuparse-project/backend-core/documents/views.py#L265-L289)

- Documentos (para OCR referencia e preview)
  - GET /api/ocr/documents
  - GET /api/ocr/documents/{document_id}
  - GET /api/ocr/documents/{document_id}/file
  - Arquivo: [docuparse-project/backend-core/documents/urls.py](docuparse-project/backend-core/documents/urls.py#L20-L38)
  - Implementacao: [docuparse-project/backend-core/documents/views.py](docuparse-project/backend-core/documents/views.py#L68-L170)

### Como cada aba usa o back-end hoje

- Modelo (setup)
  - Usa GET schema-configs para listar e POST/PATCH para salvar.
  - Definicao do schema (prompt, exemplos, regras) vai em SchemaConfig.definition.
  - Relacao: [docuparse-project/frontend/src/main.jsx](docuparse-project/frontend/src/main.jsx#L1049-L1189)
  - Status: integrado com backend-core.

- OCR referencia
  - Usa documentos e detalhe para carregar OCR e preview.
  - Relacao: [docuparse-project/frontend/src/main.jsx](docuparse-project/frontend/src/main.jsx#L979-L1068)
  - Status: integrado com backend-core.

- Schema
  - Edita campos localmente e salva via schema-configs.
  - Status: integrado com backend-core.

- Instrucoes
  - Edita prompt localmente e salva via schema-configs.
  - Status: integrado com backend-core.

- Exemplos
  - Edita few-shot localmente e salva via schema-configs.
  - Status: integrado com backend-core.

- Teste visual
  - Gera JSON mockado no front-end (buildLangExtractPreview).
  - Nao chama API de extracao.
  - Status: somente mock no front-end.

- Regras
  - Edita JSON localmente e salva via schema-configs.
  - Status: integrado com backend-core.

- Publicacao
  - Salva schema-configs e cria layout-configs.
  - Status: integrado com backend-core.

## LangExtract service (FastAPI)

### Endpoints

- POST /api/v1/extract
  - Exige schema_definition (422 sem ele) e extrai via LLM, retornando ExtractResponse.
  - Arquivos: [docuparse-project/langextract-service/api/app.py](docuparse-project/langextract-service/api/app.py), [docuparse-project/langextract-service/domain/llm_extractor.py](docuparse-project/langextract-service/domain/llm_extractor.py)

### Worker de eventos

- Consome "layout.classified", busca o SchemaConfig do layout no backend-core e publica "extraction.completed". Sem schema no catalogo, nao publica nada.
  - Arquivos: [docuparse-project/langextract-service/application/extraction_event_worker.py](docuparse-project/langextract-service/application/extraction_event_worker.py), [docuparse-project/langextract-service/domain/backend_core_client.py](docuparse-project/langextract-service/domain/backend_core_client.py)

### Regras de extracao atuais

- Layout -> schema vem do LayoutConfig do catalogo global (backend-core). O extrator regex e o mapa fixo SCHEMA_BY_LAYOUT foram removidos em 2026-09-27.

## Backend core: consumo de extraction.completed

- Evento "extraction.completed" gera ExtractionResult e muda status do documento.
  - Arquivo: [docuparse-project/backend-core/documents/services/event_consumers.py](docuparse-project/backend-core/documents/services/event_consumers.py#L38-L104)
- Worker do backend-core consome eventos e grava resultados.
  - Arquivo: [docuparse-project/backend-core/documents/services/event_stream_worker.py](docuparse-project/backend-core/documents/services/event_stream_worker.py#L16-L61)

## Mapa de integracao por aba

| Aba UI | Integracao no backend-core | Integracao no langextract-service | Status atual |
| --- | --- | --- | --- |
| Modelo | SchemaConfig CRUD | Nao usa SchemaConfig | Parcial (salva, nao aplica na extracao) |
| OCR referencia | Documentos + transcricao OCR | N/A | OK (backend-core) |
| Schema | SchemaConfig.definition.fields | Nao usa SchemaConfig | Parcial |
| Instrucoes | SchemaConfig.definition.prompt | Nao usa SchemaConfig | Parcial |
| Exemplos | SchemaConfig.definition.examples | Nao usa SchemaConfig | Parcial |
| Teste visual | Mock local no front-end | Nao chama /api/v1/extract | Incompleto |
| Regras | SchemaConfig.definition.post_processing | Nao usa SchemaConfig | Parcial |
| Publicacao | LayoutConfig CRUD | Nao usa LayoutConfig | Parcial |

## Lacunas e falhas encontradas

1. (Resolvido em 2026-09-27) LangExtract service nao consumia SchemaConfig/LayoutConfig no worker; a extracao era fixa em codigo.
2. A UI nao chama /api/v1/extract para teste visual; o preview e gerado no front-end.
3. Nao ha endpoint no backend-core para executar extracao usando o schema salvo nem para validar/registrar exemplos.
4. (Resolvido em 2026-09-27) O mapeamento de layout -> schema era fixo (SCHEMA_BY_LAYOUT) e ignorava o LayoutConfig.
5. (Resolvido em 2026-09-27) SchemaConfig.version agora chega ao langextract-service nos dois fluxos.
6. Regras de pos-processamento e traceabilidade existem na UI, mas nao sao aplicadas na extracao real.

## O que ja esta pronto e usado

- UI salva e lista schemas/layouts no backend-core.
- UI usa documentos e OCR do backend-core para referencia e validacao.
- pipeline de eventos publica "extraction.completed" e grava ExtractionResult.

## O que falta para conectar LangExtract ao que a UI configura

- Um adaptador no langextract-service para buscar SchemaConfig/LayoutConfig do backend-core ou de um storage compartilhado.
- Uma forma de selecionar schema por layout/configuracao (LayoutConfig) em runtime.
- Um endpoint no backend-core (ou langextract-service) para teste visual real, chamando a extracao com o schema escolhido.
- Aplicar regras de pos-processamento e traceabilidade na extracao (ex: incluir source span).
