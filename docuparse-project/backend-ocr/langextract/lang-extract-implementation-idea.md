# Extração Estruturada com LangExtract

> Pipeline para extrair dados estruturados a partir de `raw_text` gerado por OCR, com estratégias distintas para documentos **digital_pdf** e **scanned_image**.

---

## Visão Geral

| Etapa | Descrição |
|-------|-----------|
| 1 | Definir o Schema (Pydantic) |
| 2 | Criar prompts específicos por tipo |
| 3 | Exemplos para o modelo (Few-Shot) |
| 4 | Escolher o prompt dinamicamente |
| 5 | Executar extração com LLM |
| 6 | Pós-processamento |
| 7 | Fallback com Regex |
| 8 | Pipeline completo |

---

## Etapa 1 — Definir o Schema

O schema representa os dados a extrair e serve como contrato para a saída estruturada. Use `Optional` porque o OCR pode falhar ou omitir campos.

```python
from pydantic import BaseModel
from typing import Optional

class Campo(BaseModel):
    value: Optional[str | float | bool]
    confidence: float

class NotaFiscalSchema(BaseModel):
    fornecedor_nome: Campo
    tomador_nome: Campo
    cnpj_fornecedor: Campo
    numero_nota: Campo
    descricao_servico: Campo
    valor_nota: Campo
    retencao: Campo
    cnpj_tomador: Campo
```

---

## Etapa 2 — Criar Prompts Específicos

### Prompt para `digital_pdf`

```python
PROMPT_DIGITAL = """
Você é um sistema especialista em extração de dados de notas fiscais brasileiras.

O texto fornecido vem de um PDF digital, portanto está bem estruturado.

Extraia os seguintes campos:

- Nome do fornecedor
- Nome do tomador do serviço
- CNPJ do fornecedor
- Número da nota fiscal
- Descrição do serviço
- Valor da nota fiscal (converter para float, ex: 1234.56)
- Se há retenção (true/false)
- CNPJ do tomador

Formato de saída:

Para cada campo, retorne um objeto contendo:
- value: valor extraído (ou null)
- confidence: número entre 0 e 1 indicando a confiança na extração

Exemplo:

{
  "cnpj_fornecedor": {
    "value": "12345678000199",
    "confidence": 0.98
  }
}

Regras:
- Se não encontrar um campo, value = null e confidence = 0
- "Não há retenção" → retencao = false
- Normalize valores monetários
- Não invente valores
- Use alta confiança apenas quando o valor estiver claramente explícito
- Use confiança média quando houver pequena ambiguidade
- Use baixa confiança quando houver inferência
"""
```

### Prompt para `scanned_image`

```python
PROMPT_SCANNED = """
Você é um sistema especialista em extração de dados de notas fiscais brasileiras.

O texto fornecido vem de OCR de imagem escaneada e pode conter erros como:
- caracteres trocados (O/0, l/1)
- palavras quebradas
- espaçamento inconsistente

Extraia os seguintes campos:

- Nome do fornecedor
- Nome do tomador do serviço
- CNPJ do fornecedor
- Número da nota fiscal
- Descrição do serviço
- Valor da nota fiscal (converter para float)
- Se há retenção (true/false)
- CNPJ do tomador

Formato de saída:

Para cada campo, retorne um objeto contendo:
- value: valor extraído (ou null)
- confidence: número entre 0 e 1 indicando a confiança

Exemplo:

{
  "valor_nota": {
    "value": 1250.0,
    "confidence": 0.85
  }
}

Regras:
- Corrija erros óbvios de OCR ao interpretar
- Se um valor parecer ambíguo, escolha o mais provável
- Se não encontrar um campo, value = null e confidence = 0
- "Nao ha retencao", "N H RETENCAO", etc → retencao = false
- Normalize valores monetários
- Use confiança baixa se houver ruído significativo no OCR
- Use confiança média se houver inferência
- Use confiança alta apenas se o valor estiver claramente legível
"""
```

### Diferença entre as abordagens

| Aspecto | `digital_pdf` | `scanned_image` |
|---------|--------------|-----------------|
| Qualidade do texto | Limpo e estruturado | Com ruído e artefatos |
| Estratégia do prompt | Extração direta | Inferência e correção de OCR |
| Precisão esperada | Alta | Moderada |
| Necessidade de fallback | Baixa | Alta |

---

## Etapa 3 — Exemplos para o Modelo (Few-Shot)

Few-shot examples ensinam o modelo a reconhecer padrões do documento sem depender apenas do prompt. Inclua-os como mensagens `user`/`assistant` antes do input real.

### Exemplo para `digital_pdf` — NFS-e Recife

**Texto bruto (input):**

```
DANFSe v1.0
Documento Auxiliar da NFS-e
Prefeitura do Recife
Secretaria de Finanças
faleconosco@recife.pe.gov.br
Chave de Acesso da NFS-e
26116062208629869000101000000000000625120022507574
...
EMITENTE DA NFS-e
Prestador do Serviço
CNPJ / CPF / NIF
08.629.869/0001-01
Nome / Nome Empresarial
MUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS
...
TOMADOR DO SERVIÇO
CNPJ / CPF / NIF
02.315.237/0001-97
Nome / Nome Empresarial
CONDOMINIO DO EDIFICIO RECIFE COLONIAL
...
Descrição do Serviço
Prestação de serviços advocatícios na defesa dos direitos e interesses do tomador em
procedimento de retificação e demarcação de metragens e área proposto no 6º Ofício de
Registro de Imóveis do Recife proposto por proprietário de imóvel confinante.
...
Valor do Serviço
R$ 10.000,00
...
Retenção do ISSQN
Não Retido
...
Valor Líquido da NFS-e
R$ 10.000,00
```

