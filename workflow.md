# Workflow atual do DocuParse

Este documento descreve o fluxo atual de processamento **do upload no frontend até o JSON final retornado ao usuário**, incluindo regras de roteamento/fallback e os OCRs disponíveis.

## 1) Entrada no Frontend (React)

Arquivo principal: `docuparse-project/frontend/src/main.jsx`.

### Fluxo
1. O usuário seleciona um arquivo (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`, `.webp`).
2. O frontend carrega opções de engine via `GET /api/ocr/engines`.
3. Ao clicar em **Start**, envia `multipart/form-data` para `POST /api/ocr/process` com:
   - `file` (obrigatório)
   - `engine` (opcional; quando selecionado pelo usuário) -> O usuário também pode deixar o sistema decidir o melhor engine
4. Exibe o JSON de resposta no visualizador.

### Regras nesta etapa
- Sem arquivo, o botão de execução não deve processar.
- Se `engine` não for informado, o backend usa roteamento automático.
- Erros HTTP são exibidos no bloco de erro da tela.

---

## 2) Backend Core (Django) – Gateway/Orquestração

Arquivos principais:
- `docuparse-project/backend-core/documents/views.py`
- `docuparse-project/backend-core/documents/services/ocr_client.py`

### Fluxo
1. `GET /api/ocr/engines` chama `OCRClient.list_engines()` no backend-ocr.
2. `POST /api/ocr/process` valida `file`.
3. Se válido, repassa o arquivo para o backend-ocr (`/process`) mantendo `engine` quando informado.
4. Retorna o JSON recebido do backend-ocr para o frontend.

### Regras nesta etapa
- Campo `file` ausente => erro `400`.
- Falha de comunicação com backend-ocr => erro `502`.
- O backend-core não faz OCR; ele atua como proxy/orquestrador.

---

## 3) Backend OCR (FastAPI) – Processamento

Arquivos principais:
- `docuparse-project/backend-ocr/main.py`
- `docuparse-project/backend-ocr/agent/classifier.py`
- `docuparse-project/backend-ocr/agent/router.py`

### 3.1 Endpoint `/process`
1. Lê bytes do arquivo enviado.
2. Chama `route_and_process(filename, content, selected_engine)`.
3. Retorna envelope padrão:
   - `filename`
   - `detected_type`
   - `tools_used`
   - `transcription`
   - `processing_time`

### Regras nesta etapa
- A decisão real de engine/fallback acontece no `router.py`.
- `detected_type` vem da classificação do documento.

---

## 4) Classificação do Documento (`classifier.py`)

Classes possíveis:
- `digital_pdf`
- `scanned_image`
- `handwritten_complex`

### Sinais usados (resumo)
- Extensão/assinatura do arquivo (PDF vs imagem).
- Heurísticas do nome do arquivo (ex.: manuscrito, scanned, table, mixed).
- Para PDF: presença de camada textual + análise visual por página (amostragem).
- Para imagem: análise visual para score de manuscrito/complexidade.

### Regras de decisão (resumo)
- PDF com muito texto extraível e estrutura tende a `digital_pdf`.
- Conteúdo com forte sinal de manuscrito/misto tende a `handwritten_complex`.
- Imagens comuns (sem sinal forte de manuscrito) tendem a `scanned_image`.

---

## 5) Roteamento e Fallback (`router.py`)

### 5.1 Resolução da engine
Ordem de decisão:
1. Se usuário informou `engine`, ela é priorizada (com aliases, ex.: `paddleocr` -> `paddle`, `hybrid` -> `paddle_deepseek`).
2. Se não informou:
   - `digital_pdf` -> `docling`
   - `scanned_image` -> `paddle`
   - `handwritten_complex` -> `paddle_deepseek`
   - fallback final -> `tesseract`

### 5.2 Pré-processamento
- PDF para parser nativo (`docling`/`llamaparse`): usa PDF original quando aplicável.
- Fluxo OCR em imagem: pode renderizar 1ª página de PDF para PNG e aplicar preprocess específico por engine.
- Metadados de entrada/preprocess são adicionados em `input_meta`/`_meta`.

### 5.3 Regras de fallback (resumo)
- **Paddle**: se `avg_confidence < 70`, tenta fallback para **EasyOCR**.
- **Paddle + DeepSeek (híbrido)**: se `avg_confidence < 70`, aciona DeepSeek; se DeepSeek indisponível/erro, mantém resultado Paddle.
- **Docling**: se `avg_confidence < 70`, fallback para **LlamaParse**.
- **EasyOCR indisponível**: fallback para **Tesseract**.
- **DeepSeek indisponível**: fallback para **Tesseract** no modo deepseek direto.
- Erros de runtime/Tesseract ausente: retorna extração mock + mensagem em `raw_text_fallback`.

---

## 6) Formato do Resultado

O retorno final do `/process` contém um campo `transcription` (normalizado no `router.py`).

Estrutura atualmente usada em `transcription`:
- `document_info`
- `entities`
- `tables`
- `totals`
- `raw_text`
- `raw_text_fallback`
- `ocr_meta`

Observação: em casos de fallback, `ocr_meta` registra informações como `primary_engine`, `fallback_engine`, confiança média e flags de erro.

---

## 7) OCRs disponíveis

### 7.1 Disponíveis no dropdown do frontend (via `/engines` do backend-ocr)
- `tesseract`
- `docling`
- `deepseek`
- `llamaparse`
- `easyocr` (apenas se o pacote estiver instalado no ambiente)

### 7.2 Disponíveis internamente no roteador (mesmo que não apareçam sempre no dropdown)
- `paddle`
- `paddle_deepseek` (híbrido)

### 7.3 Papel breve de cada engine
- **Tesseract**: OCR clássico e fallback robusto para imagens.
- **EasyOCR**: OCR para imagens com boa leitura de texto misto PT/EN.
- **PaddleOCR**: OCR principal para imagem escaneada, com score de confiança e fallback.
- **DeepSeek**: extração multimodal para cenários complexos/manuscritos (via Ollama/OpenAI-compatible).
- **Docling**: foco em PDF digital com análise estrutural por páginas.
- **LlamaParse**: parser alternativo para PDF digital (usado também como fallback do Docling).

---

## 8) Resumo executivo do caminho ponta a ponta

`Frontend (upload + engine opcional)` -> `Backend Core (proxy/orquestra)` -> `Backend OCR (/process)` -> `Classifier` -> `Router (engine + preprocess + fallback)` -> `Engine OCR` -> `Normalize transcription` -> `JSON final no frontend`.
