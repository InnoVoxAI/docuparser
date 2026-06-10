export const BOLETO_DEFAULT_RULES = {
    valor_boleto: {
        type: 'decimal',
        required: true,
        normalize_currency: true,
        decimal_separator: ',',
        thousand_separator: '.',
        min: 0,
        max: 99999999,
        context_priority: [
            'recibo do pagador',
            'linha digitavel',
            'pagavel preferencialmente',
        ],
        avoid_contexts: [
            'demonstrativo de receitas e despesas',
            'total de receitas',
            'saldo',
        ],
    },
    linha_digitavel: {
        type: 'boleto_linha_digitavel',
        required: true,
        normalize_numeric: true,
        remove_spaces: true,
        remove_dots: true,
        validate_checksum: true,
        allowed_lengths: [47, 48],
    },
    cnpj_cpf_beneficiario: {
        type: 'cpf_or_cnpj',
        normalize_numeric: true,
        validate_checksum: true,
    },
    cnpj_cpf_pagador: {
        type: 'cpf_or_cnpj',
        normalize_numeric: true,
        validate_checksum: true,
    },
    data_vencimento: {
        type: 'date',
        required: true,
        input_formats: ['DD/MM/YYYY'],
        normalize_to: 'YYYY-MM-DD',
    },
    multa_percentual: {
        type: 'percentage',
        min: 0,
        max: 100,
    },
    multa_valor: {
        type: 'decimal',
        normalize_currency: true,
        decimal_separator: ',',
        thousand_separator: '.',
        min: 0,
    },
    juros_percentual_dia: {
        type: 'percentage',
        min: 0,
        max: 10,
    },
    juros_valor_dia: {
        type: 'decimal',
        normalize_currency: true,
        decimal_separator: ',',
        thousand_separator: '.',
        min: 0,
    },
    parcelamento: {
        type: 'fraction',
        pattern: '(\\d{1,3})\\/(\\d{1,3})',
    },
    beneficiario_nome: {
        aliases: [
            'beneficiario',
            'cedente',
            'condominio',
            'administradora',
        ],
    },
    segment_document: {
        enabled: true,
        sections: [
            {
                name: 'boleto',
                anchors: [
                    'recibo do pagador',
                    'linha digitavel',
                    'pagavel preferencialmente',
                ],
            },
            {
                name: 'composicao_cobranca',
                anchors: [
                    'composição da cobrança',
                ],
            },
            {
                name: 'demonstrativo_financeiro',
                anchors: [
                    'demonstrativo de receitas e despesas',
                    'total de receitas',
                    'total de despesas',
                ],
            },
            {
                name: 'bloco_postal',
                anchors: [
                    'para uso dos correios',
                    'remetente',
                ],
            },
        ],
    },
    normalize_document_numbers: {
        remove_non_numeric: true,
    },
}
