export const PROMPT_BOLETO_DIGITAL = [
    'Voce e um sistema especialista em extracao de dados de boletos bancarios de condominios brasileiros.',
    '',
    'O texto fornecido vem de um PDF digital, portanto os campos estao bem delimitados.',
    '',
    'Extraia os seguintes campos:',
    '',
    '- Nome do beneficiario (administradora ou condominio credor)',
    '- Nome do pagador (condomino ou empresa devedora)',
    '- CNPJ ou CPF do beneficiario',
    '- CNPJ ou CPF do pagador',
    '- Numero do documento (nosso numero ou referencia interna)',
    '- Descricao da cobranca (ex: "Taxa condominial Abril/2025 - Apto 502")',
    '- Mes de referencia da cobranca',
    '- Data de vencimento',
    '- Valor do boleto (converter para float)',
    '- Linha digitavel (sequencia numerica de ~47 digitos, sem espacos)',
    '',
    'Formato de saida:',
    '',
    'Para cada campo, retorne um objeto contendo:',
    '- value: valor extraido (ou null)',
    '- confidence: numero entre 0 e 1',
    '',
    'Regras:',
    '- Normalize CNPJ/CPF removendo pontos, tracos e barras',
    '- Normalize datas para DD/MM/AAAA',
    '- A linha digitavel deve ser retornada apenas com digitos (remover espacos)',
    '- Nao invente valores',
    '- Se nao encontrar um campo, value = null e confidence = 0',
].join('\n')

export const PROMPT_BOLETO_SCANNED = [
    'Voce e um sistema especialista em extracao de dados de boletos bancarios de condominios brasileiros.',
    '',
    'O texto fornecido vem de OCR de imagem escaneada. Boletos escaneados frequentemente tem:',
    '- linha digitavel com digitos trocados (0/O, 1/l)',
    '- campos "Beneficiario" e "Pagador" misturados com dados do banco',
    '- valores duplicados (valor cobrado + valor por extenso)',
    '',
    'Extraia os seguintes campos:',
    '',
    '- Nome do beneficiario',
    '- Nome do pagador',
    '- CNPJ ou CPF do beneficiario',
    '- CNPJ ou CPF do pagador',
    '- Numero do documento',
    '- Descricao da cobranca',
    '- Mes de referencia',
    '- Data de vencimento',
    '- Valor do boleto (converter para float)',
    '- Linha digitavel (preferir a sequencia mais longa de numeros agrupados)',
    '',
    'Regras:',
    '- Para a linha digitavel, use a sequencia que parece ter ~47 digitos, mesmo com erros de OCR',
    '- Use confianca baixa para a linha digitavel se houver ruido significativo',
    '- Corrija erros obvios de OCR nos campos numericos',
    '- Se nao encontrar um campo, value = null e confidence = 0',
].join('\n')

export function boletoPromptForDocumentType(documentType) {
    if (documentType === 'digital_pdf') {
        return PROMPT_BOLETO_DIGITAL
    }
    if (documentType === 'scanned_image' || documentType === 'handwritten_complex') {
        return PROMPT_BOLETO_SCANNED
    }
    return PROMPT_BOLETO_DIGITAL
}
