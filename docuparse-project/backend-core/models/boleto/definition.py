from __future__ import annotations

SCHEMA_ID = "boleto_default"
VERSION = "v1"
MODEL_NAME = "BOLETO DEFAULT"

FIELDS = [
    # =========================================================
    # IDENTIFICACAO DO BOLETO
    # =========================================================
    {
        "name": "tipo_documento",
        "type": "string",
        "required": False,
        "rule": "Tipo do documento: boleto bancario, ficha de compensacao, arrecadacao etc.",
    },
    {
        "name": "categoria_documento",
        "type": "string",
        "required": False,
        "rule": "Categoria do documento: condominio, aluguel, escolar, bancario etc.",
    },
    {
        "name": "codigo_barras",
        "type": "string",
        "required": False,
        "rule": "Codigo de barras numerico com 44 digitos.",
    },
    {
        "name": "linha_digitavel",
        "type": "string",
        "required": True,
        "rule": "Sequencia da linha digitavel; remover espacos e pontuacao.",
    },
    {
        "name": "nosso_numero",
        "type": "string",
        "required": False,
        "rule": "Nosso numero do boleto.",
    },
    {
        "name": "numero_documento",
        "type": "string",
        "required": False,
        "rule": "Numero do documento ou referencia interna.",
    },
    {
        "name": "numero_controle",
        "type": "string",
        "required": False,
        "rule": "Numero de controle interno do boleto.",
    },
    {
        "name": "carteira",
        "type": "string",
        "required": False,
        "rule": "Codigo da carteira bancária.",
    },
    {
        "name": "especie_documento",
        "type": "string",
        "required": False,
        "rule": "Especie do documento: DM, DS, NP etc.",
    },
    {
        "name": "aceite",
        "type": "boolean",
        "required": False,
        "rule": "Indica aceite do documento.",
    },
    # =========================================================
    # BANCO / EMISSAO
    # =========================================================
    {
        "name": "codigo_banco",
        "type": "string",
        "required": False,
        "rule": "Codigo do banco emissor.",
    },
    {
        "name": "nome_banco",
        "type": "string",
        "required": False,
        "rule": "Nome do banco emissor.",
    },
    {
        "name": "instituicao_cobranca",
        "type": "string",
        "required": False,
        "rule": "Instituicao financeira ou fintech responsavel pela cobranca.",
    },
    {
        "name": "agencia",
        "type": "string",
        "required": False,
        "rule": "Numero da agencia.",
    },
    {
        "name": "conta_corrente",
        "type": "string",
        "required": False,
        "rule": "Conta corrente do beneficiario.",
    },
    {
        "name": "agencia_codigo_beneficiario",
        "type": "string",
        "required": False,
        "rule": "Codigo agencia/beneficiario.",
    },
    {
        "name": "data_documento",
        "type": "date",
        "required": False,
        "rule": "Data de emissao do documento.",
    },
    {
        "name": "data_processamento",
        "type": "date",
        "required": False,
        "rule": "Data de processamento do boleto.",
    },
    # =========================================================
    # BENEFICIARIO / CREDOR
    # =========================================================
    {
        "name": "beneficiario_nome",
        "type": "string",
        "required": True,
        "rule": "Nome do beneficiario/credor.",
    },
    {
        "name": "beneficiario_nome_fantasia",
        "type": "string",
        "required": False,
        "rule": "Nome fantasia do beneficiario.",
    },
    {
        "name": "cnpj_cpf_beneficiario",
        "type": "string",
        "required": False,
        "rule": "CPF ou CNPJ do beneficiario; normalizar numerico.",
    },
    {
        "name": "endereco_beneficiario",
        "type": "string",
        "required": False,
        "rule": "Endereco completo do beneficiario.",
    },
    {
        "name": "cidade_beneficiario",
        "type": "string",
        "required": False,
        "rule": "Cidade do beneficiario.",
    },
    {
        "name": "uf_beneficiario",
        "type": "string",
        "required": False,
        "rule": "UF do beneficiario.",
    },
    {
        "name": "cep_beneficiario",
        "type": "string",
        "required": False,
        "rule": "CEP do beneficiario.",
    },
    # =========================================================
    # PAGADOR / SACADO
    # =========================================================
    {
        "name": "pagador_nome",
        "type": "string",
        "required": True,
        "rule": "Nome do pagador/sacado.",
    },
    {
        "name": "cnpj_cpf_pagador",
        "type": "string",
        "required": False,
        "rule": "CPF ou CNPJ do pagador; normalizar numerico.",
    },
    {
        "name": "endereco_pagador",
        "type": "string",
        "required": False,
        "rule": "Endereco completo do pagador.",
    },
    {
        "name": "cidade_pagador",
        "type": "string",
        "required": False,
        "rule": "Cidade do pagador.",
    },
    {
        "name": "uf_pagador",
        "type": "string",
        "required": False,
        "rule": "UF do pagador.",
    },
    {
        "name": "cep_pagador",
        "type": "string",
        "required": False,
        "rule": "CEP do pagador.",
    },
    {
        "name": "unidade",
        "type": "string",
        "required": False,
        "rule": "Numero da unidade/apartamento/sala.",
    },
    {
        "name": "bloco",
        "type": "string",
        "required": False,
        "rule": "Bloco ou torre da unidade.",
    },
    {
        "name": "sacador_avalista",
        "type": "string",
        "required": False,
        "rule": "Nome do sacador avalista.",
    },
    {
        "name": "cnpj_cpf_sacador_avalista",
        "type": "string",
        "required": False,
        "rule": "CPF/CNPJ do sacador avalista.",
    },
    # =========================================================
    # COBRANCA
    # =========================================================
    {
        "name": "tipo_cobranca",
        "type": "string",
        "required": False,
        "rule": "Tipo da cobranca: condominial, aluguel, acordo, taxa extra etc.",
    },
    {
        "name": "descricao",
        "type": "string",
        "required": False,
        "rule": "Descricao da cobranca.",
    },
    {
        "name": "instrucoes",
        "type": "string",
        "required": False,
        "rule": "Instrucoes do boleto.",
    },
    {
        "name": "demonstrativo",
        "type": "string",
        "required": False,
        "rule": "Texto demonstrativo da cobranca.",
    },
    {
        "name": "mes_referencia",
        "type": "string",
        "required": False,
        "rule": "Competencia da cobranca no formato MM/AAAA.",
    },
    {
        "name": "competencia_financeira",
        "type": "string",
        "required": False,
        "rule": "Competencia financeira principal da cobranca.",
    },
    {
        "name": "referencia",
        "type": "string",
        "required": False,
        "rule": "Referencia textual da cobranca.",
    },
    {
        "name": "itens_cobranca",
        "type": "array",
        "required": False,
        "rule": "Lista de itens detalhados da cobranca.",
    },
    {
        "name": "descontos_progressivos",
        "type": "array",
        "required": False,
        "rule": "Lista de descontos condicionados por data.",
    },
    {
        "name": "parcela_atual",
        "type": "integer",
        "required": False,
        "rule": "Numero da parcela atual.",
    },
    {
        "name": "total_parcelas",
        "type": "integer",
        "required": False,
        "rule": "Quantidade total de parcelas.",
    },
    # =========================================================
    # DATAS
    # =========================================================
    {
        "name": "data_vencimento",
        "type": "date",
        "required": True,
        "rule": "Data de vencimento.",
    },
    {
        "name": "data_limite_pagamento",
        "type": "date",
        "required": False,
        "rule": "Ultima data permitida para pagamento.",
    },
    # =========================================================
    # VALORES
    # =========================================================
    {
        "name": "valor_boleto",
        "type": "decimal",
        "required": True,
        "rule": "Valor principal do boleto.",
    },
    {
        "name": "valor_documento",
        "type": "decimal",
        "required": False,
        "rule": "Valor original do documento.",
    },
    {
        "name": "valor_cobrado",
        "type": "decimal",
        "required": False,
        "rule": "Valor efetivamente cobrado.",
    },
    {
        "name": "valor_liquido",
        "type": "decimal",
        "required": False,
        "rule": "Valor liquido esperado.",
    },
    {
        "name": "desconto",
        "type": "decimal",
        "required": False,
        "rule": "Valor de desconto.",
    },
    {
        "name": "abatimento",
        "type": "decimal",
        "required": False,
        "rule": "Valor de abatimento.",
    },
    {
        "name": "multa",
        "type": "decimal",
        "required": False,
        "rule": "Valor de multa.",
    },
    {
        "name": "multa_percentual",
        "type": "decimal",
        "required": False,
        "rule": "Percentual da multa aplicada apos vencimento.",
    },
    {
        "name": "juros",
        "type": "decimal",
        "required": False,
        "rule": "Valor de juros.",
    },
    {
        "name": "juros_percentual_dia",
        "type": "decimal",
        "required": False,
        "rule": "Percentual diario de juros.",
    },
    {
        "name": "mora_dia",
        "type": "decimal",
        "required": False,
        "rule": "Valor diario de mora.",
    },
    {
        "name": "outros_acrescimos",
        "type": "decimal",
        "required": False,
        "rule": "Outros acrescimos aplicados.",
    },
    {
        "name": "valor_pago",
        "type": "decimal",
        "required": False,
        "rule": "Valor efetivamente pago.",
    },
    {
        "name": "saldo_anterior",
        "type": "decimal",
        "required": False,
        "rule": "Saldo financeiro anterior.",
    },
    {
        "name": "saldo_atual",
        "type": "decimal",
        "required": False,
        "rule": "Saldo financeiro final.",
    },
    {
        "name": "total_receitas",
        "type": "decimal",
        "required": False,
        "rule": "Total de receitas do demonstrativo.",
    },
    {
        "name": "total_despesas",
        "type": "decimal",
        "required": False,
        "rule": "Total de despesas do demonstrativo.",
    },
    # =========================================================
    # PAGAMENTO
    # =========================================================
    {
        "name": "pagavel_em",
        "type": "string",
        "required": False,
        "rule": "Locais de pagamento permitidos.",
    },
    {
        "name": "aceita_pagamento_parcial",
        "type": "boolean",
        "required": False,
        "rule": "Indica se aceita pagamento parcial.",
    },
    {
        "name": "registrado",
        "type": "boolean",
        "required": False,
        "rule": "Indica se boleto registrado.",
    },
    # =========================================================
    # PIX / QR CODE
    # =========================================================
    {
        "name": "pix_copia_cola",
        "type": "string",
        "required": False,
        "rule": "Codigo Pix copia e cola.",
    },
    {
        "name": "pix_qrcode_presente",
        "type": "boolean",
        "required": False,
        "rule": "Indica presenca de QRCode Pix.",
    },
    {
        "name": "pix_chave",
        "type": "string",
        "required": False,
        "rule": "Chave Pix identificada.",
    },
    # =========================================================
    # DOCUMENTO / SEGMENTACAO
    # =========================================================
    {
        "name": "documento_hibrido",
        "type": "boolean",
        "required": False,
        "rule": "Indica boleto hibrido com Pix ou multiplos blocos financeiros.",
    },
    {
        "name": "blocos_semanticos",
        "type": "array",
        "required": False,
        "rule": "Lista de blocos semanticos identificados no documento.",
    },
    {
        "name": "demonstrativo_financeiro_presente",
        "type": "boolean",
        "required": False,
        "rule": "Indica existencia de demonstrativo financeiro.",
    },
    # =========================================================
    # METADADOS / OCR
    # =========================================================
    {
        "name": "codigo_moeda",
        "type": "string",
        "required": False,
        "rule": "Codigo da moeda no boleto.",
    },
    {
        "name": "especie_moeda",
        "type": "string",
        "required": False,
        "rule": "Especie da moeda.",
    },
    {
        "name": "texto_complementar",
        "type": "string",
        "required": False,
        "rule": "Informacoes adicionais.",
    },
    {
        "name": "observacoes",
        "type": "string",
        "required": False,
        "rule": "Observacoes gerais.",
    },
    {
        "name": "confidence_score",
        "type": "decimal",
        "required": False,
        "rule": "Confianca geral da extracao.",
    },
    {
        "name": "source_block",
        "type": "string",
        "required": False,
        "rule": "Bloco semantico onde o campo foi encontrado.",
    },
    {
        "name": "source_snippet",
        "type": "string",
        "required": False,
        "rule": "Trecho bruto utilizado para extracao.",
    },
    {
        "name": "arquivo_origem",
        "type": "string",
        "required": False,
        "rule": "Nome do arquivo original.",
    },
    {
        "name": "pagina_origem",
        "type": "integer",
        "required": False,
        "rule": "Pagina do PDF de origem.",
    },
]

