# Fix Plan: OpenRouter 404 — `baidu/qianfan-ocr-fast:free` not found

**Erro observado:**
```
OpenRouter errors: page_1: OpenRouter HTTP 404: {"error":{"message":"No endpoints found for baidu/qianfan-ocr-fast:free.","code":404},"user_id":"..."}
```

**Fluxo afetado:** Processamento OCR de documentos do tipo `scanned_image` via engine `openrouter`.

---

## Hipóteses internas (código / configuração)

### H1 — Modelo removido do OpenRouter (causa mais provável)
O modelo `baidu/qianfan-ocr-fast:free` retorna 404 com a mensagem "No endpoints found". O OpenRouter usa esse código quando o modelo não está mais disponível na plataforma. O `.env` aponta para esse modelo como `OPENROUTER_MODEL`, que é lido diretamente em `openrouter_engine.py:239`:
```python
model = (model_override or os.getenv("OPENROUTER_MODEL", "")).strip()
```
**Localização:** `docuparse-project/.env` (variável `OPENROUTER_MODEL`)

---

### H2 — `LANGEXTRACT_MODEL` configurado com modelo de visão (erro de configuração)
O `.env` define `LANGEXTRACT_MODEL=baidu/qianfan-ocr-fast:free`. Esse é um modelo de visão (OCR visual), mas o `langextract-service` o usa para **extração de texto estruturado via chat-completions** — sem envio de imagem.

O próprio comentário no código (`llm_extractor.py:204–208`) adverte explicitamente:
```python
# We deliberately do NOT fall back to OPENROUTER_MODEL because that variable is
# shared with backend-ocr and may point to a vision-only model (e.g.
# baidu/qianfan-ocr-fast:free) that rejects text chat-completion requests.
```
O modelo correto anterior era `deepseek/deepseek-chat-v3-0324:free` (linha comentada no `.env`).

**Localização:** `docuparse-project/.env` (variável `LANGEXTRACT_MODEL`)

---

### H3 — Fallback de modelo nunca é acionado em caso de erro HTTP
Em `openrouter_engine.py:315–349`, a função `_call_openrouter_with_empty_text_retry()` só aciona o modelo de fallback (`OPENROUTER_FALLBACK_MODEL`) quando o modelo primário retorna **texto vazio**. Um erro HTTP 404 lança uma exceção (`RuntimeError`) que é capturada no nível da página em `_process_image_pdf()` e adicionada a `page_errors` — nunca acionando o fallback.

```python
# Fallback é acionado apenas aqui — somente se _extract_ocr_text(result) for vazio:
if _extract_ocr_text(result):
    return result, False, primary_model
```

Resultado: `OPENROUTER_FALLBACK_MODEL=qwen/qwen2.5-vl-72b-instruct` (que está disponível) nunca é tentado quando o modelo primário está indisponível.

**Localização:** `backend-ocr/infrastructure/engines/openrouter_engine.py:315–349`

---

### H4 — Desconexão entre OCRSettings do banco de dados e variável de ambiente lida pelo backend-ocr
O frontend salva o modelo OpenRouter no banco de dados via `OCRSettings.openrouter_model` (`backend-core/documents/models.py:177`). Mas o `backend-ocr` lê o modelo exclusivamente da variável de ambiente `OPENROUTER_MODEL` no momento da chamada:
```python
model = (model_override or os.getenv("OPENROUTER_MODEL", "")).strip()
```
Mudanças salvas na aba "OCR" das configurações do frontend **não afetam** o modelo usado pelo `backend-ocr`, a não ser que o container seja reiniciado com o `.env` atualizado. O campo do banco nunca é propagado para o ambiente do serviço.

**Localização:**
- `backend-core/documents/models.py:177` (campo `openrouter_model`)
- `backend-core/documents/views.py:391–430` (endpoint PATCH `/settings/ocr`)
- `backend-ocr/infrastructure/engines/openrouter_engine.py:239` (leitura da env var)

---

### H5 — docker-compose sobrescreve o fallback padrão do `LANGEXTRACT_MODEL`
O `docker-compose.yml` define o padrão:
```yaml
LANGEXTRACT_MODEL: ${LANGEXTRACT_MODEL:-deepseek/deepseek-chat-v3-0324:free}
```
Porém, como o `.env` define `LANGEXTRACT_MODEL=baidu/qianfan-ocr-fast:free`, o valor da variável sobrescreve o fallback do Compose. O modelo `deepseek` (funcional para extração de texto) nunca é usado.

**Localização:** `docuparse-project/docker-compose.yml` (serviço `langextract-service`), `docuparse-project/.env`

---

### H6 — Erro de OCR é mascarado, não sinalizado claramente ao usuário
Quando uma página falha em `_process_image_pdf()`, o erro é adicionado a `page_errors` mas não propaga exceção. O resultado final tem `raw_text=""` e `raw_text_fallback="OpenRouter errors: ..."`. O frontend exibe esse conteúdo no campo de transcrição, sem distinção visual entre um texto extraído e uma mensagem de erro.

**Localização:** `backend-ocr/infrastructure/engines/openrouter_engine.py:487–498`

---

## Causas externas ao código

### E1 — Descontinuação do modelo `baidu/qianfan-ocr-fast:free` pelo OpenRouter
O modelo foi disponibilizado como tier gratuito no OpenRouter e pode ter sido removido pelo provedor (Baidu) ou pela própria plataforma OpenRouter sem aviso prévio. Modelos gratuitos (`*:free`) são instáveis em relação à disponibilidade.

**Como verificar:** Acesse [openrouter.ai/models](https://openrouter.ai/models) e busque por `baidu/qianfan-ocr-fast`.

---

### E2 — Instabilidade temporária no endpoint do OpenRouter
O OpenRouter pode ter sofrido instabilidade temporária no roteamento para este modelo. A mensagem "No endpoints found" pode indicar que o modelo está temporariamente sem capacidade de inferência, não necessariamente removido de forma permanente.

---

### E3 — Política de cotas ou bloqueio de IP/chave de API
O OpenRouter pode ter aplicado limites de taxa ou bloqueado a chave de API `sk-or-v1-...` por excesso de requisições, conta inativa ou violação de termos. Nesse caso, mesmo modelos disponíveis retornariam erros.

---

## Ações recomendadas

1. **Imediato** — Substituir `OPENROUTER_MODEL` e `LANGEXTRACT_MODEL` no `.env`:
   ```dotenv
   OPENROUTER_MODEL=qwen/qwen2.5-vl-72b-instruct
   LANGEXTRACT_MODEL=deepseek/deepseek-chat-v3-0324:free
   ```
   O modelo de visão `qwen/qwen2.5-vl-72b-instruct` já é o `OPENROUTER_FALLBACK_MODEL` e estava funcional. O `deepseek` é adequado para text chat completions.

2. **Médio prazo** — Corrigir o fallback em `openrouter_engine.py` para acionar `OPENROUTER_FALLBACK_MODEL` também em caso de erros HTTP (4xx/5xx), não apenas em texto vazio.

3. **Médio prazo** — Propagar `OCRSettings.openrouter_model` do banco de dados para o container `backend-ocr` (via env injection no runtime ou chamada de API), eliminando a desconexão entre frontend e serviço.
