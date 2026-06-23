// =========================================================
// Exemplo 1 — Campos de identificação e emissora
// =========================================================
// Tipo do documento, CNPJ da concessionaria, identificadores.

// =========================================================
// Exemplo 2 — Dados do cliente e contrato
// =========================================================
// Matricula, referencia de competencia, datas.

// =========================================================
// Exemplo 3 — Valores de pagamento
// =========================================================
// Total a pagar, tarifa minima e numero de economias.

// =========================================================
// Exemplo 4 — Linha digitavel (extremamente importante)
// =========================================================
// Concessionarias usam formato de 4 grupos com digito verificador.
// Normalizar removendo hifens e espacos.

// =========================================================
// Exemplo 5 — Tributos (PIS e COFINS)
// =========================================================
// Percentual e valor monetario extraidos da tabela de tributos.

// =========================================================
// Exemplo 6 — Consumo e medicao
// =========================================================
// Tipo de consumo e numero de economias faturadas.

// =========================================================
// Exemplo 7 — Doacao e campos opcionais
// =========================================================
// Valores adicionais que aparecem em algumas faturas.

export const CONTA_AGUA_DEFAULT_EXAMPLES = [

    // — Exemplo 1: identificacao e emissora —
    {
        field: 'tipo_documento',
        expected: 'conta_agua',
        source: 'FATURA MENSAL DE ÁGUA E ESGOTO',
    },
    {
        field: 'cnpj_emissor',
        expected: '09769035000164',
        source: 'CNPJ: 09.769.035/0001-64',
    },
    {
        field: 'numero_documento',
        expected: '20260254994214',
        source: 'Nº Documento: 20260254994214',
    },
    {
        field: 'numero_contrato',
        expected: '1473288',
        source: 'Nº Contrato: 1473288',
    },

    // — Exemplo 2: cliente, contrato e datas —
    {
        field: 'nome_cliente',
        expected: 'CONDOMINIO DO EDIFICIO PARK FLEMING',
        source: 'DADOS DO CLIENTE\nCONDOMINIO DO EDIFICIO PARK FLEMING',
    },
    {
        field: 'matricula',
        expected: '054994214',
        source: 'MATRÍCULA:\n054994214 02/2026-9',
    },
    {
        field: 'referencia',
        expected: '02/2026',
        source: '054994214 02/2026-9',
    },
    {
        field: 'data_vencimento',
        expected: '2026-03-20',
        source: 'VENCIMENTO: 20/03/2026',
    },
    {
        field: 'data_emissao',
        expected: '2026-03-18',
        source: 'Emitido em: 18/03/2026',
    },

    // — Exemplo 3: valores de pagamento —
    {
        field: 'total_pagar',
        expected: '5925.50',
        source: 'TOTAL A PAGAR:\n5.925,50',
    },
    {
        field: 'tarifa_minima',
        expected: '61.77',
        source: 'TARIFA MINIMA 61,77 POR UNIDADE MINIMO 5.924,50',
    },
    {
        field: 'numero_economias',
        expected: '50',
        source: 'RESIDENCIAL 050 UNIDADES',
    },

    // — Exemplo 4: linha digitavel —
    {
        field: 'linha_digitavel',
        expected: '828400000599255000183407054994214013022026900034',
        source: '82840000059-9 25500018340-7 05499421401-3 02202690003-4',
    },

    // — Exemplo 5: tributos —
    {
        field: 'cofins_percentual',
        expected: '3.00',
        source: 'COFINS\n3,00\n5.924,50\n177,74',
    },
    {
        field: 'cofins_valor',
        expected: '177.74',
        source: 'COFINS\n3,00\n5.924,50\n177,74',
    },
    {
        field: 'pis_percentual',
        expected: '0.65',
        source: 'PIS 0,65\n5.924,50\n38,51',
    },
    {
        field: 'pis_valor',
        expected: '38.51',
        source: 'PIS 0,65\n5.924,50\n38,51',
    },

    // — Exemplo 6: consumo e medicao —
    {
        field: 'tipo_consumo',
        expected: 'minimo_fixo',
        source: 'NÃO MEDIDO /MIN FIXAD',
    },
    {
        field: 'categoria',
        expected: 'residencial',
        source: 'ESGOTO\n RESIDENCIAL 050 UNIDADES',
    },

    // — Exemplo 7: doacao e campos adicionais —
    {
        field: 'doacao',
        expected: '1.00',
        source: 'DOACAO AO PRO-CRIANCA 02/2026 1,00',
    },
    {
        field: 'emitido_por',
        expected: 'INTERNET',
        source: 'Emitido por: INTERNET Emitido em: 18/03/2026',
    },

]