**Saída esperada (output):**

```json
{
  "fornecedor_nome":   "MUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS",
  "tomador_nome":      "CONDOMINIO DO EDIFICIO RECIFE COLONIAL",
  "cnpj_fornecedor":   "08629869000101",
  "numero_nota":       "26116062208629869000101000000000000625120022507574",
  "descricao_servico": "Prestação de serviços advocatícios na defesa dos direitos e interesses do tomador em procedimento de retificação e demarcação de metragens e área proposto no 6º Ofício de Registro de Imóveis do Recife proposto por proprietário de imóvel confinante.",
  "valor_nota":        10000.0,
  "retencao":          false,
  "cnpj_tomador":      "02315237000197"
}
```

### Como injetar os few-shots na chamada à API

```python
FEW_SHOT_DIGITAL = [
    {
        "role": "user",
        "content": (
            "Texto da nota fiscal:\n"
            "DANFSe v1.0\n"
            "Chave de Acesso da NFS-e\n"
            "26116062208629869000101000000000000625120022507574\n"
            "CNPJ / CPF / NIF\n08.629.869/0001-01\n"
            "Nome / Nome Empresarial\nMUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS\n"
            "TOMADOR DO SERVIÇO\nCNPJ / CPF / NIF\n02.315.237/0001-97\n"
            "Nome / Nome Empresarial\nCONDOMINIO DO EDIFICIO RECIFE COLONIAL\n"
            "Descrição do Serviço\n"
            "Prestação de serviços advocatícios na defesa dos direitos e interesses do tomador...\n"
            "Valor do Serviço\nR$ 10.000,00\n"
            "Retenção do ISSQN\nNão Retido\n"
            "Valor Líquido da NFS-e\nR$ 10.000,00"
        )
    },
    {
        "role": "assistant",
        "content": """{
  "fornecedor_nome":   "MUNOZ, PEREIRA E VASCONCELOS ADVOGADOS ASSOCIADOS",
  "tomador_nome":      "CONDOMINIO DO EDIFICIO RECIFE COLONIAL",
  "cnpj_fornecedor":   "08629869000101",
  "numero_nota":       "26116062208629869000101000000000000625120022507574",
  "descricao_servico": "Prestação de serviços advocatícios na defesa dos direitos e interesses do tomador em procedimento de retificação e demarcação de metragens e área proposto no 6º Ofício de Registro de Imóveis do Recife proposto por proprietário de imóvel confinante.",
  "valor_nota":        10000.0,
  "retencao":          false,
  "cnpj_tomador":      "02315237000197"
}"""
    }
]
```

### O que esses exemplos ensinam ao modelo (`digital_pdf`)

| Campo | Padrão aprendido |
|-------|-----------------|
| `cnpj_fornecedor` / `cnpj_tomador` | Remover pontos e traços (`08.629.869/0001-01` → `08629869000101`) |
| `numero_nota` | Usar a Chave de Acesso completa quando não há número simples |
| `valor_nota` | Converter `R$ 10.000,00` → `10000.0` |
| `retencao` | `"Não Retido"` → `false` |
| `descricao_servico` | Extrair o parágrafo inteiro, sem truncar |

---

### Exemplo para `scanned_image` — Recibo de Indenização

**Texto bruto (input):**

```
Recibo de indenização
Eu, SÁVIO VASCONCELOS DE LIMA. CPF nº 054.697.724-38,
RG nº 6739255, proprietário legal da unidade 301 deste condomínio,
recebi do Condomínio do Edifício Recife Colonial, CNPJ nº 02.315.237/0001-97, a
importância de R$ 391,90 (trezentos e noventa e um reais e noventa centavos), referente
ao reembolso da compra do chuveiro blindado da marca Lorenzetti M220, em virtude do
dano que aconteceu após a manutenção das válvulas de retenção do condomínio e liberação
da água para as unidades até o ponto da regulagem ideal, o chuveiro em questão, não
suportou a pressão e rachou a tubulação do mesmo.
Diante do fato, compramos novo chuveiro blindado e solicitamos o reembolso.
A quitação dar-se-á de forma integral com a confirmação do depósito via PIX informado
abaixo:
Titular da conta PIX: SÁVIO VASCONCELOS DE LIMA
Conta PIX: 87999269484 CPF: ( ) Celular: (X) Outro: ( )
Recife, 02 de dezembro de 2025.
Nome: SÁVIO VASCONCELOS DE LIMA
CPF: 054.697.724-38
```

**Saída esperada (output):**

```json
{
  "fornecedor_nome":   "SÁVIO VASCONCELOS DE LIMA",
  "tomador_nome":      "CONDOMINIO DO EDIFICIO RECIFE COLONIAL",
  "cnpj_fornecedor":   null,
  "numero_nota":       null,
  "descricao_servico": "Reembolso da compra de chuveiro blindado Lorenzetti M220 devido a dano causado por aumento de pressão após manutenção das válvulas de retenção do condomínio.",
  "valor_nota":        391.90,
  "retencao":          false,
  "cnpj_tomador":      "02315237000197"
}
```