PROMPT_INSTRUCTIONS = "\n".join(
    [
        "Voce e um sistema especialista em extracao de dados de boletos bancarios brasileiros.",
        "",
        "O texto fornecido pode vir de um PDF digital ou de OCR de imagem escaneada.",
        "",
        "Extraia os campos na lista de schemas e retorne um objeto contendo:",
        "- value: valor extraido (ou null)",
        "- confidence: numero entre 0 e 1 indicando a confianca na extracao",
        "",
        "Regras gerais:",
        "- Se nao encontrar um campo, value = null e confidence = 0",
        "- Nao invente valores",
        "- Use alta confianca apenas quando o valor estiver claramente explicito",
        "- Use confianca media quando houver pequena ambiguidade",
        "- Use baixa confianca quando houver inferencia",
        "- Corrija erros obvios de OCR nos campos numericos (ex: O/0, l/1)",
        "",
        "Regras especificas para boletos:",
        "- linha_digitavel: sequencia de 47 digitos (48 em arrecadacao); remover espacos e pontos. Com ruido de OCR, usar confianca baixa",
        "- codigo_barras: somente quando houver sequencia numerica de 44 digitos explicita; nao derivar da linha digitavel",
        "- beneficiario_nome: tambem rotulado como cedente; pagador_nome: tambem rotulado como sacado",
        "- valor_boleto: extrair da ficha de compensacao ou recibo do pagador, nunca do demonstrativo de receitas e despesas",
        "- multa, juros e mora_dia: extrair das instrucoes ou dos campos (+)Mora/Multa; nao confundir com valor por extenso",
        "- CNPJ e CPF: normalizar para apenas digitos",
        "- Datas: normalizar para YYYY-MM-DD",
        "- Valores monetarios: converter para float (R$ 1.470,15 -> 1470.15)",
    ]
)

