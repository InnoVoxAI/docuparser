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
