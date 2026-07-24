// Tipos e constantes do "builder" LangExtract (área "Extração" de Configurações).
// Movidos tal-e-qual de `src/main.tsx` (T036-T039) — não fazem parte do
// escopo de conversão RHF+Zod (essa área não tem formulário Ocr/Email/
// WhatsApp/Integrações, ver decisão #8 do handoff de T036-T040).

export interface SchemaForm {
    schema_id: string
    version: string
    model_name: string
    document_type: string
    status: string
}

export interface LayoutForm {
    layout: string
    document_type: string
    schema_config_id: string
    confidence_threshold: string
}

export interface ReferenceReview {
    quality: string
    action: string
    notes: string
}

export const SETTINGS_TABS = [
    { id: 'setup', label: 'Modelo' },
    { id: 'ocr', label: 'OCR referencia' },
    { id: 'schema', label: 'Schema' },
    { id: 'instructions', label: 'Instrucoes' },
    { id: 'examples', label: 'Exemplos' },
    { id: 'test', label: 'Teste visual' },
    { id: 'rules', label: 'Regras' },
    { id: 'publish', label: 'Publicacao' },
]

export const SETTINGS_AREAS = [
    { id: 'email', label: 'Email' },
    { id: 'whatsapp', label: 'WhatsApp' },
    { id: 'ocr-routing', label: 'OCR' },
    { id: 'extraction', label: 'Extracao' },
    { id: 'integrations', label: 'Integracoes' },
]

export const SETTINGS_TAB_HELP: Record<string, { title: string; text: string }> = {
    setup: {
        title: 'Setup do modelo',
        text: 'Defina a identidade do template de extracao: nome, schema, tipo de documento, versao e status. Esses dados controlam qual configuracao sera aplicada apos OCR e classificacao.',
    },
    ocr: {
        title: 'OCR de referencia',
        text: 'Escolha um documento real ja processado para usar como base. Compare o original com a transcricao OCR e confirme se o texto tem qualidade suficiente para criar exemplos e regras.',
    },
    schema: {
        title: 'Schema de saida',
        text: 'Liste os campos que o LangExtract deve devolver. Para cada campo, informe tipo, obrigatoriedade e a regra de extracao ou normalizacao esperada.',
    },
    instructions: {
        title: 'Instrucoes LangExtract',
        text: 'Monte o prompt controlado que orienta a extracao. Use regras objetivas, proiba invencao de dados e exija rastreabilidade com o trecho fonte.',
    },
    examples: {
        title: 'Exemplos few-shot',
        text: 'Adicione exemplos revisados por humano. Cada linha deve ligar um campo ao valor correto e ao trecho OCR que justifica esse valor.',
    },
    test: {
        title: 'Teste visual',
        text: 'Use esta aba para validar o template com um documento real. Confira o original, o OCR destacado e o JSON esperado antes de publicar a versao.',
    },
    rules: {
        title: 'Regras de pos-processamento',
        text: 'Defina validacoes deterministicas aplicadas depois da extracao, como normalizacao de moeda/data e validacao de CPF ou CNPJ.',
    },
    publish: {
        title: 'Publicacao',
        text: 'Revise o JSON final do template, salve o schema e vincule o layout correspondente. Use status aprovado somente quando os testes estiverem conferidos.',
    },
}

export const PROMPT_HINTS = [
    'Nao inventar dados',
    'Usar texto exato',
    'Normalizar datas',
    'Extrair valores monetarios',
    'Tratar multiplas ocorrencias',
    'Ignorar rodape/cabecalho',
    'Priorizar tabelas',
    'Priorizar campos proximos ao rotulo',
]

export const PROTECTED_SCHEMA_IDS = ['nota_fiscal_default', 'conta_agua_default']
