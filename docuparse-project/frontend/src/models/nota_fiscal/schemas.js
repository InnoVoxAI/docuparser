export const NOTA_FISCAL_DEFAULT_SCHEMA_ID = 'nota_fiscal_default'
export const NOTA_FISCAL_DEFAULT_MODEL_NAME = 'NOTA FISCAL DEFAULT'

// export const NOTA_FISCAL_DEFAULT_FIELDS = [
//     { name: 'fornecedor_nome', type: 'string', required: true, rule: 'Razao social do fornecedor.' },
//     { name: 'tomador_nome', type: 'string', required: true, rule: 'Razao social do tomador.' },
//     { name: 'cnpj_fornecedor', type: 'string', required: true, rule: 'CNPJ do fornecedor; normalizar numerico.' },
//     { name: 'numero_nota', type: 'string', required: true, rule: 'Numero da nota fiscal.' },
//     { name: 'descricao_servico', type: 'string', required: false, rule: 'Descricao do servico.' },
//     { name: 'valor_nota', type: 'decimal', required: true, rule: 'Converter para float.' },
//     { name: 'retencao', type: 'boolean', required: false, rule: 'True/false indicando retencao.' },
//     { name: 'cnpj_tomador', type: 'string', required: false, rule: 'CNPJ do tomador; normalizar numerico.' },
// ]

