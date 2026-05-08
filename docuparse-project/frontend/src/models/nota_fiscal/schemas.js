export const NOTA_FISCAL_DEFAULT_SCHEMA_ID = 'nota_fiscal_default'
export const NOTA_FISCAL_DEFAULT_MODEL_NAME = 'NOTA FISCAL DEFAULT'

export const NOTA_FISCAL_DEFAULT_FIELDS = [
    { name: 'fornecedor_nome', type: 'string', required: true, rule: 'Razao social do fornecedor.' },
    { name: 'tomador_nome', type: 'string', required: true, rule: 'Razao social do tomador.' },
    { name: 'cnpj_fornecedor', type: 'string', required: true, rule: 'CNPJ do fornecedor; normalizar numerico.' },
    { name: 'numero_nota', type: 'string', required: true, rule: 'Numero da nota fiscal.' },
    { name: 'descricao_servico', type: 'string', required: false, rule: 'Descricao do servico.' },
    { name: 'valor_nota', type: 'decimal', required: true, rule: 'Converter para float.' },
    { name: 'retencao', type: 'boolean', required: false, rule: 'True/false indicando retencao.' },
    { name: 'cnpj_tomador', type: 'string', required: false, rule: 'CNPJ do tomador; normalizar numerico.' },
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