### Como injetar os few-shots na chamada à API (`scanned_image`)

```python
FEW_SHOT_SCANNED = [
    {
        "role": "user",
        "content": (
            "Texto da nota fiscal:\n"
            "Recibo de indenização\n"
            "Eu, SÁVIO VASCONCELOS DE LIMA. CPF nº 054.697.724-38,\n"
            "RG nº 6739255, proprietário legal da unidade 301 deste condomínio,\n"
            "recebi do Condomínio do Edifício Recife Colonial, CNPJ nº 02.315.237/0001-97, a\n"
            "importância de R$ 391,90 (trezentos e noventa e um reais e noventa centavos), referente\n"
            "ao reembolso da compra do chuveiro blindado da marca Lorenzetti M220, em virtude do\n"
            "dano que aconteceu após a manutenção das válvulas de retenção do condomínio e liberação\n"
            "da água para as unidades até o ponto da regulagem ideal, o chuveiro em questão, não\n"
            "suportou a pressão e rachou a tubulação do mesmo.\n"
            "Diante do fato, compramos novo chuveiro blindado e solicitamos o reembolso.\n"
            "Recife, 02 de dezembro de 2025.\n"
            "Nome: SÁVIO VASCONCELOS DE LIMA\n"
            "CPF: 054.697.724-38"
        )
    },
    {
        "role": "assistant",
        "content": """{
  "fornecedor_nome":   "SÁVIO VASCONCELOS DE LIMA",
  "tomador_nome":      "CONDOMINIO DO EDIFICIO RECIFE COLONIAL",
  "cnpj_fornecedor":   null,
  "numero_nota":       null,
  "descricao_servico": "Reembolso da compra de chuveiro blindado Lorenzetti M220 devido a dano causado por aumento de pressão após manutenção das válvulas de retenção do condomínio.",
  "valor_nota":        391.90,
  "retencao":          false,
  "cnpj_tomador":      "02315237000197"
}"""
    }
]
```

### O que esses exemplos ensinam ao modelo (`scanned_image`)

| Campo | Padrão aprendido |
|-------|-----------------|
| `fornecedor_nome` | Pessoa física como fornecedor — extrair do corpo do texto, não de um campo rotulado |
| `tomador_nome` | Inferir o nome por extenso (`"Condomínio do Edifício Recife Colonial"` → normalizar para maiúsculas) |
| `cnpj_fornecedor` | Retornar `null` quando o fornecedor é pessoa física (CPF, não CNPJ) |
| `numero_nota` | Retornar `null` quando o documento é um recibo informal sem numeração |
| `valor_nota` | Extrair `R$ 391,90` mesmo quando acompanhado de valor por extenso |
| `retencao` | Inferir `false` pela ausência de qualquer menção a retenção no texto |
| `descricao_servico` | Sintetizar o motivo do pagamento a partir de texto narrativo, sem copiar literalmente |

---

## Etapa 4 — Escolher o Prompt Dinamicamente

```python
def escolher_prompt(document_type: str) -> str:
    if document_type == "digital_pdf":
        return PROMPT_DIGITAL
    elif document_type == "scanned_image":
        return PROMPT_SCANNED
    else:
        return PROMPT_DIGITAL  # fallback seguro
```

---

## Etapa 5 — Executar Extração com LLM

```python
from openai import OpenAI

client = OpenAI()

FEW_SHOTS = {
    "digital_pdf":   FEW_SHOT_DIGITAL,
    "scanned_image": FEW_SHOT_SCANNED,
}

def extrair_dados(document: dict) -> NotaFiscalSchema:
    prompt      = escolher_prompt(document["document_type"])
    few_shots   = FEW_SHOTS.get(document["document_type"], [])

    messages = [
        {"role": "system", "content": prompt},
        *few_shots,
        {"role": "user", "content": f"Texto da nota fiscal:\n{document['raw_text']}"}
    ]

    response = client.responses.parse(
        model="gpt-4.1",
        input=messages,
        response_format=NotaFiscalSchema
    )

    return response.output_parsed
```

---

## Etapa 6 — Pós-processamento

Normaliza campos críticos como CNPJ, removendo caracteres não numéricos.

```python
import re

def limpar_cnpj(cnpj: str | None) -> str | None:
    if not cnpj:
        return None
    return re.sub(r"\D", "", cnpj)

def normalizar_dados(dados: NotaFiscalSchema) -> NotaFiscalSchema:
    dados.cnpj_fornecedor = limpar_cnpj(dados.cnpj_fornecedor)
    dados.cnpj_tomador    = limpar_cnpj(dados.cnpj_tomador)
    return dados
```

---

## Etapa 7 — Fallback com Regex

Usado quando o LLM não consegue extrair o valor monetário:

```python
def extrair_valor_regex(texto: str) -> float | None:
    match = re.search(r"R\$\s?([\d.,]+)", texto)
    if match:
        return float(match.group(1).replace(".", "").replace(",", "."))
    return None
```

```python
# Aplicar fallback após extração principal
if dados.valor_nota is None:
    dados.valor_nota = extrair_valor_regex(document["raw_text"])
```

---

## Etapa 8 — Pipeline Completo

```python
def processar_documento(document: dict) -> dict:
    dados = extrair_dados(document)
    dados = normalizar_dados(dados)

    if dados.valor_nota is None:
        dados.valor_nota = extrair_valor_regex(document["raw_text"])

    return dados.dict()
```

### Execução

