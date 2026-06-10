# =============================================================================
# CAMADA: shared/
# =============================================================================
#
# Responsabilidade: utilitários genéricos e reutilizáveis por qualquer camada.
#
# O que pertence aqui:
#   - preprocessing.py → pipelines de pré-processamento de imagem.
#                        Cada engine tem seu pipeline específico, mas o código
#                        fica centralizado aqui para evitar duplicação:
#                            deskew, CLAHE, denoise, upscale, sharpen,
#                            warp_perspective, segment_handwritten_regions, etc.
#                        Migrado de: utils/preprocessing.py (sem mudança de lógica)
#
#   - validators.py    → validações genéricas independentes de domínio:
#                            cnpj_is_valid()   → checksum Módulo 11
#                            parse_currency()  → "R$ 1.234,56" → float
#                            is_valid_date()   → "DD/MM/YYYY"  → bool
#                        Extraído de: utils/validate_fields.py
#
# Regra de ouro desta camada:
#   O código aqui não deve importar nada de api/, application/, domain/ ou
#   infrastructure/. É a camada mais "baixa" — depende apenas de libs externas
#   e stdlib. Qualquer outra camada pode importar shared/, nunca o contrário.
#
# Estado atual (Fase 1): pacote criado como placeholder.
# Os arquivos serão migrados na Fase 2 do refactor.
# =============================================================================
