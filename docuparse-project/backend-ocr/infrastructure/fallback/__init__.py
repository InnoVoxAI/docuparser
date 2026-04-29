# =============================================================================
# CAMADA: infrastructure/fallback/
# =============================================================================
#
# Responsabilidade: gerenciar a lógica de fallback entre engines de OCR.
#
# O que pertence aqui:
#   - fallback_handler.py → centraliza TODA a lógica de fallback:
#       should_trigger_fallback()  → decide se o resultado primário é suficiente
#                                    ou se um segundo engine deve ser acionado
#                                    (checa: confidence médio, cobertura de texto,
#                                     falhas de engine, campos críticos ausentes)
#
#       merge_fallback_result()    → combina resultados do engine primário e
#                                    do fallback, escolhendo o melhor por campo
#
#       is_engine_error_fallback() → detecta quando o engine falhou por erro
#                                    (diferente de qualidade baixa)
#
# Por que isolado aqui e não no router:
#   A lógica de "devo tentar de novo com outro engine?" é uma decisão de
#   infraestrutura — ela sabe o que os engines retornam e como combiná-los.
#   Não é regra de negócio (domain) nem fluxo de orquestração (application).
#
# Estado atual (Fase 1): pacote criado como placeholder.
# fallback_handler.py será migrado de utils/ocr_fallback.py na Fase 4 do refactor.
# =============================================================================