```python
resultado = processar_documento(document)
print(resultado)
```

### Exemplo de saída

```json
{
    "fornecedor_nome":   "Empresa ABC Ltda",
    "tomador_nome":      "Empresa XYZ",
    "cnpj_fornecedor":   "12345678000199",
    "numero_nota":       "12345",
    "descricao_servico": "Consultoria em TI",
    "valor_nota":        1250.0,
    "retencao":          false,
    "cnpj_tomador":      "98765432000111"
}
```

---

## Boas Práticas

- **Separar prompts** por tipo de documento
- **Nunca confiar 100%** no OCR — sempre validar
- **Usar fallback com regex** para campos críticos como valor
- **Validar campos críticos** (CNPJ, valor) após extração
- **Evoluir com few-shot** — adicionar exemplos reais ao prompt conforme surgem casos de erro

---

## Resumo da Arquitetura

```
raw_text (OCR)
     │
     ▼
escolher_prompt(document_type)
     │
     ▼
LLM (structured output → NotaFiscalSchema)
     │
     ▼
normalizar_dados()   ←── limpar CNPJ, etc.
     │
     ▼
fallback regex       ←── se valor_nota == None
     │
     ▼
dados estruturados (dict)
```

---

## Documento: Fatura de Condomínio

Aplicável a faturas de serviços públicos (água, energia, gás) e prestadores recorrentes recebidas pelo condomínio.

### Schema

```python
class FaturaCondominio(BaseModel):
    emitente_nome: Campo          # empresa emissora (COMPESA, CELPE, etc.)
    destinatario_nome: Campo      # nome do condomínio destinatário
    cnpj_emitente: Campo
    cnpj_destinatario: Campo
    numero_fatura: Campo          # número/código da fatura ou conta
    descricao_servico: Campo      # tipo: água, energia elétrica, gás, etc.
    mes_referencia: Campo         # "MM/AAAA"
    data_vencimento: Campo        # "DD/MM/AAAA"
    valor_total: Campo            # float
    valor_multa_juros: Campo      # float ou null (se não houver)
```

### Prompt para `digital_pdf`

```python
PROMPT_FATURA_DIGITAL = """
Você é um sistema especialista em extração de dados de faturas de serviços públicos e prestadores recebidas por condomínios brasileiros.

O texto fornecido vem de um PDF digital, portanto está bem estruturado.

Extraia os seguintes campos:

- Nome do emitente (empresa que emitiu a fatura, ex: COMPESA, CELPE, Gás Natural)
- Nome do destinatário (nome do condomínio ou responsável)
- CNPJ do emitente
- CNPJ do destinatário
- Número/código da fatura ou conta
- Descrição do serviço (água, energia elétrica, gás, manutenção, etc.)
- Mês de referência da cobrança
- Data de vencimento
- Valor total a pagar (converter para float)
- Valor de multa/juros se houver (converter para float, null se não houver)

Formato de saída:

Para cada campo, retorne um objeto contendo:
- value: valor extraído (ou null)
- confidence: número entre 0 e 1

Regras:
- Se não encontrar um campo, value = null e confidence = 0
- Normalize valores monetários (R$ 1.250,00 → 1250.0)
- Normalize datas para o formato DD/MM/AAAA
- Extraia o mês de referência como "MM/AAAA"
- Não invente valores
- Use alta confiança apenas quando o valor estiver claramente explícito
"""
```

### Prompt para `scanned_image`

```python
PROMPT_FATURA_SCANNED = """
Você é um sistema especialista em extração de dados de faturas de serviços públicos e prestadores recebidas por condomínios brasileiros.

O texto fornecido vem de OCR de imagem escaneada e pode conter erros como:
- caracteres trocados (O/0, l/1, 5/S)
- valores monetários com espaçamento inconsistente
- datas com separadores trocados

Extraia os seguintes campos:

- Nome do emitente (empresa que emitiu a fatura)
- Nome do destinatário (nome do condomínio)
- CNPJ do emitente
- CNPJ do destinatário
- Número/código da fatura
- Descrição do serviço
- Mês de referência
- Data de vencimento
- Valor total a pagar (converter para float)
- Valor de multa/juros se houver (null se ausente)

Regras:
- Corrija erros óbvios de OCR ao interpretar (ex: "CNPJ O2.315" → "CNPJ 02.315")
- Normalize valores monetários
- Normalize datas para DD/MM/AAAA
- Extraia o mês de referência como "MM/AAAA"
- Se não encontrar um campo, value = null e confidence = 0
- Use confiança baixa para campos com ruído significativo
"""
```

### Exemplos Few-Shot

#### `digital_pdf` — Conta de Água (COMPESA)

**Texto bruto (input):**

```
COMPESA — Companhia Pernambucana de Saneamento
CNPJ: 10.786.460/0001-30
Conta de Fornecimento de Água e Esgoto

Unidade Consumidora: CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL
CNPJ: 02.315.237/0001-97
Referência: Março/2025
Vencimento: 15/04/2025

Consumo registrado: 245 m³
Valor da conta: R$ 1.872,40
Multa por atraso: —
Total a pagar: R$ 1.872,40
```

**Saída esperada (output):**