export const NOTA_FISCAL_DEFAULT_FIELDS = [

    // =========================================================
    // IDENTIFICACAO DO DOCUMENTO
    // =========================================================

    {
        name: 'tipo_documento',
        type: 'string',
        required: true,
        rule: 'Tipo do documento fiscal: NFE, NFSE, DANFE, CTE etc.'
    },

    {
        name: 'modelo_documento',
        type: 'string',
        required: false,
        rule: 'Modelo fiscal do documento.'
    },

    {
        name: 'numero_nota',
        type: 'string',
        required: true,
        rule: 'Numero da nota fiscal.'
    },

    {
        name: 'serie_nota',
        type: 'string',
        required: false,
        rule: 'Serie da nota fiscal.'
    },

    {
        name: 'codigo_verificacao',
        type: 'string',
        required: false,
        rule: 'Codigo de verificacao da nota.'
    },

    {
        name: 'chave_acesso',
        type: 'string',
        required: false,
        rule: 'Chave de acesso da NF-e/NFS-e; normalizar numerico.'
    },

    {
        name: 'protocolo_autorizacao',
        type: 'string',
        required: false,
        rule: 'Numero do protocolo de autorizacao.'
    },

    {
        name: 'data_emissao',
        type: 'date',
        required: true,
        rule: 'Data de emissao da nota fiscal.'
    },

    {
        name: 'hora_emissao',
        type: 'string',
        required: false,
        rule: 'Hora da emissao.'
    },

    {
        name: 'competencia',
        type: 'date',
        required: false,
        rule: 'Competencia da nota fiscal.'
    },

    // =========================================================
    // EMITENTE / FORNECEDOR
    // =========================================================

    {
        name: 'fornecedor_nome',
        type: 'string',
        required: true,
        rule: 'Razao social do fornecedor.'
    },

    {
        name: 'fornecedor_nome_fantasia',
        type: 'string',
        required: false,
        rule: 'Nome fantasia do fornecedor.'
    },

    {
        name: 'cnpj_fornecedor',
        type: 'string',
        required: true,
        rule: 'CNPJ do fornecedor; normalizar numerico.'
    },

    {
        name: 'cpf_fornecedor',
        type: 'string',
        required: false,
        rule: 'CPF do fornecedor se pessoa fisica.'
    },

    {
        name: 'inscricao_estadual_fornecedor',
        type: 'string',
        required: false,
        rule: 'Inscricao estadual do fornecedor.'
    },

    {
        name: 'inscricao_municipal_fornecedor',
        type: 'string',
        required: false,
        rule: 'Inscricao municipal do fornecedor.'
    },

    {
        name: 'regime_tributario',
        type: 'string',
        required: false,
        rule: 'Regime tributario da empresa.'
    },

    {
        name: 'simples_nacional',
        type: 'boolean',
        required: false,
        rule: 'Indica se optante pelo simples nacional.'
    },

    {
        name: 'email_fornecedor',
        type: 'string',
        required: false,
        rule: 'Email do fornecedor.'
    },

    {
        name: 'telefone_fornecedor',
        type: 'string',
        required: false,
        rule: 'Telefone do fornecedor.'
    },

    // =========================================================
    // ENDERECO FORNECEDOR
    // =========================================================

    {
        name: 'endereco_fornecedor',
        type: 'string',
        required: false,
        rule: 'Endereco completo do fornecedor.'
    },

    {
        name: 'logradouro_fornecedor',
        type: 'string',
        required: false,
        rule: 'Logradouro do fornecedor.'
    },

    {
        name: 'numero_endereco_fornecedor',
        type: 'string',
        required: false,
        rule: 'Numero do endereco.'
    },

    {
        name: 'bairro_fornecedor',
        type: 'string',
        required: false,
        rule: 'Bairro do fornecedor.'
    },

    {
        name: 'cidade_fornecedor',
        type: 'string',
        required: false,
        rule: 'Cidade do fornecedor.'
    },

    {
        name: 'uf_fornecedor',
        type: 'string',
        required: false,
        rule: 'UF do fornecedor.'
    },

    {
        name: 'cep_fornecedor',
        type: 'string',
        required: false,
        rule: 'CEP do fornecedor.'
    },

    // =========================================================
    // TOMADOR / CLIENTE
    // =========================================================

    {
        name: 'tomador_nome',
        type: 'string',
        required: true,
        rule: 'Razao social do tomador.'
    },

    {
        name: 'cnpj_tomador',
        type: 'string',
        required: false,
        rule: 'CNPJ do tomador; normalizar numerico.'
    },

    {
        name: 'cpf_tomador',
        type: 'string',
        required: false,
        rule: 'CPF do tomador.'
    },

    {
        name: 'inscricao_estadual_tomador',
        type: 'string',
        required: false,
        rule: 'Inscricao estadual do tomador.'
    },

    {
        name: 'inscricao_municipal_tomador',
        type: 'string',
        required: false,
        rule: 'Inscricao municipal do tomador.'
    },

    {
        name: 'email_tomador',
        type: 'string',
        required: false,
        rule: 'Email do tomador.'
    },

    {
        name: 'telefone_tomador',
        type: 'string',
        required: false,
        rule: 'Telefone do tomador.'
    },

    // =========================================================
    // ENDERECO TOMADOR
    // =========================================================

    {
        name: 'endereco_tomador',
        type: 'string',
        required: false,
        rule: 'Endereco completo do tomador.'
    },

    {
        name: 'cidade_tomador',
        type: 'string',
        required: false,
        rule: 'Cidade do tomador.'
    },

    {
        name: 'uf_tomador',
        type: 'string',
        required: false,
        rule: 'UF do tomador.'
    },

    {
        name: 'cep_tomador',
        type: 'string',
        required: false,
        rule: 'CEP do tomador.'
    },

    // =========================================================
    // SERVICO / PRODUTO
    // =========================================================

    {
        name: 'descricao_servico',
        type: 'string',
        required: false,
        rule: 'Descricao do servico.'
    },

    {
        name: 'codigo_servico',
        type: 'string',
        required: false,
        rule: 'Codigo municipal/nacional do servico.'
    },

    {
        name: 'natureza_operacao',
        type: 'string',
        required: false,
        rule: 'Natureza da operacao.'
    },

    {
        name: 'local_prestacao',
        type: 'string',
        required: false,
        rule: 'Cidade/local da prestacao do servico.'
    },

    // =========================================================
    // VALORES
    // =========================================================

    {
        name: 'valor_servico',
        type: 'decimal',
        required: true,
        rule: 'Valor bruto do servico.'
    },

    {
        name: 'valor_produtos',
        type: 'decimal',
        required: false,
        rule: 'Valor total dos produtos.'
    },

    {
        name: 'valor_nota',
        type: 'decimal',
        required: true,
        rule: 'Valor total da nota.'
    },

    {
        name: 'valor_liquido',
        type: 'decimal',
        required: false,
        rule: 'Valor liquido da nota.'
    },

    {
        name: 'desconto',
        type: 'decimal',
        required: false,
        rule: 'Valor total de descontos.'
    },

    {
        name: 'desconto_condicionado',
        type: 'decimal',
        required: false,
        rule: 'Desconto condicionado.'
    },

    {
        name: 'desconto_incondicionado',
        type: 'decimal',
        required: false,
        rule: 'Desconto incondicionado.'
    },

    // =========================================================
    // IMPOSTOS
    // =========================================================

    {
        name: 'issqn',
        type: 'decimal',
        required: false,
        rule: 'Valor do ISSQN.'
    },

    {
        name: 'aliquota_issqn',
        type: 'decimal',
        required: false,
        rule: 'Aliquota ISSQN.'
    },

    {
        name: 'icms',
        type: 'decimal',
        required: false,
        rule: 'Valor do ICMS.'
    },

    {
        name: 'ipi',
        type: 'decimal',
        required: false,
        rule: 'Valor do IPI.'
    },

    {
        name: 'pis',
        type: 'decimal',
        required: false,
        rule: 'Valor do PIS.'
    },

    {
        name: 'cofins',
        type: 'decimal',
        required: false,
        rule: 'Valor do COFINS.'
    },

    {
        name: 'csll',
        type: 'decimal',
        required: false,
        rule: 'Valor da CSLL.'
    },

    {
        name: 'irrf',
        type: 'decimal',
        required: false,
        rule: 'Valor do IRRF.'
    },

    {
        name: 'inss',
        type: 'decimal',
        required: false,
        rule: 'Valor do INSS.'
    },

    // =========================================================
    // RETENCOES
    // =========================================================

    {
        name: 'retencao',
        type: 'boolean',
        required: false,
        rule: 'True/false indicando retencao.'
    },

    {
        name: 'iss_retido',
        type: 'boolean',
        required: false,
        rule: 'Indica ISS retido.'
    },

    {
        name: 'valor_retido',
        type: 'decimal',
        required: false,
        rule: 'Valor total retido.'
    },

    // =========================================================
    // INFORMACOES OPERACIONAIS
    // =========================================================

    {
        name: 'municipio_incidencia',
        type: 'string',
        required: false,
        rule: 'Municipio de incidencia tributaria.'
    },

    {
        name: 'pais_prestacao',
        type: 'string',
        required: false,
        rule: 'Pais da prestacao do servico.'
    },

    {
        name: 'tributacao',
        type: 'string',
        required: false,
        rule: 'Tipo de tributacao aplicada.'
    },

    {
        name: 'regime_especial_tributacao',
        type: 'string',
        required: false,
        rule: 'Regime especial de tributacao.'
    },

    {
        name: 'beneficio_fiscal',
        type: 'string',
        required: false,
        rule: 'Beneficio fiscal aplicado.'
    },

    // =========================================================
    // METADADOS
    // =========================================================

    {
        name: 'municipio_emissao',
        type: 'string',
        required: false,
        rule: 'Municipio emissor da nota.'
    },

    {
        name: 'uf_emissao',
        type: 'string',
        required: false,
        rule: 'UF emissora.'
    },

    {
        name: 'ambiente',
        type: 'string',
        required: false,
        rule: 'Homologacao ou producao.'
    },

    {
        name: 'qr_code_presente',
        type: 'boolean',
        required: false,
        rule: 'Indica se existe QRCode no documento.'
    },

    {
        name: 'texto_complementar',
        type: 'string',
        required: false,
        rule: 'Informacoes complementares.'
    },

]


function scoreNotaFiscalText(rawText) {
    if (!rawText) {
        return 0
    }
    const text = String(rawText).toLowerCase()
    let score = 0
    const keywords = [
        'nota fiscal',
        'nf-e',
        'nfe',
        'chave de acesso',
        'icms',
        'ipi',
        'pis',
        'cofins',
        'iss',
        'tomador',
        'fornecedor',
        'descricao',
        'quantidade',
        'valor unitario',
        'valor total',
        'produtos',
        'servicos',
    ]
    keywords.forEach((keyword) => {
        if (text.includes(keyword)) {
            score += 1
        }
    })
    const accessKeyRegex = /\b\d{44}\b/
    if (accessKeyRegex.test(text)) {
        score += 3
    }
    return score
}

export function isLikelyNotaFiscalText(rawText, threshold = 4) {
    return scoreNotaFiscalText(rawText) >= threshold
}