PROMPT_GUARDRAILS = [
    "Nao inventar dados",
    "Usar texto exato",
    "Normalizar datas",
    "Extrair valores monetarios",
    "Tratar multiplas ocorrencias",
    "Ignorar rodape/cabecalho",
    "Priorizar tabelas",
    "Priorizar campos proximos ao rotulo",
]

EXAMPLES = [
    {
        "field": "tipo_documento",
        "expected": "boleto_condominial",
        "source": "CONDOMINIO DO EDIFICIO PLACE DE LA BASTILLE\n30/03/2026\n1.470,15",
    },
    {
        "field": "beneficiario_nome",
        "expected": "CONDOMINIO DO EDIFICIO PLACE DE LA BASTILLE",
        "source": "CONDOMINIO DO EDIFICIO PLACE DE LA BASTILLE",
    },
    {
        "field": "cnpj_cpf_beneficiario",
        "expected": "06067594000134",
        "source": "CNPJ: 06.067.594/0001-34",
    },
    {
        "field": "pagador_nome",
        "expected": "THAUANA SOUSA FERREIRA",
        "source": "THAUANA SOUSA FERREIRA",
    },
    {
        "field": "cnpj_cpf_pagador",
        "expected": "00568544390",
        "source": "CPF: 005.685.443-90",
    },
    {
        "field": "data_vencimento",
        "expected": "2026-03-30",
        "source": "30/03/2026",
    },
    {
        "field": "valor_boleto",
        "expected": "1470.15",
        "source": "1.470,15",
    },
    {
        "field": "linha_digitavel",
        "expected": "48190000030000515052925642660143814010000147015",
        "source": "48190.00003 00005.150529 25642.660143 8 14010000147015",
    },
    {
        "field": "descontos_progressivos",
        "expected": '[{"data_limite": "2026-03-10", "valor_desconto": 100.0, "valor_com_desconto": 1370.15}, {"data_limite": "2026-03-20", "valor_desconto": 50.0, "valor_com_desconto": 1420.15}]',
        "source": "Até dia 10/03/2026 conceder desconto de R$100,00, cobrar R$1.370,15.\nAté dia 20/03/2026 conceder desconto de R$50,00, cobrar R$1.420,15.",
    },
    {
        "field": "multa_percentual",
        "expected": "2.00",
        "source": "Após vencimento: Multa 2,00%= R$29,40",
    },
    {
        "field": "multa_valor",
        "expected": "29.40",
        "source": "Após vencimento: Multa 2,00%= R$29,40",
    },
    {
        "field": "juros_percentual_dia",
        "expected": "0.033",
        "source": "Juros 0,033% a.d.= R$0,49/dia",
    },
    {
        "field": "juros_valor_dia",
        "expected": "0.49",
        "source": "Juros 0,033% a.d.= R$0,49/dia",
    },
    {
        "field": "itens_cobranca",
        "expected": '[{"descricao": "Taxa Condominial", "valor": 1040.15}, {"descricao": "Rateio Extra SERV. DA FACHADA/ CXS AR CONDICION", "valor": 430.0}]',
        "source": "Composição da cobrança\nTaxa Condominial 1.040,15\nRateio Extra SERV. DA FACHADA/ CXS AR CONDICION - 430,00",
    },
    {
        "field": "parcelamento",
        "expected": '{"parcela_atual": 20, "total_parcelas": 24}',
        "source": "Parc. 20/24",
    },
    {
        "field": "unidade",
        "expected": "0103",
        "source": "Unidade\n0103 1",
    },
    {
        "field": "bloco",
        "expected": "1",
        "source": "Unidade\n0103 1",
    },
    {
        "field": "documento_hibrido",
        "expected": "true",
        "source": "Pix Copia e Cola\n00020126...",
    },
    {
        "field": "subdocumentos",
        "expected": '["boleto", "demonstrativo_financeiro", "composicao_cobranca", "bloco_postal"]',
        "source": "Pix Copia e Cola\n00020126...\nComposição da cobrança\nBloco Postal",
    },
    # Boleto Itau (ficha de compensacao fotografada)
    {
        "field": "nome_banco",
        "expected": "BANCO ITAU SA",
        "source": "BANCO ITAU SA | 341-7",
    },
    {"field": "codigo_banco", "expected": "341", "source": "BANCO ITAU SA | 341-7"},
    {
        "field": "linha_digitavel",
        "expected": "34191099902129632293283012370009712910000247555",
        "source": "34191.09990 21296.322932 83012.370009 7 12910000247555",
    },
    {
        "field": "pagavel_em",
        "expected": "Pagamento Aceito em qualquer Instituicao Bancaria",
        "source": "LOCAL DE PAGAMENTO\nPagamento Aceito em qualquer Instituicao Bancaria",
    },
    {
        "field": "beneficiario_nome",
        "expected": "BAHIANA DISTRIBUIDORA DE GAS",
        "source": "BENEFICIARIO: BAHIANA DISTRIBUIDORA DE GAS",
    },
    {
        "field": "cnpj_cpf_beneficiario",
        "expected": "46395687000102",
        "source": "CPF/CNPJ\n46395687000102",
    },
    {
        "field": "pagador_nome",
        "expected": "CONDOMINIO DO EDIFICIO RECIFE COLONIAL",
        "source": "PAGADOR\nCONDOMINIO DO EDIFICIO RECIFE COLONIAL - CPF/CNPJ: 02315237000197",
    },
    {
        "field": "cnpj_cpf_pagador",
        "expected": "02315237000197",
        "source": "CONDOMINIO DO EDIFICIO RECIFE COLONIAL - CPF/CNPJ: 02315237000197",
    },
    {
        "field": "nosso_numero",
        "expected": "109/99212963-2",
        "source": "NOSSO NUMERO\n109/99212963-2",
    },
    {
        "field": "numero_documento",
        "expected": "99212963",
        "source": "N. DOCUMENTO\n99212963",
    },
    {
        "field": "data_documento",
        "expected": "2025-11-24",
        "source": "DATA DOCUMENTO\n24/11/2025",
    },
    {
        "field": "data_vencimento",
        "expected": "2025-12-10",
        "source": "VENCIMENTO\n10/12/2025",
    },
    {
        "field": "valor_documento",
        "expected": "2475.55",
        "source": "(=)VALOR DOCUMENTO\n2.475,55",
    },
    {
        "field": "desconto",
        "expected": "null",
        "source": "(-)DESCONTO/ABATIMENTO\n(-)OUTRAS DEDUCOES",
    },
    {
        "field": "multa",
        "expected": "49.51",
        "source": "Apos o vencimento, cobrar multa de R$ 49,51.",
    },
    {
        "field": "mora_dia",
        "expected": "2.89",
        "source": "Apos o vencimento, cobrar mora diaria de R$ 2,89",
    },
    {
        "field": "valor_pago",
        "expected": "null",
        "source": "(=)VALOR COBRADO\nFICHA DE COMPENSACAO",
    },
    {
        "field": "instrucoes",
        "expected": "Apos o vencimento, cobrar multa de R$ 49,51. Apos o vencimento, cobrar mora diaria de R$ 2,89. Nao pagto implicara na inclusao em orgao de restricao. APOS VENC MULTA DE 2% + 0.1167% MORA DIARIA",
        "source": "INSTRUCOES DE RESPONSABILIDADE DO BENEFICIARIO\nApos o vencimento, cobrar multa de R$ 49,51. Apos o vencimento, cobrar mora di\naria de R$ 2,89\nNao pagto implicara na inclusao em orgao de restricao\nAPOS VENC MULTA DE 2% + 0.1167% MORA DIARIA",
    },
]

