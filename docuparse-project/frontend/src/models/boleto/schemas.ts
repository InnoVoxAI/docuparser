export const BOLETO_DEFAULT_SCHEMA_ID = 'boleto_default'
export const BOLETO_DEFAULT_MODEL_NAME = 'BOLETO DEFAULT'

export const BOLETO_DEFAULT_FIELDS = [

    // =========================================================
    // IDENTIFICACAO DO BOLETO
    // =========================================================

    {
        name: 'tipo_documento',
        type: 'string',
        required: false,
        rule: 'Tipo do documento: boleto bancario, ficha de compensacao, arrecadacao etc.'
    },

    {
        name: 'categoria_documento',
        type: 'string',
        required: false,
        rule: 'Categoria do documento: condominio, aluguel, escolar, bancario etc.'
    },

    {
        name: 'codigo_barras',
        type: 'string',
        required: false,
        rule: 'Codigo de barras numerico com 44 digitos.'
    },

    {
        name: 'linha_digitavel',
        type: 'string',
        required: true,
        rule: 'Sequencia da linha digitavel; remover espacos e pontuacao.'
    },

    {
        name: 'nosso_numero',
        type: 'string',
        required: false,
        rule: 'Nosso numero do boleto.'
    },

    {
        name: 'numero_documento',
        type: 'string',
        required: false,
        rule: 'Numero do documento ou referencia interna.'
    },

    {
        name: 'numero_controle',
        type: 'string',
        required: false,
        rule: 'Numero de controle interno do boleto.'
    },

    {
        name: 'carteira',
        type: 'string',
        required: false,
        rule: 'Codigo da carteira bancária.'
    },

    {
        name: 'especie_documento',
        type: 'string',
        required: false,
        rule: 'Especie do documento: DM, DS, NP etc.'
    },

    {
        name: 'aceite',
        type: 'boolean',
        required: false,
        rule: 'Indica aceite do documento.'
    },

    // =========================================================
    // BANCO / EMISSAO
    // =========================================================

    {
        name: 'codigo_banco',
        type: 'string',
        required: false,
        rule: 'Codigo do banco emissor.'
    },

    {
        name: 'nome_banco',
        type: 'string',
        required: false,
        rule: 'Nome do banco emissor.'
    },

    {
        name: 'instituicao_cobranca',
        type: 'string',
        required: false,
        rule: 'Instituicao financeira ou fintech responsavel pela cobranca.'
    },

    {
        name: 'agencia',
        type: 'string',
        required: false,
        rule: 'Numero da agencia.'
    },

    {
        name: 'conta_corrente',
        type: 'string',
        required: false,
        rule: 'Conta corrente do beneficiario.'
    },

    {
        name: 'agencia_codigo_beneficiario',
        type: 'string',
        required: false,
        rule: 'Codigo agencia/beneficiario.'
    },

    {
        name: 'data_documento',
        type: 'date',
        required: false,
        rule: 'Data de emissao do documento.'
    },

    {
        name: 'data_processamento',
        type: 'date',
        required: false,
        rule: 'Data de processamento do boleto.'
    },

    // =========================================================
    // BENEFICIARIO / CREDOR
    // =========================================================

    {
        name: 'beneficiario_nome',
        type: 'string',
        required: true,
        rule: 'Nome do beneficiario/credor.'
    },

    {
        name: 'beneficiario_nome_fantasia',
        type: 'string',
        required: false,
        rule: 'Nome fantasia do beneficiario.'
    },

    {
        name: 'cnpj_cpf_beneficiario',
        type: 'string',
        required: false,
        rule: 'CPF ou CNPJ do beneficiario; normalizar numerico.'
    },

    {
        name: 'endereco_beneficiario',
        type: 'string',
        required: false,
        rule: 'Endereco completo do beneficiario.'
    },

    {
        name: 'cidade_beneficiario',
        type: 'string',
        required: false,
        rule: 'Cidade do beneficiario.'
    },

    {
        name: 'uf_beneficiario',
        type: 'string',
        required: false,
        rule: 'UF do beneficiario.'
    },

    {
        name: 'cep_beneficiario',
        type: 'string',
        required: false,
        rule: 'CEP do beneficiario.'
    },

    // =========================================================
    // PAGADOR / SACADO
    // =========================================================

    {
        name: 'pagador_nome',
        type: 'string',
        required: true,
        rule: 'Nome do pagador/sacado.'
    },

    {
        name: 'cnpj_cpf_pagador',
        type: 'string',
        required: false,
        rule: 'CPF ou CNPJ do pagador; normalizar numerico.'
    },

    {
        name: 'endereco_pagador',
        type: 'string',
        required: false,
        rule: 'Endereco completo do pagador.'
    },

    {
        name: 'cidade_pagador',
        type: 'string',
        required: false,
        rule: 'Cidade do pagador.'
    },

    {
        name: 'uf_pagador',
        type: 'string',
        required: false,
        rule: 'UF do pagador.'
    },

    {
        name: 'cep_pagador',
        type: 'string',
        required: false,
        rule: 'CEP do pagador.'
    },

    {
        name: 'unidade',
        type: 'string',
        required: false,
        rule: 'Numero da unidade/apartamento/sala.'
    },

    {
        name: 'bloco',
        type: 'string',
        required: false,
        rule: 'Bloco ou torre da unidade.'
    },

    {
        name: 'sacador_avalista',
        type: 'string',
        required: false,
        rule: 'Nome do sacador avalista.'
    },

    {
        name: 'cnpj_cpf_sacador_avalista',
        type: 'string',
        required: false,
        rule: 'CPF/CNPJ do sacador avalista.'
    },

    // =========================================================
    // COBRANCA
    // =========================================================

    {
        name: 'tipo_cobranca',
        type: 'string',
        required: false,
        rule: 'Tipo da cobranca: condominial, aluguel, acordo, taxa extra etc.'
    },

    {
        name: 'descricao',
        type: 'string',
        required: false,
        rule: 'Descricao da cobranca.'
    },

    {
        name: 'instrucoes',
        type: 'string',
        required: false,
        rule: 'Instrucoes do boleto.'
    },

    {
        name: 'demonstrativo',
        type: 'string',
        required: false,
        rule: 'Texto demonstrativo da cobranca.'
    },

    {
        name: 'mes_referencia',
        type: 'string',
        required: false,
        rule: 'Competencia da cobranca no formato MM/AAAA.'
    },

    {
        name: 'competencia_financeira',
        type: 'string',
        required: false,
        rule: 'Competencia financeira principal da cobranca.'
    },

    {
        name: 'referencia',
        type: 'string',
        required: false,
        rule: 'Referencia textual da cobranca.'
    },

    {
        name: 'itens_cobranca',
        type: 'array',
        required: false,
        rule: 'Lista de itens detalhados da cobranca.'
    },

    {
        name: 'descontos_progressivos',
        type: 'array',
        required: false,
        rule: 'Lista de descontos condicionados por data.'
    },

    {
        name: 'parcela_atual',
        type: 'integer',
        required: false,
        rule: 'Numero da parcela atual.'
    },

    {
        name: 'total_parcelas',
        type: 'integer',
        required: false,
        rule: 'Quantidade total de parcelas.'
    },

    // =========================================================
    // DATAS
    // =========================================================

    {
        name: 'data_vencimento',
        type: 'date',
        required: true,
        rule: 'Data de vencimento.'
    },

    {
        name: 'data_limite_pagamento',
        type: 'date',
        required: false,
        rule: 'Ultima data permitida para pagamento.'
    },

    // =========================================================
    // VALORES
    // =========================================================

    {
        name: 'valor_boleto',
        type: 'decimal',
        required: true,
        rule: 'Valor principal do boleto.'
    },

    {
        name: 'valor_documento',
        type: 'decimal',
        required: false,
        rule: 'Valor original do documento.'
    },

    {
        name: 'valor_cobrado',
        type: 'decimal',
        required: false,
        rule: 'Valor efetivamente cobrado.'
    },

    {
        name: 'valor_liquido',
        type: 'decimal',
        required: false,
        rule: 'Valor liquido esperado.'
    },

    {
        name: 'desconto',
        type: 'decimal',
        required: false,
        rule: 'Valor de desconto.'
    },

    {
        name: 'abatimento',
        type: 'decimal',
        required: false,
        rule: 'Valor de abatimento.'
    },

    {
        name: 'multa',
        type: 'decimal',
        required: false,
        rule: 'Valor de multa.'
    },

    {
        name: 'multa_percentual',
        type: 'decimal',
        required: false,
        rule: 'Percentual da multa aplicada apos vencimento.'
    },

    {
        name: 'juros',
        type: 'decimal',
        required: false,
        rule: 'Valor de juros.'
    },

    {
        name: 'juros_percentual_dia',
        type: 'decimal',
        required: false,
        rule: 'Percentual diario de juros.'
    },

    {
        name: 'mora_dia',
        type: 'decimal',
        required: false,
        rule: 'Valor diario de mora.'
    },

    {
        name: 'outros_acrescimos',
        type: 'decimal',
        required: false,
        rule: 'Outros acrescimos aplicados.'
    },

    {
        name: 'valor_pago',
        type: 'decimal',
        required: false,
        rule: 'Valor efetivamente pago.'
    },

    {
        name: 'saldo_anterior',
        type: 'decimal',
        required: false,
        rule: 'Saldo financeiro anterior.'
    },

    {
        name: 'saldo_atual',
        type: 'decimal',
        required: false,
        rule: 'Saldo financeiro final.'
    },

    {
        name: 'total_receitas',
        type: 'decimal',
        required: false,
        rule: 'Total de receitas do demonstrativo.'
    },

    {
        name: 'total_despesas',
        type: 'decimal',
        required: false,
        rule: 'Total de despesas do demonstrativo.'
    },

    // =========================================================
    // PAGAMENTO
    // =========================================================

    {
        name: 'pagavel_em',
        type: 'string',
        required: false,
        rule: 'Locais de pagamento permitidos.'
    },

    {
        name: 'aceita_pagamento_parcial',
        type: 'boolean',
        required: false,
        rule: 'Indica se aceita pagamento parcial.'
    },

    {
        name: 'registrado',
        type: 'boolean',
        required: false,
        rule: 'Indica se boleto registrado.'
    },

    // =========================================================
    // PIX / QR CODE
    // =========================================================

    {
        name: 'pix_copia_cola',
        type: 'string',
        required: false,
        rule: 'Codigo Pix copia e cola.'
    },

    {
        name: 'pix_qrcode_presente',
        type: 'boolean',
        required: false,
        rule: 'Indica presenca de QRCode Pix.'
    },

    {
        name: 'pix_chave',
        type: 'string',
        required: false,
        rule: 'Chave Pix identificada.'
    },

    // =========================================================
    // DOCUMENTO / SEGMENTACAO
    // =========================================================

    {
        name: 'documento_hibrido',
        type: 'boolean',
        required: false,
        rule: 'Indica boleto hibrido com Pix ou multiplos blocos financeiros.'
    },

    {
        name: 'blocos_semanticos',
        type: 'array',
        required: false,
        rule: 'Lista de blocos semanticos identificados no documento.'
    },

    {
        name: 'demonstrativo_financeiro_presente',
        type: 'boolean',
        required: false,
        rule: 'Indica existencia de demonstrativo financeiro.'
    },

    // =========================================================
    // METADADOS / OCR
    // =========================================================

    {
        name: 'codigo_moeda',
        type: 'string',
        required: false,
        rule: 'Codigo da moeda no boleto.'
    },

    {
        name: 'especie_moeda',
        type: 'string',
        required: false,
        rule: 'Especie da moeda.'
    },

    {
        name: 'texto_complementar',
        type: 'string',
        required: false,
        rule: 'Informacoes adicionais.'
    },

    {
        name: 'observacoes',
        type: 'string',
        required: false,
        rule: 'Observacoes gerais.'
    },

    {
        name: 'confidence_score',
        type: 'decimal',
        required: false,
        rule: 'Confianca geral da extracao.'
    },

    {
        name: 'source_block',
        type: 'string',
        required: false,
        rule: 'Bloco semantico onde o campo foi encontrado.'
    },

    {
        name: 'source_snippet',
        type: 'string',
        required: false,
        rule: 'Trecho bruto utilizado para extracao.'
    },

    {
        name: 'arquivo_origem',
        type: 'string',
        required: false,
        rule: 'Nome do arquivo original.'
    },

    {
        name: 'pagina_origem',
        type: 'integer',
        required: false,
        rule: 'Pagina do PDF de origem.'
    },

]

function scoreBoletoText(rawText) {
    if (!rawText) {
        return 0
    }
    const text = String(rawText).toLowerCase()
    let score = 0
    const keywords = [
        'boleto',
        'linha digitavel',
        'beneficiario',
        'pagador',
        'vencimento',
        'nosso numero',
        'valor',
    ]
    keywords.forEach((keyword) => {
        if (text.includes(keyword)) {
            score += 1
        }
    })
    const linhaDigitavelRegex = /\b\d{5}\.?\d{5}\s+\d{5}\.?\d{6}\s+\d{5}\.?\d{6}\s+\d\s+\d{14}\b/
    const barcodeRegex = /\b\d{44}\b/
    if (linhaDigitavelRegex.test(text)) {
        score += 3
    }
    if (barcodeRegex.test(text)) {
        score += 2
    }
    return score
}

export function isLikelyBoletoText(rawText, threshold = 4) {
    return scoreBoletoText(rawText) >= threshold
}
