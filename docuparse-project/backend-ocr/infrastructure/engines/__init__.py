# =============================================================================
# CAMADA: infrastructure/engines/
# =============================================================================
#
# Responsabilidade: implementar os engines de OCR disponíveis na aplicação.
#
# O que pertence aqui:
#   - base_engine.py      → classe abstrata (ABC) que define o contrato comum
#                           para todos os engines. Todo engine DEVE implementar:
#                               process(file_bytes: bytes, metadata: dict) → dict
#                               name: str (property)
#
#   - openrouter_engine.py → OCR via LLM multimodal (OpenRouter API)
#                            ATENÇÃO: a classificação interna atual (texto vs imagem)
#                            será removida nesta fase — o engine receberá doc_type
#                            já classificado via metadata.
#
#   - tesseract_engine.py  → OCR local via pytesseract
#   - paddle_engine.py     → OCR via PaddleOCR (melhor para documentos escaneados)
#   - easyocr_engine.py    → OCR via EasyOCR
#   - trocr_engine.py      → OCR transformer para manuscritos (Microsoft TrOCR)
#   - docling_engine.py    → Extração de texto de PDFs com camada de texto
#   - llamaparse_engine.py → Parsing de PDFs via LlamaParse
#   - deepseek_engine.py   → OCR via modelo Deepseek multimodal (Ollama)
#
# Todos os engines DEVEM herdar de BaseOCREngine para garantir interface uniforme.
# Isso permite que o engine_resolver.py os trate de forma intercambiável.
#
# Estado atual (Fase 1): pacote criado como placeholder.
# Os engines serão migrados de engines/ na Fase 4 do refactor.
# =============================================================================
