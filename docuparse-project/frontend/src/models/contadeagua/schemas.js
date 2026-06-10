export const CONTA_AGUA_DEFAULT_SCHEMA_ID = 'conta_agua_default'
export const CONTA_AGUA_DEFAULT_MODEL_NAME = 'CONTA AGUA DEFAULT'

export const CONTA_AGUA_DEFAULT_FIELDS = [

    // =========================================================
    // IDENTIFICACAO DO DOCUMENTO
    // =========================================================

    {
        name: 'tipo_documento',
        type: 'string',
        required: true,
        rule: 'Tipo do documento: conta_agua.',
    },

    {
        name: 'numero_documento',
        type: 'string',
        required: false,
        rule: 'Numero do documento ou fatura.',
    },

    {
        name: 'numero_contrato',
        type: 'string',
        required: false,
        rule: 'Numero do contrato de fornecimento.',
    },

    {
        name: 'referencia',
        type: 'string',
        required: true,
        rule: 'Competencia da fatura no formato MM/AAAA. Ignorar digito verificador apos hifen.',
    },

    {
        name: 'data_vencimento',
        type: 'date',
        required: true,
        rule: 'Data de vencimento da fatura.',
    },

    {
        name: 'data_emissao',
        type: 'date',
        required: false,
        rule: 'Data de emissao da fatura.',
    },

    // =========================================================
    // EMISSOR / CONCESSIONARIA
    // =========================================================

    {
        name: 'nome_emissor',
        type: 'string',
        required: false,
        rule: 'Nome da concessionaria emissora (ex: COMPESA, SABESP, CEDAE, EMBASA).',
    },

    {
        name: 'cnpj_emissor',
        type: 'string',
        required: true,
        rule: 'CNPJ da concessionaria; normalizar numerico.',
    },

    {
        name: 'inscricao_estadual_emissor',
        type: 'string',
        required: false,
        rule: 'Inscricao estadual da concessionaria.',
    },

    {
        name: 'endereco_emissor',
        type: 'string',
        required: false,
        rule: 'Endereco da concessionaria emissora.',
    },

    {
        name: 'escritorio',
        type: 'string',
        required: false,
        rule: 'Escritorio regional responsavel pelo atendimento.',
    },

    // =========================================================
    // CLIENTE / IMOVEL
    // =========================================================

    {
        name: 'nome_cliente',
        type: 'string',
        required: true,
        rule: 'Razao social ou nome do titular do contrato.',
    },

    {
        name: 'endereco_cliente',
        type: 'string',
        required: false,
        rule: 'Endereco do imovel faturado.',
    },

    {
        name: 'cidade_cliente',
        type: 'string',
        required: false,
        rule: 'Cidade do imovel.',
    },

    {
        name: 'uf_cliente',
        type: 'string',
        required: false,
        rule: 'UF do imovel.',
    },

    {
        name: 'cep_cliente',
        type: 'string',
        required: false,
        rule: 'CEP do imovel.',
    },

    // =========================================================
    // IDENTIFICADORES DO CONTRATO
    // =========================================================

    {
        name: 'matricula',
        type: 'string',
        required: true,
        rule: 'Matricula do cliente junto a concessionaria; normalizar numerico.',
    },

    {
        name: 'inscricao_cliente',
        type: 'string',
        required: false,
        rule: 'Inscricao ou codigo do imovel.',
    },

    {
        name: 'codigo_ligacao',
        type: 'string',
        required: false,
        rule: 'Codigo da ligacao de agua ou esgoto.',
    },

    {
        name: 'inicio_relacao',
        type: 'date',
        required: false,
        rule: 'Data de inicio do contrato ou ligacao.',
    },

    // =========================================================
    // MEDICAO E CONSUMO
    // =========================================================

    {
        name: 'hidrometro',
        type: 'string',
        required: false,
        rule: 'Numero ou codigo do hidrometro.',
    },

    {
        name: 'leitura_anterior',
        type: 'decimal',
        required: false,
        rule: 'Leitura anterior do hidrometro em m³.',
    },

    {
        name: 'leitura_atual',
        type: 'decimal',
        required: false,
        rule: 'Leitura atual do hidrometro em m³.',
    },

    {
        name: 'leitura_faturada',
        type: 'decimal',
        required: false,
        rule: 'Leitura efetivamente faturada em m³.',
    },

    {
        name: 'consumo_agua',
        type: 'decimal',
        required: false,
        rule: 'Volume de agua consumido em m³.',
    },

    {
        name: 'consumo_esgoto',
        type: 'decimal',
        required: false,
        rule: 'Volume de esgoto faturado em m³.',
    },

    {
        name: 'tipo_consumo',
        type: 'string',
        required: false,
        rule: 'Tipo de consumo: medido, minimo_fixo ou estimado.',
    },

    // =========================================================
    // CATEGORIA / ECONOMIAS
    // =========================================================

    {
        name: 'categoria',
        type: 'string',
        required: false,
        rule: 'Categoria do imovel: residencial, comercial, industrial ou publico.',
    },

    {
        name: 'numero_economias',
        type: 'integer',
        required: false,
        rule: 'Numero de economias ou unidades faturadas.',
    },

    // =========================================================
    // VALORES
    // =========================================================

    {
        name: 'total_pagar',
        type: 'decimal',
        required: true,
        rule: 'Valor total a pagar. Extrair do campo TOTAL A PAGAR, nao dos tributos ou subtotais.',
    },

    {
        name: 'tarifa_minima',
        type: 'decimal',
        required: false,
        rule: 'Valor unitario da tarifa minima por economia.',
    },

    {
        name: 'valor_agua',
        type: 'decimal',
        required: false,
        rule: 'Valor referente ao consumo de agua.',
    },

    {
        name: 'valor_esgoto',
        type: 'decimal',
        required: false,
        rule: 'Valor referente ao servico de coleta de esgoto.',
    },

    {
        name: 'debito_anterior',
        type: 'decimal',
        required: false,
        rule: 'Saldo devedor de competencias anteriores.',
    },

    {
        name: 'multa',
        type: 'decimal',
        required: false,
        rule: 'Multa por atraso de pagamento.',
    },

    {
        name: 'juros',
        type: 'decimal',
        required: false,
        rule: 'Juros por atraso de pagamento.',
    },

    {
        name: 'desconto_social',
        type: 'decimal',
        required: false,
        rule: 'Desconto de tarifa social aplicado.',
    },

    {
        name: 'doacao',
        type: 'decimal',
        required: false,
        rule: 'Valor de doacao ao fundo social (ex: PRO-CRIANCA, FUNDO SOCIAL).',
    },

    // =========================================================
    // TRIBUTOS
    // =========================================================

    {
        name: 'pis_percentual',
        type: 'decimal',
        required: false,
        rule: 'Aliquota do PIS em percentual.',
    },

    {
        name: 'pis_valor',
        type: 'decimal',
        required: false,
        rule: 'Valor monetario do PIS.',
    },

    {
        name: 'cofins_percentual',
        type: 'decimal',
        required: false,
        rule: 'Aliquota do COFINS em percentual.',
    },

    {
        name: 'cofins_valor',
        type: 'decimal',
        required: false,
        rule: 'Valor monetario do COFINS.',
    },

    {
        name: 'tributos',
        type: 'json',
        required: false,
        rule: 'Array de tributos com: [{nome, percentual, base_calculo, valor}].',
    },

    // =========================================================
    // SERVICOS COBRADOS
    // =========================================================

    {
        name: 'descricao_servicos',
        type: 'json',
        required: false,
        rule: 'Array de servicos cobrados: [{descricao, valor}].',
    },

    // =========================================================
    // PAGAMENTO
    // =========================================================

    {
        name: 'linha_digitavel',
        type: 'string',
        required: false,
        rule: 'Linha digitavel ou codigo de barras para pagamento; normalizar numerico removendo espacos e hifens.',
    },

    {
        name: 'opcao_debito_automatico',
        type: 'string',
        required: false,
        rule: 'Codigo para adesao ao debito automatico.',
    },

    // =========================================================
    // METADADOS
    // =========================================================

    {
        name: 'emitido_por',
        type: 'string',
        required: false,
        rule: 'Canal de emissao: INTERNET, AGENCIA, AUTOATENDIMENTO etc.',
    },

    {
        name: 'situacao_agua',
        type: 'string',
        required: false,
        rule: 'Situacao da ligacao de agua: ligado, cortado, suprimido.',
    },

    {
        name: 'situacao_esgoto',
        type: 'string',
        required: false,
        rule: 'Situacao da ligacao de esgoto: ligado, cortado, suprimido.',
    },

]


function scoreContaAguaText(rawText) {
    if (!rawText) {
        return 0
    }
    const text = String(rawText).toLowerCase()
    let score = 0
    const keywords = [
        'fatura',
        'água',
        'agua',
        'esgoto',
        'consumo',
        'matrícula',
        'matricula',
        'hidrômetro',
        'hidrometro',
        'tarifa',
        'concessionaria',
        'compesa',
        'sabesp',
        'cedae',
        'embasa',
        'copasa',
        'sanepar',
        'cagece',
        'leitura',
        'economia',
    ]
    keywords.forEach((keyword) => {
        if (text.includes(keyword)) {
            score += 1
        }
    })
    return score
}

export function isLikelyContaAguaText(rawText, threshold = 3) {
    return scoreContaAguaText(rawText) >= threshold
}
