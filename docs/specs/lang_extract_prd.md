A UI para LangExtract deve ser tratada como uma **tela de configuração de extração estruturada**, não apenas como “prompt editor”. O LangExtract trabalha bem quando recebe instruções claras, exemplos few-shot e consegue manter vínculo com o texto-fonte para validação visual. ([GitHub][1])

## Especificação sugerida da UI

### 1. Tela: Modelo de Extração

**Objetivo:** configurar como um tipo de documento será extraído.

Campos principais:

| Campo             | Função                                                         |
| ----------------- | -------------------------------------------------------------- |
| Nome do modelo    | Ex: “Boleto Bancário”, “Nota Fiscal”, “Contrato de Fornecedor” |
| Tipo de documento | Seleção ligada à classificação anterior                        |
| Layout            | Ex: tabela, formulário, carta, e-mail, recibo, boleto          |
| Versão            | Permite versionar prompts e schemas                            |
| Status            | Rascunho, em teste, aprovado, desativado                       |

---

### 2. Aba: Texto OCR de Referência

Mostrar o texto bruto extraído pelo OCR:

```text
CONDOMÍNIO EDIFÍCIO ALVORADA
Fornecedor: ABC Limpeza Ltda
CNPJ: 12.345.678/0001-90
Valor: R$ 2.450,00
Vencimento: 10/05/2026
```

Funcionalidades:

* visualização do texto OCR;
* destaque de linhas, blocos e páginas;
* comparação com imagem/PDF original;
* indicação de confiança do OCR;
* marcação de ruídos: cabeçalho, rodapé, carimbo, assinatura, tabela etc.

---

### 3. Aba: Schema de Saída

Aqui o utilizador define **o que deve ser extraído**.

Exemplo visual:

| Campo           | Tipo    | Obrigatório | Regra                                |
| --------------- | ------- | ----------- | ------------------------------------ |
| fornecedor_nome | string  | sim         | extrair exatamente como aparece      |
| fornecedor_cnpj | string  | não         | normalizar para `00.000.000/0000-00` |
| valor_total     | decimal | sim         | remover R$, converter vírgula        |
| vencimento      | date    | sim         | formato ISO `YYYY-MM-DD`             |
| documento_tipo  | enum    | sim         | boleto, nota_fiscal, contrato        |

Também permitir edição em JSON:

```json
{
  "fornecedor_nome": "string",
  "fornecedor_cnpj": "string",
  "valor_total": "decimal",
  "vencimento": "date",
  "documento_tipo": "enum"
}
```

---

### 4. Aba: Instruções LangExtract

Editor de prompt com template controlado.

Exemplo:

```text
Extraia os campos financeiros do documento.

Regras:
- Use somente informações presentes no texto.
- Não invente valores ausentes.
- Extraia o valor exatamente associado ao campo.
- Preserve rastreabilidade com o trecho original.
- Quando houver múltiplos valores, escolha o valor total final.
- Se o campo não existir, retorne null.
```

A UI deve ter blocos prontos:

* “não inventar dados”;
* “usar texto exato”;
* “normalizar datas”;
* “extrair valores monetários”;
* “tratar múltiplas ocorrências”;
* “ignorar rodapé/cabeçalho”;
* “priorizar tabelas”;
* “priorizar campos próximos ao rótulo”.

---

### 5. Aba: Exemplos Few-shot

Essa é uma das partes mais importantes.

A UI deve permitir o utilizador selecionar um trecho OCR e marcar a extração correta.

Exemplo:

**Texto:**

```text
Fornecedor: ABC Limpeza Ltda
Valor total: R$ 2.450,00
Vencimento: 10/05/2026
```

**Extrações esperadas:**

```json
{
  "fornecedor_nome": "ABC Limpeza Ltda",
  "valor_total": 2450.00,
  "vencimento": "2026-05-10"
}
```

Para cada exemplo:

| Campo           | Valor esperado   | Trecho fonte                   |
| --------------- | ---------------- | ------------------------------ |
| fornecedor_nome | ABC Limpeza Ltda | `Fornecedor: ABC Limpeza Ltda` |
| valor_total     | 2450.00          | `Valor total: R$ 2.450,00`     |
| vencimento      | 2026-05-10       | `Vencimento: 10/05/2026`       |

---

### 6. Aba: Teste de Extração

Fluxo:

1. carregar documento real;
2. mostrar OCR bruto;
3. executar LangExtract;
4. mostrar JSON extraído;
5. destacar no texto os trechos usados.

Layout ideal:

```text
[Imagem/PDF original] | [Texto OCR com highlights] | [JSON extraído]
```

Exemplo de saída:

```json
{
  "fornecedor_nome": {
    "value": "ABC Limpeza Ltda",
    "source": "Fornecedor: ABC Limpeza Ltda",
    "confidence": 0.92
  },
  "valor_total": {
    "value": 2450.00,
    "source": "Valor total: R$ 2.450,00",
    "confidence": 0.95
  }
}
```

---

### 7. Aba: Validação Humana

O operador deve poder corrigir os campos extraídos.

| Campo           | Valor extraído   | Correção   | Status    |
| --------------- | ---------------- | ---------- | --------- |
| fornecedor_nome | ABC Limpeza Ltda | —          | aprovado  |
| valor_total     | 2450.00          | —          | aprovado  |
| vencimento      | null             | 2026-05-10 | corrigido |

Essas correções podem alimentar novos exemplos para melhorar o prompt/schema.

---

### 8. Aba: Regras de Pós-processamento

Após LangExtract, aplicar regras determinísticas:

* normalização de datas;
* normalização de moeda;
* validação de CNPJ/CPF;
* validação de IBAN/NIB, se aplicável;
* cálculo de total;
* comparação com dados do fornecedor;
* matching com contrato;
* validação contra Superlógica/API bancária.

Exemplo:

```json
{
  "valor_total": {
    "type": "decimal",
    "required": true,
    "min": 0
  },
  "fornecedor_cnpj": {
    "type": "cnpj",
    "validate_checksum": true
  }
}
```

---

## Componentes principais da UI

Eu desenharia a UI assim:

```text
Configuração de Extração
 ├── Dados gerais
 ├── Tipo de documento
 ├── Layout esperado
 ├── Schema de campos
 ├── Prompt/Instruções
 ├── Exemplos anotados
 ├── Teste com documento real
 ├── Validação visual
 ├── Regras de normalização
 └── Publicação da versão
```

## Fluxo recomendado

```text
OCR bruto
  ↓
Classificação do documento
  ↓
Classificação de layout
  ↓
Escolha do modelo LangExtract
  ↓
Extração estruturada
  ↓
Validação humana
  ↓
Normalização
  ↓
Envio para sistema gerencial / workflow
```

## Entidades no banco

Principais tabelas/coleções:

```text
extraction_template
extraction_schema
extraction_prompt
extraction_example
extraction_run
extraction_result
extraction_validation
extraction_version
```

## Recomendação prática

Não deixe o supervisor editar apenas um “prompt livre”. Crie uma UI guiada com:

* schema obrigatório;
* exemplos anotados;
* regras de normalização;
* teste visual;
* versionamento;
* aprovação antes de publicar.

Assim o LangExtract vira uma peça configurável e auditável dentro do sistema de ingestão, em vez de uma chamada opaca para LLM.

[1]: https://github.com/google/langextract?utm_source=chatgpt.com "google/langextract: A Python library for extracting ..."
