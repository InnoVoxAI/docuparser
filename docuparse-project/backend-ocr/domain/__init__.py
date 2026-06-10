# =============================================================================
# CAMADA: domain/
# =============================================================================
#
# Responsabilidade: regras de negócio puras — independentes de framework,
# banco de dados ou tecnologia de OCR.
#
# O que pertence aqui:
#   - classifier.py      → classifica o documento UMA única vez no fluxo
#                          Retorna: digital_pdf | scanned_image | handwritten_complex
#
#   - engine_resolver.py → Strategy Pattern: recebe o doc_type classificado e
#                          retorna qual engine de OCR deve ser usado.
#                          Elimina o bloco de ifs do router.py atual.
#
#   - field_extractor.py → extrai campos estruturados do texto bruto do OCR:
#                          fornecedor, tomador, CNPJ, valor NF, retenção, etc.
#                          Inclui scoring de confiança por campo.
#
# Regra de ouro desta camada:
#   O código aqui não importa FastAPI, pytesseract, paddle ou qualquer lib externa.
#   Se um import não for stdlib ou uma interface interna, ele não pertence ao domain/.
#
# Estado atual (Fase 1): pacote criado como placeholder.
# Os arquivos serão populados nas Fases 2 e 3 do refactor.
# =============================================================================
