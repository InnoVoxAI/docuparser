export const NOTA_FISCAL_DEFAULT_RULES = {
    valor_nota: {
        type: 'decimal',
        required: true,
        normalize_currency: true,
        decimal_separator: ',',
        thousand_separator: '.',
        min: 0,
        max: 999999999,
    },
    data_emissao: {
        type: 'date',
        required: true,
        input_formats: ['DD/MM/YYYY', 'DD/MM/YYYY HH:mm:ss'],
        normalize_to: 'YYYY-MM-DD',
    },
    cnpj_fornecedor: {
        type: 'cnpj',
        required: true,
        normalize_numeric: true,
        validate_checksum: true,
    },
    cpf_tomador: {
        type: 'cpf',
        required: false,
        normalize_numeric: true,
        validate_checksum: true,
    },
    iss_retido: {
        type: 'boolean',
        truthy: ['sim', 'retido', 'true'],
        falsy: ['nao', 'não', 'nao retido', 'não retido', '-'],
    },
    uf_emissao: {
        type: 'enum',
        allowed: [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF',
            'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
            'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS',
            'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
        ],
    },
}
