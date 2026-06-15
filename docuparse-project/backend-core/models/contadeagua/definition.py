from __future__ import annotations

SCHEMA_ID = "conta_agua_default"
VERSION = "v1"
MODEL_NAME = "CONTA AGUA DEFAULT"

FIELDS = [

    # =========================================================
    # IDENTIFICACAO DO DOCUMENTO
    # =========================================================

    {"name": "tipo_documento", "type": "string", "required": True, "rule": "Tipo do documento: conta_agua."},
    {"name": "numero_documento", "type": "string", "required": False, "rule": "Numero do documento ou fatura."},
    {"name": "numero_contrato", "type": "string", "required": False, "rule": "Numero do contrato de fornecimento."},
    {"name": "referencia", "type": "string", "required": True, "rule": "Competencia da fatura no formato MM/AAAA. Ignorar digito verificador apos hifen."},
    {"name": "data_vencimento", "type": "date", "required": True, "rule": "Data de vencimento da fatura."},
    {"name": "data_emissao", "type": "date", "required": False, "rule": "Data de emissao da fatura."},

    # =========================================================
    # EMISSOR / CONCESSIONARIA
    # =========================================================

    {"name": "nome_emissor", "type": "string", "required": False, "rule": "Nome da concessionaria emissora (ex: COMPESA, SABESP, CEDAE, EMBASA)."},
    {"name": "cnpj_emissor", "type": "string", "required": True, "rule": "CNPJ da concessionaria; normalizar numerico."},
    {"name": "inscricao_estadual_emissor", "type": "string", "required": False, "rule": "Inscricao estadual da concessionaria."},
    {"name": "endereco_emissor", "type": "string", "required": False, "rule": "Endereco da concessionaria emissora."},
    {"name": "escritorio", "type": "string", "required": False, "rule": "Escritorio regional responsavel pelo atendimento."},

    # =========================================================
    # CLIENTE / IMOVEL
    # =========================================================

    {"name": "nome_cliente", "type": "string", "required": True, "rule": "Razao social ou nome do titular do contrato."},
    {"name": "endereco_cliente", "type": "string", "required": False, "rule": "Endereco do imovel faturado."},
    {"name": "cidade_cliente", "type": "string", "required": False, "rule": "Cidade do imovel."},
    {"name": "uf_cliente", "type": "string", "required": False, "rule": "UF do imovel."},
    {"name": "cep_cliente", "type": "string", "required": False, "rule": "CEP do imovel."},

    # =========================================================
    # IDENTIFICADORES DO CONTRATO
    # =========================================================

    {"name": "matricula", "type": "string", "required": True, "rule": "Matricula do cliente junto a concessionaria; normalizar numerico."},
    {"name": "inscricao_cliente", "type": "string", "required": False, "rule": "Inscricao ou codigo do imovel."},
    {"name": "codigo_ligacao", "type": "string", "required": False, "rule": "Codigo da ligacao de agua ou esgoto."},
    {"name": "inicio_relacao", "type": "date", "required": False, "rule": "Data de inicio do contrato ou ligacao."},

    # =========================================================
    # MEDICAO E CONSUMO
    # =========================================================

    {"name": "hidrometro", "type": "string", "required": False, "rule": "Numero ou codigo do hidrometro."},
    {"name": "leitura_anterior", "type": "decimal", "required": False, "rule": "Leitura anterior do hidrometro em m³."},
    {"name": "leitura_atual", "type": "decimal", "required": False, "rule": "Leitura atual do hidrometro em m³."},
    {"name": "leitura_faturada", "type": "decimal", "required": False, "rule": "Leitura efetivamente faturada em m³."},
    {"name": "consumo_agua", "type": "decimal", "required": False, "rule": "Volume de agua consumido em m³."},
    {"name": "consumo_esgoto", "type": "decimal", "required": False, "rule": "Volume de esgoto faturado em m³."},
    {"name": "tipo_consumo", "type": "string", "required": False, "rule": "Tipo de consumo: medido, minimo_fixo ou estimado."},

    # =========================================================
    # CATEGORIA / ECONOMIAS
    # =========================================================

    {"name": "categoria", "type": "string", "required": False, "rule": "Categoria do imovel: residencial, comercial, industrial ou publico."},
    {"name": "numero_economias", "type": "integer", "required": False, "rule": "Numero de economias ou unidades faturadas."},

    # =========================================================
    # VALORES
    # =========================================================

    {"name": "total_pagar", "type": "decimal", "required": True, "rule": "Valor total a pagar. Extrair do campo TOTAL A PAGAR, nao dos tributos ou subtotais."},
    {"name": "tarifa_minima", "type": "decimal", "required": False, "rule": "Valor unitario da tarifa minima por economia."},
    {"name": "valor_agua", "type": "decimal", "required": False, "rule": "Valor referente ao consumo de agua."},
    {"name": "valor_esgoto", "type": "decimal", "required": False, "rule": "Valor referente ao servico de coleta de esgoto."},
    {"name": "debito_anterior", "type": "decimal", "required": False, "rule": "Saldo devedor de competencias anteriores."},
    {"name": "multa", "type": "decimal", "required": False, "rule": "Multa por atraso de pagamento."},
    {"name": "juros", "type": "decimal", "required": False, "rule": "Juros por atraso de pagamento."},
    {"name": "desconto_social", "type": "decimal", "required": False, "rule": "Desconto de tarifa social aplicado."},
    {"name": "doacao", "type": "decimal", "required": False, "rule": "Valor de doacao ao fundo social (ex: PRO-CRIANCA, FUNDO SOCIAL)."},

    # =========================================================
    # TRIBUTOS
    # =========================================================

    {"name": "pis_percentual", "type": "decimal", "required": False, "rule": "Aliquota do PIS em percentual."},
    {"name": "pis_valor", "type": "decimal", "required": False, "rule": "Valor monetario do PIS."},
    {"name": "cofins_percentual", "type": "decimal", "required": False, "rule": "Aliquota do COFINS em percentual."},
    {"name": "cofins_valor", "type": "decimal", "required": False, "rule": "Valor monetario do COFINS."},
    {"name": "tributos", "type": "json", "required": False, "rule": "Array de tributos com: [{nome, percentual, base_calculo, valor}]."},

    # =========================================================
    # SERVICOS COBRADOS
    # =========================================================

    {"name": "descricao_servicos", "type": "json", "required": False, "rule": "Array de servicos cobrados: [{descricao, valor}]."},

    # =========================================================
    # PAGAMENTO
    # =========================================================

    {"name": "linha_digitavel", "type": "string", "required": False, "rule": "Linha digitavel ou codigo de barras para pagamento; normalizar numerico removendo espacos e hifens."},
    {"name": "opcao_debito_automatico", "type": "string", "required": False, "rule": "Codigo para adesao ao debito automatico."},

    # =========================================================
    # METADADOS
    # =========================================================

    {"name": "emitido_por", "type": "string", "required": False, "rule": "Canal de emissao: INTERNET, AGENCIA, AUTOATENDIMENTO etc."},
    {"name": "situacao_agua", "type": "string", "required": False, "rule": "Situacao da ligacao de agua: ligado, cortado, suprimido."},
    {"name": "situacao_esgoto", "type": "string", "required": False, "rule": "Situacao da ligacao de esgoto: ligado, cortado, suprimido."},
]

