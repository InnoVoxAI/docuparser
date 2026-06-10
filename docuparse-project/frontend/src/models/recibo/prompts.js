export const DEFAULT_LANGEXTRACT_PROMPT = [
    'Extraia os campos financeiros do documento.',
    '',
    'Regras:',
    '- Use somente informacoes presentes no texto.',
    '- Nao invente valores ausentes.',
    '- Preserve o trecho fonte usado para cada campo.',
    '- Quando houver multiplos valores, escolha o valor total final.',
    '- Se o campo nao existir, retorne null.',
].join('\n')
