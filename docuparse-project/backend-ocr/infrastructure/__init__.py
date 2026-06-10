# =============================================================================
# CAMADA: infrastructure/
# =============================================================================
#
# Responsabilidade: integrações com o mundo externo — tudo que depende de
# tecnologia específica, serviços externos ou bibliotecas de terceiros.
#
# O que pertence aqui:
#   - engines/       → implementações dos engines de OCR (Tesseract, Paddle,
#                      EasyOCR, TrOCR, Docling, LlamaParse, DeepSeek, OpenRouter)
#
#   - fallback/      → lógica de fallback entre engines: quando acionar,
#                      como combinar resultados de múltiplos engines.
#
# O que NÃO pertence aqui:
#   - Regras de classificação de documentos (isso é domain/)
#   - Extração de campos de NFS-e (isso é domain/)
#   - Configuração de rotas HTTP (isso é api/)
#
# Princípio: se amanhã trocarmos o Tesseract por outro engine, apenas este
# pacote muda — o resto da aplicação não sabe e não precisa saber.
#
# Estado atual (Fase 1): pacote criado como placeholder.
# Os engines serão migrados de engines/ na Fase 4 do refactor.
# =============================================================================