```json
{
  "emitente_nome":      { "value": "COMPESA — Companhia Pernambucana de Saneamento", "confidence": 0.99 },
  "destinatario_nome":  { "value": "CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL", "confidence": 0.99 },
  "cnpj_emitente":      { "value": "10786460000130", "confidence": 0.98 },
  "cnpj_destinatario":  { "value": "02315237000197", "confidence": 0.98 },
  "numero_fatura":      { "value": null, "confidence": 0 },
  "descricao_servico":  { "value": "Fornecimento de Água e Esgoto", "confidence": 0.97 },
  "mes_referencia":     { "value": "03/2025", "confidence": 0.99 },
  "data_vencimento":    { "value": "15/04/2025", "confidence": 0.99 },
  "valor_total":        { "value": 1872.40, "confidence": 0.99 },
  "valor_multa_juros":  { "value": null, "confidence": 0.95 }
}
```

```python
FEW_SHOT_FATURA_DIGITAL = [
    {
        "role": "user",
        "content": (
            "Texto do documento:\n"
            "COMPESA — Companhia Pernambucana de Saneamento\n"
            "CNPJ: 10.786.460/0001-30\n"
            "Conta de Fornecimento de Água e Esgoto\n"
            "Unidade Consumidora: CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL\n"
            "CNPJ: 02.315.237/0001-97\n"
            "Referência: Março/2025\n"
            "Vencimento: 15/04/2025\n"
            "Consumo registrado: 245 m³\n"
            "Valor da conta: R$ 1.872,40\n"
            "Multa por atraso: —\n"
            "Total a pagar: R$ 1.872,40"
        )
    },
    {
        "role": "assistant",
        "content": """{
  "emitente_nome":      { "value": "COMPESA — Companhia Pernambucana de Saneamento", "confidence": 0.99 },
  "destinatario_nome":  { "value": "CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL", "confidence": 0.99 },
  "cnpj_emitente":      { "value": "10786460000130", "confidence": 0.98 },
  "cnpj_destinatario":  { "value": "02315237000197", "confidence": 0.98 },
  "numero_fatura":      { "value": null, "confidence": 0 },
  "descricao_servico":  { "value": "Fornecimento de Água e Esgoto", "confidence": 0.97 },
  "mes_referencia":     { "value": "03/2025", "confidence": 0.99 },
  "data_vencimento":    { "value": "15/04/2025", "confidence": 0.99 },
  "valor_total":        { "value": 1872.40, "confidence": 0.99 },
  "valor_multa_juros":  { "value": null, "confidence": 0.95 }
}"""
    }
]
```

### O que esses exemplos ensinam ao modelo (`fatura`)

| Campo | Padrão aprendido |
|-------|-----------------|
| `mes_referencia` | `"Março/2025"` → `"03/2025"` |
| `valor_multa_juros` | Traço ou ausência de campo → `null` |
| `numero_fatura` | Ausência de número explícito → `null` |
| `cnpj_emitente` / `cnpj_destinatario` | Remover pontos, barras e traços |

### Diferença entre as abordagens

| Aspecto | `digital_pdf` | `scanned_image` |
|---------|--------------|-----------------|
| Layout | Tabelas e campos rotulados | Texto corrido com ruído |
| Valor monetário | Facilmente identificável | Pode conter artefatos (`R S 1.872,40`) |
| Datas | Formato consistente | Separadores podem ser trocados |
| Mês de referência | Campo explícito | Pode estar no cabeçalho ou rodapé |

---

## Documento: Boleto de Condomínio

Aplicável a boletos bancários de cobrança da taxa condominial ou serviços avulsos emitidos pela administradora.

### Schema

```python
class BoletoCondominio(BaseModel):
    beneficiario_nome: Campo      # administradora ou condomínio credor
    pagador_nome: Campo           # condômino ou empresa devedora
    cnpj_cpf_beneficiario: Campo
    cnpj_cpf_pagador: Campo
    numero_documento: Campo       # nosso número ou referência interna
    descricao: Campo              # "Taxa condominial — Abril/2025 — Apto 301"
    mes_referencia: Campo         # "MM/AAAA"
    data_vencimento: Campo        # "DD/MM/AAAA"
    valor_boleto: Campo           # float
    linha_digitavel: Campo        # string com ~47 dígitos, sem espaços
```

### Prompt para `digital_pdf`

```python
PROMPT_BOLETO_DIGITAL = """
Você é um sistema especialista em extração de dados de boletos bancários de condomínios brasileiros.

O texto fornecido vem de um PDF digital, portanto os campos estão bem delimitados.

Extraia os seguintes campos:

- Nome do beneficiário (administradora ou condomínio credor)
- Nome do pagador (condômino ou empresa devedora)
- CNPJ ou CPF do beneficiário
- CNPJ ou CPF do pagador
- Número do documento (nosso número ou referência interna)
- Descrição da cobrança (ex: "Taxa condominial Abril/2025 — Apto 502")
- Mês de referência da cobrança
- Data de vencimento
- Valor do boleto (converter para float)
- Linha digitável (sequência numérica de ~47 dígitos, sem espaços)

Formato de saída:

Para cada campo, retorne um objeto contendo:
- value: valor extraído (ou null)
- confidence: número entre 0 e 1

Regras:
- Normalize CNPJ/CPF removendo pontos, traços e barras
- Normalize datas para DD/MM/AAAA
- A linha digitável deve ser retornada apenas com dígitos (remover espaços)
- Não invente valores
- Se não encontrar um campo, value = null e confidence = 0
"""
```

### Prompt para `scanned_image`