POST_PROCESSING = {
    "valor_boleto": {
        "type": "decimal",
        "required": True,
        "normalize_currency": True,
        "decimal_separator": ",",
        "thousand_separator": ".",
        "min": 0,
        "max": 99999999,
        "context_priority": [
            "recibo do pagador",
            "linha digitavel",
            "pagavel preferencialmente",
        ],
        "avoid_contexts": [
            "demonstrativo de receitas e despesas",
            "total de receitas",
            "saldo",
        ],
    },
    "linha_digitavel": {
        "type": "boleto_linha_digitavel",
        "required": True,
        "normalize_numeric": True,
        "remove_spaces": True,
        "remove_dots": True,
        "validate_checksum": True,
        "allowed_lengths": [47, 48],
    },
    "cnpj_cpf_beneficiario": {
        "type": "cpf_or_cnpj",
        "normalize_numeric": True,
        "validate_checksum": True,
    },
    "cnpj_cpf_pagador": {
        "type": "cpf_or_cnpj",
        "normalize_numeric": True,
        "validate_checksum": True,
    },
    "data_vencimento": {
        "type": "date",
        "required": True,
        "input_formats": ["DD/MM/YYYY"],
        "normalize_to": "YYYY-MM-DD",
    },
    "multa_percentual": {"type": "percentage", "min": 0, "max": 100},
    "multa_valor": {
        "type": "decimal",
        "normalize_currency": True,
        "decimal_separator": ",",
        "thousand_separator": ".",
        "min": 0,
    },
    "juros_percentual_dia": {"type": "percentage", "min": 0, "max": 10},
    "juros_valor_dia": {
        "type": "decimal",
        "normalize_currency": True,
        "decimal_separator": ",",
        "thousand_separator": ".",
        "min": 0,
    },
    "parcelamento": {"type": "fraction", "pattern": "(\\d{1,3})\\/(\\d{1,3})"},
    "beneficiario_nome": {
        "aliases": ["beneficiario", "cedente", "condominio", "administradora"],
    },
}

EXTRACTION_DEFINITION: dict = {
    "kind": "langextract_template",
    "model_name": MODEL_NAME,
    "document_type": "boleto",
    "status": "active",
    "fields": FIELDS,
    "prompt": {
        "instructions": PROMPT_INSTRUCTIONS,
        "guardrails": PROMPT_GUARDRAILS,
    },
    "examples": EXAMPLES,
    "reference_review": {
        "document_id": "",
        "filename": "",
        "ocr_quality": "",
        "recommended_action": "",
        "notes": "Semeado automaticamente na inicializacao do sistema.",
    },
    "post_processing": POST_PROCESSING,
    "traceability": {
        "require_source_span": True,
        "allow_visual_validation": True,
    },
}
