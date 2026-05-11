// =========================================================
// Exemplo 1 — Boleto condominial básico
// =========================================================
// Campos principais de identificação, partes e valores.

// =========================================================
// Exemplo 2 — Descontos progressivos
// =========================================================
// Boletos condominiais frequentemente oferecem faixas de
// desconto por antecipação de pagamento.

// =========================================================
// Exemplo 3 — Multa e juros pós-vencimento
// =========================================================
// Regras de acréscimo quando o pagamento ocorre após o vencimento.

// =========================================================
// Exemplo 4 — Composição da cobrança (extremamente importante)
// =========================================================
// Detalhamento dos itens que compõem o valor total do boleto.
// Comum em boletos condominiais com rateios e taxas extras.

// =========================================================
// Exemplo 5 — Parcelamento
// =========================================================
// Identifica a parcela atual e o total de parcelas do contrato.

// =========================================================
// Exemplo 6 — Unidade condominial
// =========================================================
// Unidade e bloco separados a partir de um campo composto.

// =========================================================
// Exemplo 7 — Documento híbrido (extremamente importante)
// =========================================================
// Boleto com múltiplos blocos (Pix, demonstrativo, bloco postal).
// Deve sinalizar documento_hibrido=true e listar os subdocumentos.

export const BOLETO_DEFAULT_EXAMPLES = [
    // — Exemplo 1: campos de identificação —
    {
        field: 'tipo_documento',
        expected: 'boleto_condominial',
        source: 'CONDOMINIO DO EDIFICIO PLACE DE LA BASTILLE\n30/03/2026\n1.470,15',
    },
    {
        field: 'beneficiario_nome',
        expected: 'CONDOMINIO DO EDIFICIO PLACE DE LA BASTILLE',
        source: 'CONDOMINIO DO EDIFICIO PLACE DE LA BASTILLE',
    },
    {
        field: 'cnpj_cpf_beneficiario',
        expected: '06067594000134',
        source: 'CNPJ: 06.067.594/0001-34',
    },
    {
        field: 'pagador_nome',
        expected: 'THAUANA SOUSA FERREIRA',
        source: 'THAUANA SOUSA FERREIRA',
    },
    {
        field: 'cnpj_cpf_pagador',
        expected: '00568544390',
        source: 'CPF: 005.685.443-90',
    },
    {
        field: 'data_vencimento',
        expected: '2026-03-30',
        source: '30/03/2026',
    },
    {
        field: 'valor_boleto',
        expected: '1470.15',
        source: '1.470,15',
    },
    {
        field: 'linha_digitavel',
        expected: '48190000030000515052925642660143814010000147015',
        source: '48190.00003 00005.150529 25642.660143 8 14010000147015',
    },

    // — Exemplo 2: descontos progressivos —
    {
        field: 'descontos_progressivos',
        expected: JSON.stringify([
            { data_limite: '2026-03-10', valor_desconto: 100.00, valor_com_desconto: 1370.15 },
            { data_limite: '2026-03-20', valor_desconto: 50.00, valor_com_desconto: 1420.15 },
        ]),
        source: 'Até dia 10/03/2026 conceder desconto de R$100,00, cobrar R$1.370,15.\nAté dia 20/03/2026 conceder desconto de R$50,00, cobrar R$1.420,15.',
    },

    // — Exemplo 3: multa e juros pós-vencimento —
    {
        field: 'multa_percentual',
        expected: '2.00',
        source: 'Após vencimento: Multa 2,00%= R$29,40',
    },
    {
        field: 'multa_valor',
        expected: '29.40',
        source: 'Após vencimento: Multa 2,00%= R$29,40',
    },
    {
        field: 'juros_percentual_dia',
        expected: '0.033',
        source: 'Juros 0,033% a.d.= R$0,49/dia',
    },
    {
        field: 'juros_valor_dia',
        expected: '0.49',
        source: 'Juros 0,033% a.d.= R$0,49/dia',
    },

    // — Exemplo 4: composição da cobrança —
    {
        field: 'itens_cobranca',
        expected: JSON.stringify([
            { descricao: 'Taxa Condominial', valor: 1040.15 },
            { descricao: 'Rateio Extra SERV. DA FACHADA/ CXS AR CONDICION', valor: 430.00 },
        ]),
        source: 'Composição da cobrança\nTaxa Condominial 1.040,15\nRateio Extra SERV. DA FACHADA/ CXS AR CONDICION - 430,00',
    },

    // — Exemplo 5: parcelamento —
    {
        field: 'parcelamento',
        expected: JSON.stringify({ parcela_atual: 20, total_parcelas: 24 }),
        source: 'Parc. 20/24',
    },

    // — Exemplo 6: unidade condominial —
    {
        field: 'unidade',
        expected: '0103',
        source: 'Unidade\n0103 1',
    },
    {
        field: 'bloco',
        expected: '1',
        source: 'Unidade\n0103 1',
    },

    // — Exemplo 7: documento híbrido —
    {
        field: 'documento_hibrido',
        expected: 'true',
        source: 'Pix Copia e Cola\n00020126...',
    },
    {
        field: 'subdocumentos',
        expected: JSON.stringify(['boleto', 'demonstrativo_financeiro', 'composicao_cobranca', 'bloco_postal']),
        source: 'Pix Copia e Cola\n00020126...\nComposição da cobrança\nBloco Postal',
    },
]