```python
PROMPT_BOLETO_SCANNED = """
Você é um sistema especialista em extração de dados de boletos bancários de condomínios brasileiros.

O texto fornecido vem de OCR de imagem escaneada. Boletos escaneados frequentemente têm:
- linha digitável com dígitos trocados (0/O, 1/l)
- campos "Beneficiário" e "Pagador" misturados com dados do banco
- valores duplicados (valor cobrado + valor por extenso)

Extraia os seguintes campos:

- Nome do beneficiário
- Nome do pagador
- CNPJ ou CPF do beneficiário
- CNPJ ou CPF do pagador
- Número do documento
- Descrição da cobrança
- Mês de referência
- Data de vencimento
- Valor do boleto (converter para float)
- Linha digitável (preferir a sequência mais longa de números agrupados)

Regras:
- Para a linha digitável, use a sequência que parece ter ~47 dígitos, mesmo com erros de OCR
- Use confiança baixa para a linha digitável se houver ruído significativo
- Corrija erros óbvios de OCR nos campos numéricos
- Se não encontrar um campo, value = null e confidence = 0
"""
```

### Exemplos Few-Shot

#### `digital_pdf` — Boleto de Taxa Condominial

**Texto bruto (input):**

```
ADMINISTRADORA PREDIAL ATLAS LTDA
CNPJ: 34.521.088/0001-55
Beneficiário: Condomínio do Edifício Recife Colonial

Pagador: CARLOS EDUARDO MENDES SANTOS
CPF: 123.456.789-00 — Unidade: 502

Descrição: Taxa condominial ordinária — Maio/2025 — Apto 502
Nosso Número: 00291837465
Vencimento: 10/05/2025
Valor: R$ 850,00

Linha Digitável:
34191.09008 05291.837460 05000.850010 1 10050000085000
```

**Saída esperada (output):**

```json
{
  "beneficiario_nome":      { "value": "ADMINISTRADORA PREDIAL ATLAS LTDA", "confidence": 0.99 },
  "pagador_nome":           { "value": "CARLOS EDUARDO MENDES SANTOS", "confidence": 0.99 },
  "cnpj_cpf_beneficiario":  { "value": "34521088000155", "confidence": 0.98 },
  "cnpj_cpf_pagador":       { "value": "12345678900", "confidence": 0.98 },
  "numero_documento":       { "value": "00291837465", "confidence": 0.97 },
  "descricao":              { "value": "Taxa condominial ordinária — Maio/2025 — Apto 502", "confidence": 0.99 },
  "mes_referencia":         { "value": "05/2025", "confidence": 0.99 },
  "data_vencimento":        { "value": "10/05/2025", "confidence": 0.99 },
  "valor_boleto":           { "value": 850.0, "confidence": 0.99 },
  "linha_digitavel":        { "value": "34191090080529183746005000850010110050000085000", "confidence": 0.95 }
}
```

```python
FEW_SHOT_BOLETO_DIGITAL = [
    {
        "role": "user",
        "content": (
            "Texto do documento:\n"
            "ADMINISTRADORA PREDIAL ATLAS LTDA\n"
            "CNPJ: 34.521.088/0001-55\n"
            "Beneficiário: Condomínio do Edifício Recife Colonial\n"
            "Pagador: CARLOS EDUARDO MENDES SANTOS\n"
            "CPF: 123.456.789-00 — Unidade: 502\n"
            "Descrição: Taxa condominial ordinária — Maio/2025 — Apto 502\n"
            "Nosso Número: 00291837465\n"
            "Vencimento: 10/05/2025\n"
            "Valor: R$ 850,00\n"
            "Linha Digitável:\n"
            "34191.09008 05291.837460 05000.850010 1 10050000085000"
        )
    },
    {
        "role": "assistant",
        "content": """{
  "beneficiario_nome":      { "value": "ADMINISTRADORA PREDIAL ATLAS LTDA", "confidence": 0.99 },
  "pagador_nome":           { "value": "CARLOS EDUARDO MENDES SANTOS", "confidence": 0.99 },
  "cnpj_cpf_beneficiario":  { "value": "34521088000155", "confidence": 0.98 },
  "cnpj_cpf_pagador":       { "value": "12345678900", "confidence": 0.98 },
  "numero_documento":       { "value": "00291837465", "confidence": 0.97 },
  "descricao":              { "value": "Taxa condominial ordinária — Maio/2025 — Apto 502", "confidence": 0.99 },
  "mes_referencia":         { "value": "05/2025", "confidence": 0.99 },
  "data_vencimento":        { "value": "10/05/2025", "confidence": 0.99 },
  "valor_boleto":           { "value": 850.0, "confidence": 0.99 },
  "linha_digitavel":        { "value": "34191090080529183746005000850010110050000085000", "confidence": 0.95 }
}"""
    }
]
```

### O que esses exemplos ensinam ao modelo (`boleto`)

| Campo | Padrão aprendido |
|-------|-----------------|
| `cnpj_cpf_pagador` | CPF de pessoa física como pagador |
| `linha_digitavel` | Remover espaços e pontos da linha digitável impressa |
| `mes_referencia` | Extrair do campo `descricao` quando não há campo dedicado |
| `beneficiario_nome` | Distinguir a administradora do condomínio no campo beneficiário |

### Diferença entre as abordagens

| Aspecto | `digital_pdf` | `scanned_image` |
|---------|--------------|-----------------|
| Linha digitável | Bem delimitada e confiável | Alta taxa de erros de OCR — confiança reduzida |
| Pagador/beneficiário | Campos rotulados | Texto corrido — inferência necessária |
| Valor | Único e claro | Pode aparecer por extenso e numeral |

