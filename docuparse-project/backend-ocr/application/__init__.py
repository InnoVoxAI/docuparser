# =============================================================================
# CAMADA: application/
# =============================================================================
#
# Responsabilidade ÚNICA: orquestração do fluxo de processamento.
# Também chamada de "Use Case layer" ou "Service layer".
#
# O que pertence aqui:
#   - process_document.py → o coração da aplicação.
#     Ele conhece a ordem das operações, mas NÃO as executa diretamente.
#     Delega cada etapa para a camada correta:
#
#       def process_document(file):
#           doc_type = classifier.classify(file)      # domain/
#           engine   = resolver.get_engine(doc_type)  # domain/
#           raw_text = engine.process(file)           # infrastructure/
#           fields   = extractor.extract(raw_text)    # domain/
#           return build_response(fields, raw_text)
#
# O que NÃO pertence aqui:
#   - Regras de classificação (isso é domínio)
#   - Implementação de OCR (isso é infraestrutura)
#   - Parsing de HTTP request (isso é api/)
#
# Analogia: o application/ é o maestro — ele rege, não toca instrumentos.
#
# Estado atual (Fase 1): pacote criado como placeholder.
# process_document.py será criado na Fase 5 do refactor.
# =============================================================================
