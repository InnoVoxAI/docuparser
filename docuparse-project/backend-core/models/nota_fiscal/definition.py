from __future__ import annotations

SCHEMA_ID = "nota_fiscal_default"
VERSION = "v1"
MODEL_NAME = "NOTA FISCAL DEFAULT"

FIELDS = [

    # =========================================================
    # IDENTIFICACAO DO DOCUMENTO
    # =========================================================

    {"name": "tipo_documento", "type": "string", "required": True, "rule": "Tipo do documento fiscal: NFE, NFSE, DANFE, CTE etc."},
    {"name": "modelo_documento", "type": "string", "required": False, "rule": "Modelo fiscal do documento."},
    {"name": "numero_nota", "type": "string", "required": True, "rule": "Numero da nota fiscal."},
    {"name": "serie_nota", "type": "string", "required": False, "rule": "Serie da nota fiscal."},
    {"name": "codigo_verificacao", "type": "string", "required": False, "rule": "Codigo de verificacao da nota."},
    {"name": "chave_acesso", "type": "string", "required": False, "rule": "Chave de acesso da NF-e/NFS-e; normalizar numerico."},
    {"name": "protocolo_autorizacao", "type": "string", "required": False, "rule": "Numero do protocolo de autorizacao."},
    {"name": "data_emissao", "type": "date", "required": True, "rule": "Data de emissao da nota fiscal."},
    {"name": "hora_emissao", "type": "string", "required": False, "rule": "Hora da emissao."},
    {"name": "competencia", "type": "date", "required": False, "rule": "Competencia da nota fiscal."},

    # =========================================================
    # EMITENTE / FORNECEDOR
    # =========================================================

    {"name": "fornecedor_nome", "type": "string", "required": True, "rule": "Razao social do fornecedor."},
    {"name": "fornecedor_nome_fantasia", "type": "string", "required": False, "rule": "Nome fantasia do fornecedor."},
    {"name": "cnpj_fornecedor", "type": "string", "required": True, "rule": "CNPJ do fornecedor; normalizar numerico."},
    {"name": "cpf_fornecedor", "type": "string", "required": False, "rule": "CPF do fornecedor se pessoa fisica."},
    {"name": "inscricao_estadual_fornecedor", "type": "string", "required": False, "rule": "Inscricao estadual do fornecedor."},
    {"name": "inscricao_municipal_fornecedor", "type": "string", "required": False, "rule": "Inscricao municipal do fornecedor."},
    {"name": "regime_tributario", "type": "string", "required": False, "rule": "Regime tributario da empresa."},
    {"name": "simples_nacional", "type": "boolean", "required": False, "rule": "Indica se optante pelo simples nacional."},
    {"name": "email_fornecedor", "type": "string", "required": False, "rule": "Email do fornecedor."},
    {"name": "telefone_fornecedor", "type": "string", "required": False, "rule": "Telefone do fornecedor."},

    # =========================================================
    # ENDERECO FORNECEDOR
    # =========================================================

    {"name": "endereco_fornecedor", "type": "string", "required": False, "rule": "Endereco completo do fornecedor."},
    {"name": "logradouro_fornecedor", "type": "string", "required": False, "rule": "Logradouro do fornecedor."},
    {"name": "numero_endereco_fornecedor", "type": "string", "required": False, "rule": "Numero do endereco."},
    {"name": "bairro_fornecedor", "type": "string", "required": False, "rule": "Bairro do fornecedor."},
    {"name": "cidade_fornecedor", "type": "string", "required": False, "rule": "Cidade do fornecedor."},
    {"name": "uf_fornecedor", "type": "string", "required": False, "rule": "UF do fornecedor."},
    {"name": "cep_fornecedor", "type": "string", "required": False, "rule": "CEP do fornecedor."},

    # =========================================================
    # TOMADOR / CLIENTE
    # =========================================================

    {"name": "tomador_nome", "type": "string", "required": True, "rule": "Razao social do tomador."},
    {"name": "cnpj_tomador", "type": "string", "required": False, "rule": "CNPJ do tomador; normalizar numerico."},
    {"name": "cpf_tomador", "type": "string", "required": False, "rule": "CPF do tomador."},
    {"name": "inscricao_estadual_tomador", "type": "string", "required": False, "rule": "Inscricao estadual do tomador."},
    {"name": "inscricao_municipal_tomador", "type": "string", "required": False, "rule": "Inscricao municipal do tomador."},
    {"name": "email_tomador", "type": "string", "required": False, "rule": "Email do tomador."},
    {"name": "telefone_tomador", "type": "string", "required": False, "rule": "Telefone do tomador."},

    # =========================================================
    # ENDERECO TOMADOR
    # =========================================================

    {"name": "endereco_tomador", "type": "string", "required": False, "rule": "Endereco completo do tomador."},
    {"name": "cidade_tomador", "type": "string", "required": False, "rule": "Cidade do tomador."},
    {"name": "uf_tomador", "type": "string", "required": False, "rule": "UF do tomador."},
    {"name": "cep_tomador", "type": "string", "required": False, "rule": "CEP do tomador."},

    # =========================================================
    # SERVICO / PRODUTO
    # =========================================================

    {"name": "descricao_servico", "type": "string", "required": False, "rule": "Descricao do servico."},
    {"name": "codigo_servico", "type": "string", "required": False, "rule": "Codigo municipal/nacional do servico."},
    {"name": "natureza_operacao", "type": "string", "required": False, "rule": "Natureza da operacao."},
    {"name": "local_prestacao", "type": "string", "required": False, "rule": "Cidade/local da prestacao do servico."},

    # =========================================================
    # VALORES
    # =========================================================

    {"name": "valor_servico", "type": "decimal", "required": True, "rule": "Valor bruto do servico."},
    {"name": "valor_produtos", "type": "decimal", "required": False, "rule": "Valor total dos produtos."},
    {"name": "valor_nota", "type": "decimal", "required": True, "rule": "Valor total da nota."},
    {"name": "valor_liquido", "type": "decimal", "required": False, "rule": "Valor liquido da nota."},
    {"name": "desconto", "type": "decimal", "required": False, "rule": "Valor total de descontos."},
    {"name": "desconto_condicionado", "type": "decimal", "required": False, "rule": "Desconto condicionado."},
    {"name": "desconto_incondicionado", "type": "decimal", "required": False, "rule": "Desconto incondicionado."},

    # =========================================================
    # IMPOSTOS
    # =========================================================

    {"name": "issqn", "type": "decimal", "required": False, "rule": "Valor do ISSQN."},
    {"name": "aliquota_issqn", "type": "decimal", "required": False, "rule": "Aliquota ISSQN."},
    {"name": "icms", "type": "decimal", "required": False, "rule": "Valor do ICMS."},
    {"name": "ipi", "type": "decimal", "required": False, "rule": "Valor do IPI."},
    {"name": "pis", "type": "decimal", "required": False, "rule": "Valor do PIS."},
    {"name": "cofins", "type": "decimal", "required": False, "rule": "Valor do COFINS."},
    {"name": "csll", "type": "decimal", "required": False, "rule": "Valor da CSLL."},
    {"name": "irrf", "type": "decimal", "required": False, "rule": "Valor do IRRF."},
    {"name": "inss", "type": "decimal", "required": False, "rule": "Valor do INSS."},

    # =========================================================
    # RETENCOES
    # =========================================================

    {"name": "retencao", "type": "boolean", "required": False, "rule": "True/false indicando retencao."},
    {"name": "iss_retido", "type": "boolean", "required": False, "rule": "Indica ISS retido."},
    {"name": "valor_retido", "type": "decimal", "required": False, "rule": "Valor total retido."},

    # =========================================================
    # INFORMACOES OPERACIONAIS
    # =========================================================

    {"name": "municipio_incidencia", "type": "string", "required": False, "rule": "Municipio de incidencia tributaria."},
    {"name": "pais_prestacao", "type": "string", "required": False, "rule": "Pais da prestacao do servico."},
    {"name": "tributacao", "type": "string", "required": False, "rule": "Tipo de tributacao aplicada."},
    {"name": "regime_especial_tributacao", "type": "string", "required": False, "rule": "Regime especial de tributacao."},
    {"name": "beneficio_fiscal", "type": "string", "required": False, "rule": "Beneficio fiscal aplicado."},

    # =========================================================
    # METADADOS
    # =========================================================

    {"name": "municipio_emissao", "type": "string", "required": False, "rule": "Municipio emissor da nota."},
    {"name": "uf_emissao", "type": "string", "required": False, "rule": "UF emissora."},
    {"name": "ambiente", "type": "string", "required": False, "rule": "Homologacao ou producao."},
    {"name": "qr_code_presente", "type": "boolean", "required": False, "rule": "Indica se existe QRCode no documento."},
    {"name": "texto_complementar", "type": "string", "required": False, "rule": "Informacoes complementares."},
]