---

## Documento: Recibo de Pagamento

Aplicável a recibos de pagamentos emitidos ou recebidos pelo condomínio (prestadores, condôminos, funcionários).

### Schema

```python
class ReciboCondominio(BaseModel):
    recebedor_nome: Campo         # quem recebeu o pagamento
    pagador_nome: Campo           # quem efetuou o pagamento (geralmente o condomínio)
    cpf_cnpj_recebedor: Campo
    cpf_cnpj_pagador: Campo
    numero_recibo: Campo          # número sequencial, se houver
    descricao_pagamento: Campo    # motivo/descrição do pagamento
    data_pagamento: Campo         # "DD/MM/AAAA"
    valor_recebido: Campo         # float
    forma_pagamento: Campo        # "PIX", "TED", "dinheiro", "cheque", etc.
```

### Prompt para `digital_pdf`

```python
PROMPT_RECIBO_DIGITAL = """
Você é um sistema especialista em extração de dados de recibos de pagamento de condomínios brasileiros.

O texto fornecido vem de um PDF digital.

Extraia os seguintes campos:

- Nome de quem recebeu o pagamento (recebedor)
- Nome de quem efetuou o pagamento (pagador — geralmente o condomínio)
- CPF ou CNPJ do recebedor
- CPF ou CNPJ do pagador
- Número do recibo (se houver)
- Descrição do pagamento (serviço prestado, motivo do repasse, etc.)
- Data do pagamento
- Valor recebido (converter para float)
- Forma de pagamento (PIX, TED, dinheiro, cheque, etc.)

Formato de saída:

Para cada campo, retorne um objeto contendo:
- value: valor extraído (ou null)
- confidence: número entre 0 e 1

Regras:
- Normalize CPF/CNPJ removendo pontos, traços e barras
- Normalize datas para DD/MM/AAAA
- Se não encontrar a forma de pagamento, value = null
- Se não encontrar um campo, value = null e confidence = 0
- Não invente valores
"""
```

### Prompt para `scanned_image`

```python
PROMPT_RECIBO_SCANNED = """
Você é um sistema especialista em extração de dados de recibos de pagamento de condomínios brasileiros.

O texto fornecido vem de OCR de imagem escaneada. Recibos escaneados frequentemente:
- são manuscritos ou semi-manuscritos
- contêm valor por extenso além do valor numérico
- não têm número de recibo formal

Extraia os seguintes campos:

- Nome de quem recebeu o pagamento
- Nome de quem efetuou o pagamento (geralmente o condomínio)
- CPF ou CNPJ do recebedor
- CPF ou CNPJ do pagador
- Número do recibo (se houver)
- Descrição do pagamento
- Data do pagamento
- Valor recebido (preferir valor numérico; se ausente, converter o valor por extenso para float)
- Forma de pagamento

Regras:
- Se houver valor por extenso e numérico, prefira o numérico
- "Pix", "pix", "PIX" → forma_pagamento = "PIX"
- Se não encontrar um campo, value = null e confidence = 0
- Use confiança baixa para campos inferidos a partir de texto manuscrito ruidoso
"""
```

### Exemplos Few-Shot

#### `digital_pdf` — Recibo de Prestador de Serviço

**Texto bruto (input):**

```
RECIBO DE PAGAMENTO

Recibo Nº: 00147

Recebi do CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL
CNPJ: 02.315.237/0001-97

a importância de R$ 2.400,00 (dois mil e quatrocentos reais),
referente à prestação de serviços de manutenção elétrica nas
áreas comuns do edifício, realizada em 28/04/2025.

Recebedor: JOÃO FERREIRA ELÉTRICA ME
CNPJ: 47.821.033/0001-72

Data: 02/05/2025
Forma de pagamento: PIX
```

**Saída esperada (output):**

```json
{
  "recebedor_nome":       { "value": "JOÃO FERREIRA ELÉTRICA ME", "confidence": 0.99 },
  "pagador_nome":         { "value": "CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL", "confidence": 0.99 },
  "cpf_cnpj_recebedor":   { "value": "47821033000172", "confidence": 0.98 },
  "cpf_cnpj_pagador":     { "value": "02315237000197", "confidence": 0.98 },
  "numero_recibo":        { "value": "00147", "confidence": 0.99 },
  "descricao_pagamento":  { "value": "Prestação de serviços de manutenção elétrica nas áreas comuns do edifício", "confidence": 0.97 },
  "data_pagamento":       { "value": "02/05/2025", "confidence": 0.99 },
  "valor_recebido":       { "value": 2400.0, "confidence": 0.99 },
  "forma_pagamento":      { "value": "PIX", "confidence": 0.99 }
}
```