PROMPT_INSTRUCTIONS = "\n".join([
    "Voce e um sistema especialista em extracao de dados de faturas de agua e esgoto brasileiras.",
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
    "- Corrija erros obvios de OCR ao interpretar (ex: O/0, l/1, B/8)",
    "",
    "Regras especificas para faturas de agua:",
    "- total_pagar: extrair EXCLUSIVAMENTE do campo 'TOTAL A PAGAR'. Nao confundir com base de calculo dos tributos, tarifa minima ou subtotais",
    "- referencia: extrair somente MM/AAAA. Ignorar digito verificador apos hifen (ex: '02/2026-9' -> '02/2026')",
    "- linha_digitavel: normalizar removendo todos os hifens e espacos. Formato de concessionaria tem 4 grupos",
    "- matricula: normalizar numerico removendo espacos. Ignorar referencia de competencia que aparece na mesma linha",
    "- tipo_consumo: 'NAO MEDIDO' ou 'MIN FIXAD' indica minimo_fixo. 'MEDIDO' indica medido",
    "- tributos: PIS e COFINS aparecem em tabela separada com colunas percentual, base de calculo e valor",
    "- numero_economias: aparece como 'NNN UNIDADES' ou 'ECONOMIAS: NNN'",
    "- valores monetarios: converter BR para float (R$ 5.925,50 -> 5925.50)",
])

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
    {"field": "tipo_documento", "expected": "conta_agua", "source": "FATURA MENSAL DE AGUA E ESGOTO"},
    {"field": "cnpj_emissor", "expected": "09769035000164", "source": "CNPJ: 09.769.035/0001-64"},
    {"field": "numero_documento", "expected": "20260254994214", "source": "N Documento: 20260254994214"},
    {"field": "numero_contrato", "expected": "1473288", "source": "N Contrato: 1473288"},
    {"field": "nome_cliente", "expected": "CONDOMINIO DO EDIFICIO PARK FLEMING", "source": "DADOS DO CLIENTE\nCONDOMINIO DO EDIFICIO PARK FLEMING"},
    {"field": "matricula", "expected": "054994214", "source": "MATRICULA:\n054994214 02/2026-9"},
    {"field": "referencia", "expected": "02/2026", "source": "054994214 02/2026-9"},
    {"field": "data_vencimento", "expected": "2026-03-20", "source": "VENCIMENTO: 20/03/2026"},
    {"field": "data_emissao", "expected": "2026-03-18", "source": "Emitido em: 18/03/2026"},
    {"field": "total_pagar", "expected": "5925.50", "source": "TOTAL A PAGAR:\n5.925,50"},
    {"field": "tarifa_minima", "expected": "61.77", "source": "TARIFA MINIMA 61,77 POR UNIDADE MINIMO 5.924,50"},
    {"field": "numero_economias", "expected": "50", "source": "RESIDENCIAL 050 UNIDADES"},
    {"field": "linha_digitavel", "expected": "828400000599255000183407054994214013022026900034", "source": "82840000059-9 25500018340-7 05499421401-3 02202690003-4"},
    {"field": "cofins_percentual", "expected": "3.00", "source": "COFINS\n3,00\n5.924,50\n177,74"},
    {"field": "cofins_valor", "expected": "177.74", "source": "COFINS\n3,00\n5.924,50\n177,74"},
    {"field": "pis_percentual", "expected": "0.65", "source": "PIS 0,65\n5.924,50\n38,51"},
    {"field": "pis_valor", "expected": "38.51", "source": "PIS 0,65\n5.924,50\n38,51"},
    {"field": "tipo_consumo", "expected": "minimo_fixo", "source": "NAO MEDIDO /MIN FIXAD"},
    {"field": "categoria", "expected": "residencial", "source": "ESGOTO\n RESIDENCIAL 050 UNIDADES"},
    {"field": "doacao", "expected": "1.00", "source": "DOACAO AO PRO-CRIANCA 02/2026 1,00"},
    {"field": "emitido_por", "expected": "INTERNET", "source": "Emitido por: INTERNET Emitido em: 18/03/2026"},
]

