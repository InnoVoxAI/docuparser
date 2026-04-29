# =============================================================================
# CAMADA: api/routes/
# =============================================================================
#
# Responsabilidade: definir os endpoints HTTP da aplicação.
#
# O que pertence aqui:
#   - Arquivo document.py com os endpoints de processamento:
#       POST /process  → recebe arquivo, chama process_document(), devolve response
#       GET  /engines  → lista os engines OCR disponíveis
#       GET  /         → health check
#
# Padrão esperado para cada endpoint:
#   @router.post("/process")
#   async def process(file: UploadFile):
#       result = process_document(await file.read(), file.filename)
#       return result
#
# Estado atual (Fase 1): pacote criado como placeholder.
# Os endpoints serão migrados de main.py na Fase 6 do refactor.
# =============================================================================
