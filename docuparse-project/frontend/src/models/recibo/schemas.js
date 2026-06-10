export const DEFAULT_SCHEMA_ID = 'recibo_servico'
export const DEFAULT_MODEL_NAME = 'Recibo de servico'

export const DEFAULT_LANGEXTRACT_FIELDS = [
    { name: 'fornecedor_nome', type: 'string', required: true, rule: 'Extrair exatamente como aparece no documento.' },
    { name: 'fornecedor_cnpj', type: 'cnpj', required: false, rule: 'Normalizar para 00.000.000/0000-00 quando existir.' },
    { name: 'valor_total', type: 'decimal', required: true, rule: 'Usar o valor total final e converter virgula decimal.' },
    { name: 'vencimento', type: 'date', required: false, rule: 'Normalizar para YYYY-MM-DD.' },
]
