// =========================================================
// Exemplo 1 — NFS-e completa
// =========================================================
// Todos os campos extraídos de uma NFS-e padrão.
// Servem de referência few-shot para o LLM.

// =========================================================
// Exemplo 2 — campo ausente retorna null
// =========================================================
// Quando o campo existe no layout mas o valor é "-" ou em branco,
// o resultado esperado é null.

// =========================================================
// Exemplo 3 — OCR corrompido: CNPJ com espaços
// =========================================================
// Mesmo que o OCR insira espaços no CNPJ, o valor deve ser
// normalizado para apenas dígitos.

export const NOTA_FISCAL_DEFAULT_EXAMPLES = [
    {
        field: 'tipo_documento',
        expected: 'NFS-e',
        source: 'DANFSe v1.0\nDocumento Auxiliar da NFS-e',
    },
    {
        field: 'numero_nota',
        expected: '6',
        source: 'Número da NFS-e\n6',
    },
    {
        field: 'data_emissao',
        expected: '2025-12-12',
        source: 'Competência da NFS-e\n12/12/2025',
    },
    {
        field: 'competencia',
        expected: '2025-12-12',
        source: 'Competência da NFS-e\n12/12/2025',
    },
    {
        field: 'cnpj_fornecedor',
        expected: '08629869000101',
        source: 'CNPJ / CPF / NIF\n08.629.869/0001-01',
    },
    {
        field: 'fornecedor_nome',
        expected: 'MUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS',
        source: 'Nome / Nome Empresarial\nMUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS',
    },
    {
        field: 'cnpj_tomador',
        expected: '02315237000197',
        source: 'TOMADOR DO SERVIÇO\n02.315.237/0001-97',
    },
    {
        field: 'tomador_nome',
        expected: 'CONDOMINIO DO EDIFICIO RECIFE COLONIAL',
        source: 'CONDOMINIO DO EDIFICIO RECIFE COLONIAL',
    },
    {
        field: 'valor_servico',
        expected: '10000.00',
        source: 'Valor do Serviço\nR$ 10.000,00',
    },
    {
        field: 'valor_nota',
        expected: '10000.00',
        source: 'Valor Líquido da NFS-e\nR$ 10.000,00',
    },
    {
        field: 'valor_liquido',
        expected: '10000.00',
        source: 'Valor Líquido da NFS-e\nR$ 10.000,00',
    },
    {
        field: 'iss_retido',
        expected: 'false',
        source: 'ISS Retido\nnao retido',
    },
    {
        field: 'simples_nacional',
        expected: 'true',
        source: 'Simples Nacional\nsim',
    },
    {
        field: 'telefone_fornecedor',
        expected: 'null',
        source: 'Telefone\n-',
    },
    {
        field: 'cnpj_fornecedor',
        expected: '08629869000101',
        source: 'CNPJ / CPF / NIF\n08 629 869 0001 01',
    },
]