POST_PROCESSING = {
    "total_pagar": {
        "type": "decimal",
        "required": True,
        "normalize_currency": True,
        "decimal_separator": ",",
        "thousand_separator": ".",
        "min": 0,
        "max": 9999999,
        "context_priority": ["total a pagar", "vencimento", "codigo de barras"],
        "avoid_contexts": ["minimo", "tarifa minima", "base de calculo", "historico de consumo"],
    },
    "tarifa_minima": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "valor_agua": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "valor_esgoto": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "debito_anterior": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "multa": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "juros": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "desconto_social": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "doacao": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "pis_percentual": {"type": "percentage", "min": 0, "max": 100},
    "pis_valor": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "cofins_percentual": {"type": "percentage", "min": 0, "max": 100},
    "cofins_valor": {"type": "decimal", "normalize_currency": True, "decimal_separator": ",", "thousand_separator": ".", "min": 0},
    "data_vencimento": {"type": "date", "required": True, "input_formats": ["DD/MM/YYYY"], "normalize_to": "YYYY-MM-DD"},
    "data_emissao": {"type": "date", "input_formats": ["DD/MM/YYYY", "DD/MM/YYYY HH:mm:ss"], "normalize_to": "YYYY-MM-DD"},
    "inicio_relacao": {"type": "date", "input_formats": ["DD/MM/YYYY"], "normalize_to": "YYYY-MM-DD"},
    "referencia": {"type": "string", "pattern": "(\\d{2})/(\\d{4})", "normalize": "extract_mm_yyyy"},
    "cnpj_emissor": {"type": "cnpj", "required": True, "normalize_numeric": True, "validate_checksum": True},
    "matricula": {"type": "string", "normalize_numeric": True},
    "linha_digitavel": {
        "type": "conta_consumo_linha_digitavel",
        "normalize_numeric": True,
        "remove_spaces": True,
        "remove_dots": True,
        "remove_hyphens": True,
        "allowed_lengths": [47, 48],
    },
    "numero_economias": {"type": "integer", "min": 1, "max": 9999},
    "tipo_consumo": {
        "type": "enum",
        "allowed": ["medido", "minimo_fixo", "estimado"],
        "mapping": {
            "nao medido": "minimo_fixo",
            "min fixad": "minimo_fixo",
            "minimo fixo": "minimo_fixo",
            "estimado": "estimado",
            "medido": "medido",
        },
    },
    "categoria": {
        "type": "enum",
        "allowed": ["residencial", "comercial", "industrial", "publico"],
        "mapping": {
            "residencial": "residencial",
            "comercial": "comercial",
            "industrial": "industrial",
            "publico": "publico",
        },
    },
}

EXTRACTION_DEFINITION: dict = {
    "kind": "langextract_template",
    "model_name": MODEL_NAME,
    "document_type": "conta_agua",
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
