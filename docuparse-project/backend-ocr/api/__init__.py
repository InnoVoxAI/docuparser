# =============================================================================
# CAMADA: api/
# =============================================================================
#
# Responsabilidade ÚNICA: ponto de entrada HTTP da aplicação.
#
# O que pertence aqui:
#   - Configuração do FastAPI (app, middlewares, CORS)          → api/app.py
#   - Definição de rotas e endpoints (POST /process, GET /)     → api/routes/
#   - Modelos Pydantic de request e response (schemas)          → api/schemas/
#
# O que NÃO pertence aqui:
#   - Lógica de OCR ou processamento de documentos
#   - Classificação de arquivos
#   - Extração ou validação de campos
#   - Chamadas diretas a qualquer engine
#
# Regra de ouro: se o código não tem relação com HTTP, ele não fica aqui.
# O endpoint deve apenas receber o arquivo e delegar para application/.
#
# Estado atual (Fase 1): pacote criado como placeholder.
# Os arquivos serão populados na Fase 6 do refactor.
# =============================================================================
