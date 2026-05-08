export const BOLETO_DEFAULT_SCHEMA_ID = 'boleto_default'
export const BOLETO_DEFAULT_MODEL_NAME = 'BOLETO DEFAULT'

export const BOLETO_DEFAULT_FIELDS = [
    { name: 'beneficiario_nome', type: 'string', required: true, rule: 'Administradora ou condominio credor.' },
    { name: 'pagador_nome', type: 'string', required: true, rule: 'Condomino ou empresa devedora.' },
    { name: 'cnpj_cpf_beneficiario', type: 'string', required: false, rule: 'Aceita CPF ou CNPJ; normalizar numerico.' },
    { name: 'cnpj_cpf_pagador', type: 'string', required: false, rule: 'Aceita CPF ou CNPJ; normalizar numerico.' },
    { name: 'numero_documento', type: 'string', required: false, rule: 'Nosso numero ou referencia interna.' },
    { name: 'descricao', type: 'string', required: false, rule: 'Descricao da cobranca.' },
    { name: 'mes_referencia', type: 'string', required: false, rule: 'Formato MM/AAAA quando existir.' },
    { name: 'data_vencimento', type: 'date', required: true, rule: 'Formato DD/MM/AAAA.' },
    { name: 'valor_boleto', type: 'decimal', required: true, rule: 'Converter para float.' },
    { name: 'linha_digitavel', type: 'string', required: true, rule: 'Sequencia de ~47 digitos, sem espacos.' },
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
