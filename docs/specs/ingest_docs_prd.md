# 📄 Sistema de Ingestão de Documentos – Especificação v3

## 1. 🎯 Objetivo

Construir um sistema distribuído para ingestão, processamento, extração e validação de documentos financeiros (faturas, boletos e documentos em papel digitalizados), com integração ao sistema de gestão de condomínios via API do **Superlógica**.

A arquitetura inclui agora uma etapa explícita de **classificação de layout de documento**, essencial para suportar múltiplos formatos reais.

---

## 2. 📥 Canais de Entrada de Documentos

### 2.1 Email

* Integração com API de e-mail existente
* Suporte a múltiplos anexos
* Cada e-mail pode gerar múltiplos documentos

---

### 2.2 WhatsApp

* Integração via webhook
* Suporte a imagens e PDFs
* Compressão e baixa qualidade devem ser tratados no OCR

---

### 2.3 📄 Documentos em Papel

Documentos físicos recebidos pela empresa serão:

1. Escaneados via scanner corporativo
2. Convertidos para PDF ou imagem
3. Inseridos manualmente ou automaticamente no sistema

#### Fluxo:

```
Documento físico → Scanner → Upload → Pipeline OCR
```

#### Requisitos:

* Upload via interface web ou pasta monitorada
* Associação opcional a lote (batch)
* Metadados: operador, data de digitalização, origem = "paper"

---

## 3. 🧠 Classificação de Documento

O sistema deve classificar automaticamente:

* Tipo de documento: boleto | fatura
* Tipo de conteúdo:

  * pdf_text
  * scanned_pdf
  * image
  * paper_scan

### Saída:

```json
{
  "document_type": "boleto",
  "content_type": "scanned_pdf"
}
```

---

## 4. 🧩 Classificação de Layout (NOVO)

Após o OCR, o sistema deve identificar o **layout específico do documento**.

### 🎯 Objetivo

Permitir a correta aplicação do schema de extração no LangExtract.

---

### Exemplos de layout

* boleto_caixa
* boleto_bb
* boleto_bradesco
* fatura_energia
* fatura_condominio

---

### Entrada

```json
{
  "raw_text": "...",
  "document_type": "boleto"
}
```

---

### Saída

```json
{
  "layout": "boleto_caixa",
  "confidence": 0.93
}
```

---

### Estratégias de implementação

* heurísticas (regex / palavras-chave)
* modelo de classificação (ML leve)
* LLM (classificação semântica)

---

### Fluxos alternativos

* Layout não identificado → usar schema genérico
* Baixa confiança → enviar para validação humana

---

## 5. 🔍 OCR + LangExtract

### 5.1 OCR (backend-ocr)

* Extração de texto bruto
* Normalização de ruído

---

### 5.2 LangExtract (microserviço)

Transforma texto em dados estruturados com base em:

* document_type
* layout
* versão do schema

---

### Entrada

```json
{
  "raw_text": "...",
  "document_type": "boleto",
  "layout": "boleto_caixa",
  "schema_version": "v2"
}
```

---

### Saída

```json
{
  "valor": 123.45,
  "vencimento": "2026-05-01",
  "linha_digitavel": "..."
}
```

---

## 6. 👨‍💼 Validação Humana

Interface React para operadores:

* Visualização do documento
* Dados extraídos
* Correção manual
* Aprovação/Rejeição

### Estados:

* RECEIVED
* PROCESSING
* EXTRACTED
* PENDING_VALIDATION
* APPROVED
* REJECTED
* SENT_TO_SUPERLOGICA

---

## 7. 🧑‍💼 Perfis de Usuário

### Operador

* Valida documentos
* Corrige dados
* Aprova/rejeita

---

### Supervisor

Responsável por configuração de extração baseada em:

* tipo de documento
* layout
* versão de schema

---

### Modelo de configuração

```json
{
  "document_type": "boleto",
  "layout": "boleto_caixa",
  "version": "v2",
  "fields": [
    {"name": "valor", "type": "currency"},
    {"name": "vencimento", "type": "date"}
  ]
}
```

---

## 8. 🔗 Integração Superlógica

Após aprovação:

* Envio via API
* Mapeamento financeiro
* Controle de idempotência

---

## 9. 🏗️ Arquitetura

Componentes:

* backend-core (orquestrador)
* backend-ocr (OCR + classificação básica)
* serviço de classificação de layout
* langextract-service (LLM)
* fila assíncrona
* PostgreSQL
* frontend React

---

## 10. 🔄 Pipeline Assíncrono (ATUALIZADO)

```
Ingestão
   ↓
Classificação de Documento
   ↓
OCR
   ↓
Classificação de Layout
   ↓
LangExtract
   ↓
Validação
   ↓
Integração
```

---

## 11. 📌 Benefícios da Classificação de Layout

* Suporte a múltiplos formatos reais de documentos
* Maior acurácia na extração
* Redução de intervenção manual
* Evolução independente por layout

---

## 12. ⚠️ Considerações

* Layouts devem ser versionados
* Deve existir fallback para layouts desconhecidos
* Classificação deve fornecer score de confiança
* Supervisor deve poder criar novos layouts sem deploy
