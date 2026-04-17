# Workflow atual do DocuParse

Este documento descreve o fluxo atual de processamento do upload no frontend até o JSON final retornado ao usuário, incluindo regras de roteamento, fallback e validação orientada a campos críticos.

## 1) Entrada no Frontend (React)

Arquivo principal: docuparse-project/frontend/src/main.jsx.

### Fluxo da interface

1. O usuário seleciona um arquivo (.pdf, .png, .jpg, .jpeg, .bmp, .tif, .tiff, .webp).
2. O frontend carrega opções de engine via GET /api/ocr/engines.
3. Ao clicar em Start, envia multipart/form-data para POST /api/ocr/process com:
   - file (obrigatório)
   - engine (opcional; quando selecionado pelo usuário)
4. Exibe o JSON de resposta no visualizador.

### Regras da interface

- Sem arquivo, o botão não inicia processamento.
- Se engine não for informado, o backend decide automaticamente.
- Erros HTTP são exibidos na interface.

---

## 2) Backend Core (Django) – Gateway/Orquestração

Arquivos principais:

- docuparse-project/backend-core/documents/views.py
- docuparse-project/backend-core/documents/services/ocr_client.py

### Fluxo do gateway

1. GET /api/ocr/engines chama OCRClient.list_engines() no backend-ocr.
2. POST /api/ocr/process valida file.
3. Se válido, repassa o arquivo para backend-ocr (/process), mantendo engine quando informado.
4. Retorna ao frontend o JSON recebido do backend-ocr.

### Regras do gateway

- File ausente => erro 400.
- Falha de comunicação com backend-ocr => erro 502.
- O backend-core atua como proxy/orquestrador (não executa OCR).

---

## 3) Backend OCR (FastAPI) – Processamento

Arquivos principais:

- docuparse-project/backend-ocr/main.py
- docuparse-project/backend-ocr/agent/classifier.py
- docuparse-project/backend-ocr/agent/router.py

### Endpoint /process

1. Lê bytes do arquivo enviado.
2. Chama route_and_process(filename, content, selected_engine).
3. Retorna envelope padrão com:
   - filename
   - detected_type
   - tools_used
   - transcription
   - processing_time

### Regras do endpoint

- A decisão de engine e fallback acontece no router.
- detected_type vem da classificação do documento.

---

## 4) Classificação do Documento

Classes possíveis:

- digital_pdf
- scanned_image
- handwritten_complex

### Sinais usados

- Extensão e assinatura de conteúdo (PDF vs imagem).
- Heurísticas do nome do arquivo (manuscrito, scanned, table, mixed).
- Para PDF: camada textual + sinais visuais em amostragem de páginas.
- Para imagem: sinais de manuscrito/complexidade extraídos por visão computacional.

### Regras de decisão (resumo)

- PDF com texto extraível e estrutura forte tende a digital_pdf.
- Sinais fortes de manuscrito/mistura tendem a handwritten_complex.
- Imagens sem sinal forte de manuscrito tendem a scanned_image.

---

## 5) Roteamento e Fallback

### Resolução da engine

1. Se o usuário informou engine, essa escolha é priorizada (com aliases, por exemplo paddleocr -> paddle e hybrid -> paddle_deepseek).
2. Se não informou:
   - digital_pdf -> docling
   - scanned_image -> paddle
   - handwritten_complex -> paddle_deepseek
   - fallback final -> tesseract

### Pré-processamento

- Para docling/llamaparse em PDF, prioriza PDF original.
- Para OCR em imagem, pode renderizar a primeira página do PDF e aplicar preprocess por engine.
- Metadados de entrada/preprocess entram em input_meta e ocr_meta.

### Fallback técnico por engine/confiança OCR

- Paddle: se avg_confidence < 70, tenta EasyOCR.
- Paddle + DeepSeek (híbrido): se avg_confidence < 70, tenta DeepSeek.
- Docling: se avg_confidence < 70, tenta LlamaParse.
- EasyOCR indisponível: fallback para Tesseract.
- DeepSeek indisponível: fallback para Tesseract no modo deepseek direto.
- Erros de runtime/Tesseract ausente: resposta resiliente com raw_text_fallback.

### Fallback orientado a campos críticos (field-driven)

- Após OCR, o sistema extrai campos críticos:
  - fornecedor
  - tomador
  - cnpj_fornecedor
  - numero_nf
  - descricao_servico
  - valor_nf
  - retencao
  - cnpj_tomador
- Em seguida valida os campos (CNPJ, valor, número de nota, descrição, presença de retenção e presença de obrigatórios).
- Calcula:
  - field_score = taxa de validações aprovadas
  - final_score = 0.4 × ocr_confidence + 0.6 × field_score
- Dispara fallback adicional quando:
  - campo crítico inválido, ou
  - campo obrigatório ausente, ou
  - final_score < 0.85
- Engine de fallback adicional por classe:
  - digital_pdf -> llamaparse
  - scanned_image -> easyocr
  - handwritten_complex -> deepseek
- Faz merge inteligente de campos, priorizando valor de fallback quando ele estiver válido (ou quando o primário estiver vazio).

---

## 6) Formato do Resultado

O retorno final contém transcription normalizado no router.

Estrutura de transcription:

- fields
- required_fields
- field_validation
- field_score
- ocr_confidence
- final_score
- fallback_needed
- source
- fallback_engine
- fields_from_fallback
- totals
- raw_text
- raw_text_fallback
- ocr_meta

Observação: source, fallback_engine, fields_from_fallback e ocr_meta ajudam a rastrear decisões do pipeline e origem dos dados finais.

---

## 7) OCRs disponíveis

### Disponíveis no dropdown (via /engines)

- tesseract
- docling
- deepseek
- llamaparse
- easyocr (somente se instalado no ambiente)

### Disponíveis internamente no roteador

- paddle
- paddle_deepseek (híbrido)

### Papel breve de cada engine

- Tesseract: fallback robusto para imagem.
- EasyOCR: OCR para imagem com boa cobertura PT/EN.
- PaddleOCR: OCR principal para documentos escaneados.
- DeepSeek: extração multimodal para cenários complexos/manuscritos.
- Docling: foco em PDF digital com leitura estrutural.
- LlamaParse: parser alternativo de PDF, usado também em fallback.

---

## 8) Resumo executivo

Frontend (upload + engine opcional) -> Backend Core (proxy) -> Backend OCR (/process) -> Classifier -> Router (engine + preprocess + fallback) -> OCR Engine -> Extração/Validação de campos -> Merge -> transcription final no frontend.