```python
FEW_SHOT_RECIBO_DIGITAL = [
    {
        "role": "user",
        "content": (
            "Texto do documento:\n"
            "RECIBO DE PAGAMENTO\n"
            "Recibo Nº: 00147\n"
            "Recebi do CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL\n"
            "CNPJ: 02.315.237/0001-97\n"
            "a importância de R$ 2.400,00 (dois mil e quatrocentos reais),\n"
            "referente à prestação de serviços de manutenção elétrica nas\n"
            "áreas comuns do edifício, realizada em 28/04/2025.\n"
            "Recebedor: JOÃO FERREIRA ELÉTRICA ME\n"
            "CNPJ: 47.821.033/0001-72\n"
            "Data: 02/05/2025\n"
            "Forma de pagamento: PIX"
        )
    },
    {
        "role": "assistant",
        "content": """{
  "recebedor_nome":       { "value": "JOÃO FERREIRA ELÉTRICA ME", "confidence": 0.99 },
  "pagador_nome":         { "value": "CONDOMÍNIO DO EDIFÍCIO RECIFE COLONIAL", "confidence": 0.99 },
  "cpf_cnpj_recebedor":   { "value": "47821033000172", "confidence": 0.98 },
  "cpf_cnpj_pagador":     { "value": "02315237000197", "confidence": 0.98 },
  "numero_recibo":        { "value": "00147", "confidence": 0.99 },
  "descricao_pagamento":  { "value": "Prestação de serviços de manutenção elétrica nas áreas comuns do edifício", "confidence": 0.97 },
  "data_pagamento":       { "value": "02/05/2025", "confidence": 0.99 },
  "valor_recebido":       { "value": 2400.0, "confidence": 0.99 },
  "forma_pagamento":      { "value": "PIX", "confidence": 0.99 }
}"""
    }
]
```

### O que esses exemplos ensinam ao modelo (`recibo`)

| Campo | Padrão aprendido |
|-------|-----------------|
| `recebedor_nome` / `pagador_nome` | Inferir os papéis a partir do verbo ("Recebi do...") |
| `descricao_pagamento` | Sintetizar o motivo sem copiar o valor por extenso |
| `numero_recibo` | Extrair de "Recibo Nº:" mesmo quando não é campo rotulado |
| `forma_pagamento` | Normalizar variações de grafia para maiúsculas |

### Diferença entre as abordagens

| Aspecto | `digital_pdf` | `scanned_image` |
|---------|--------------|-----------------|
| Identificação de papéis | Campos rotulados | Inferência a partir do corpo narrativo |
| Valor | Claro e formatado | Pode ser manuscrito; valor por extenso pode ser mais legível |
| Forma de pagamento | Campo explícito | Pode estar no rodapé ou ausente |
| Número do recibo | Geralmente presente | Recibos informais podem não ter numeração |

---

## Integração: Roteamento por Tipo de Documento

Estende a **Etapa 4** (escolha dinâmica de prompt) para suportar todos os tipos de documentos.

### Schemas por tipo de documento

```python
SCHEMAS = {
    "nota_fiscal": NotaFiscalSchema,
    "fatura":      FaturaCondominio,
    "boleto":      BoletoCondominio,
    "recibo":      ReciboCondominio,
}
```

### Prompts e few-shots por tipo e qualidade de OCR

```python
PROMPTS = {
    "nota_fiscal": {"digital_pdf": PROMPT_DIGITAL,         "scanned_image": PROMPT_SCANNED},
    "fatura":      {"digital_pdf": PROMPT_FATURA_DIGITAL,  "scanned_image": PROMPT_FATURA_SCANNED},
    "boleto":      {"digital_pdf": PROMPT_BOLETO_DIGITAL,  "scanned_image": PROMPT_BOLETO_SCANNED},
    "recibo":      {"digital_pdf": PROMPT_RECIBO_DIGITAL,  "scanned_image": PROMPT_RECIBO_SCANNED},
}

FEW_SHOTS = {
    "nota_fiscal": {"digital_pdf": FEW_SHOT_DIGITAL,        "scanned_image": FEW_SHOT_SCANNED},
    "fatura":      {"digital_pdf": FEW_SHOT_FATURA_DIGITAL, "scanned_image": []},
    "boleto":      {"digital_pdf": FEW_SHOT_BOLETO_DIGITAL, "scanned_image": []},
    "recibo":      {"digital_pdf": FEW_SHOT_RECIBO_DIGITAL, "scanned_image": []},
}
```

### Função de extração genérica

```python
def extrair_dados_generico(document: dict) -> BaseModel:
    doc_category = document["document_category"]   # "nota_fiscal", "fatura", "boleto", "recibo"
    doc_type     = document["document_type"]        # "digital_pdf" ou "scanned_image"

    schema    = SCHEMAS[doc_category]
    prompt    = PROMPTS[doc_category].get(doc_type, PROMPTS[doc_category]["digital_pdf"])
    few_shots = FEW_SHOTS[doc_category].get(doc_type, [])

    messages = [
        {"role": "system", "content": prompt},
        *few_shots,
        {"role": "user", "content": f"Texto do documento:\n{document['raw_text']}"}
    ]

    response = client.responses.parse(
        model="gpt-4.1",
        input=messages,
        response_format=schema,
    )

    return response.output_parsed
```

### Resumo dos tipos suportados

| Tipo de documento | Schema | Campos-chave | Fallback regex |
|-------------------|--------|--------------|----------------|
| `nota_fiscal` | `NotaFiscalSchema` | CNPJ, valor_nota, retencao | `extrair_valor_regex` |
| `fatura` | `FaturaCondominio` | CNPJ emitente, valor_total, data_vencimento | `extrair_valor_regex` |
| `boleto` | `BoletoCondominio` | linha_digitavel, valor_boleto, data_vencimento | `extrair_valor_regex` |
| `recibo` | `ReciboCondominio` | valor_recebido, data_pagamento, forma_pagamento | `extrair_valor_regex` |
