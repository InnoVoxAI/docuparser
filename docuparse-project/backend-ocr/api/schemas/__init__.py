# =============================================================================
# CAMADA: api/schemas/
# =============================================================================
#
# Responsabilidade: definir os modelos Pydantic de entrada e saída da API.
#
# O que pertence aqui:
#   - Arquivo ocr_schema.py com os modelos de dados:
#       OCRResponse     → estrutura completa do response do endpoint /process
#       Transcription   → campos extraídos do documento (fornecedor, CNPJ, valor...)
#       FieldConfidence → score de confiança por campo extraído
#
# Por que isso é uma camada separada:
#   Schemas são contratos públicos da API — definem o que o frontend espera receber.
#   Mantê-los isolados permite evoluir a representação interna dos dados sem
#   quebrar o contrato externo.
#
# Estado atual (Fase 1): pacote criado como placeholder.
# Os schemas serão migrados de main.py na Fase 6 do refactor.
# =============================================================================