PROMPT_INSTRUCTIONS = "\n".join([
    "Voce e um sistema especialista em extracao de dados de notas fiscais brasileiras.",
    "",
    "O texto fornecido pode vir de um PDF digital ou de OCR de imagem escaneada.",
    "",
    "Extraia os campos na lista de schemas e retorne um objeto contendo:",
    "- value: valor extraido (ou null)",
    "- confidence: numero entre 0 e 1 indicando a confianca na extracao",
    "",
    "Regras:",
    "- Se nao encontrar um campo, value = null e confidence = 0",
    "- Nao invente valores",
    "- Use alta confianca apenas quando o valor estiver claramente explicito",
    "- Use confianca media quando houver pequena ambiguidade",
    "- Use baixa confianca quando houver inferencia",
    "- Corrija erros obvios de OCR ao interpretar (ex: O/0, l/1)",
    "- CNPJ e CPF: normalizar para apenas digitos",
    "- Datas: normalizar para YYYY-MM-DD",
    "- Valores monetarios: converter para float (R$ 1.250,00 -> 1250.00)",
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
    {"field": "tipo_documento", "expected": "NFS-e", "source": "DANFSe v1.0\nDocumento Auxiliar da NFS-e"},
    {"field": "numero_nota", "expected": "6", "source": "Numero da NFS-e\n6"},
    {"field": "data_emissao", "expected": "2025-12-12", "source": "Competencia da NFS-e\n12/12/2025"},
    {"field": "competencia", "expected": "2025-12-12", "source": "Competencia da NFS-e\n12/12/2025"},
    {"field": "cnpj_fornecedor", "expected": "08629869000101", "source": "CNPJ / CPF / NIF\n08.629.869/0001-01"},
    {"field": "fornecedor_nome", "expected": "MUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS", "source": "Nome / Nome Empresarial\nMUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS"},
    {"field": "cnpj_tomador", "expected": "02315237000197", "source": "TOMADOR DO SERVICO\n02.315.237/0001-97"},
    {"field": "tomador_nome", "expected": "CONDOMINIO DO EDIFICIO RECIFE COLONIAL", "source": "CONDOMINIO DO EDIFICIO RECIFE COLONIAL"},
    {"field": "valor_servico", "expected": "10000.00", "source": "Valor do Servico\nR$ 10.000,00"},
    {"field": "valor_nota", "expected": "10000.00", "source": "Valor Liquido da NFS-e\nR$ 10.000,00"},
    {"field": "valor_liquido", "expected": "10000.00", "source": "Valor Liquido da NFS-e\nR$ 10.000,00"},
    {"field": "iss_retido", "expected": "false", "source": "ISS Retido\nnao retido"},
    {"field": "simples_nacional", "expected": "true", "source": "Simples Nacional\nsim"},
    {"field": "telefone_fornecedor", "expected": "null", "source": "Telefone\n-"},
    {"field": "cnpj_fornecedor", "expected": "08629869000101", "source": "CNPJ / CPF / NIF\n08 629 869 0001 01"},
]

POST_PROCESSING = {
    "valor_nota": {
        "type": "decimal",
        "required": True,
        "normalize_currency": True,
        "decimal_separator": ",",
        "thousand_separator": ".",
        "min": 0,
        "max": 999999999,
    },
    "data_emissao": {
        "type": "date",
        "required": True,
        "input_formats": ["DD/MM/YYYY", "DD/MM/YYYY HH:mm:ss"],
        "normalize_to": "YYYY-MM-DD",
    },
    "cnpj_fornecedor": {
        "type": "cnpj",
        "required": True,
        "normalize_numeric": True,
        "validate_checksum": True,
    },
    "cpf_tomador": {
        "type": "cpf",
        "required": False,
        "normalize_numeric": True,
        "validate_checksum": True,
    },
    "iss_retido": {
        "type": "boolean",
        "truthy": ["sim", "retido", "true"],
        "falsy": ["nao", "nao retido", "-"],
    },
    "uf_emissao": {
        "type": "enum",
        "allowed": [
            "AC", "AL", "AP", "AM", "BA", "CE", "DF",
            "ES", "GO", "MA", "MT", "MS", "MG", "PA",
            "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
            "RO", "RR", "SC", "SP", "SE", "TO",
        ],
    },
}

EXTRACTION_DEFINITION: dict = {
    "kind": "langextract_template",
    "model_name": MODEL_NAME,
    "document_type": "nota_fiscal",
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
