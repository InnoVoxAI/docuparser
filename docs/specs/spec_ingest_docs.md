# 📄 Sistema de Ingestão de Documentos – Especificação v3 (Arquitetura com LangExtract Microservice)

## 1. 🎯 Objetivo

Construir um sistema distribuído para ingestão, processamento, extração e validação de documentos financeiros (faturas, boletos e documentos escaneados), com integração ao sistema de gestão de condomínios via API do **Superlógica**.

A arquitetura é baseada em **processamento assíncrono orientado a eventos**, com separação clara entre OCR, orquestração e extração semântica via LLM.

---

## 2. 📥 Canais de Entrada de Documentos

### 2.1 Email

* Integração com API de e-mail existente
* Suporte a múltiplos anexos por mensagem
* Cada e-mail pode gerar múltiplos documentos

---

### 2.2 WhatsApp

* Integração via webhook
* Suporte a imagens e PDFs
* Tratamento de baixa qualidade de imagem (compressão e ruído)

---

### 2.3 📄 Documentos em Papel (Digitalização)

Documentos físicos recebidos pela empresa são incorporados ao sistema via digitalização:

1. Escaneamento via scanner corporativo
2. Conversão para PDF ou imagem
3. Upload manual ou automático no sistema

#### Fluxo:

```
Documento físico → Scanner → Upload → Pipeline OCR
```

#### Metadados obrigatórios:

* origem = "paper"
* operador responsável
* timestamp de digitalização

---

## 3. 🧠 Classificação de Documento

Responsabilidade do backend-ocr:

* PDF com texto
* PDF escaneado
* Imagem
* Documento escaneado (paper)

### Saída:

```json
{
  "document_type": "boleto | fatura",
  "content_type": "pdf_text | scanned_pdf | image | paper_scan"
}
```

---

## 4. 🔍 OCR (Backend OCR)

Responsável por:

* Extração de texto bruto
* Limpeza e normalização
* Classificação inicial

### Saída padrão:

```json
{
  "raw_text": "...",
  "confidence": 0.91,
  "document_type": "boleto"
}
```

---

## 5. 🧠 LangExtract (MICROSERVICE LLM)

### 📌 Definição

O LangExtract é um **microserviço independente baseado em LLM**, responsável pela transformação semântica do texto em dados estruturados.

Ele NÃO faz parte do backend-ocr.

---

### 🧩 Responsabilidades

* Extração estruturada via LLM
* Aplicação de schema dinâmico
* Validação semântica de campos
* Versionamento de regras de extração

---

### 📥 Entrada

```json
{
  "raw_text": "...",
  "schema_version": "boleto_v3"
}
```

---

### 📤 Saída

```json
{
  "tipo": "boleto",
  "valor": 123.45,
  "vencimento": "2026-05-01",
  "linha_digitavel": "...",
  "fornecedor": "Empresa X"
}
```

---

### 🤖 Dependência de LLM

Sim.

O LangExtract utiliza LLM para:

* interpretação de linguagem natural
* resolução de ambiguidades
* extração baseada em schema

Pode ser implementado via:

* API (OpenAI / Claude / etc.)
* ou modelo local (open-source)

---

## 6. 🏗️ Backend Core (Orquestrador)

Responsável por:

* orquestração do pipeline
* controle de estado do documento
* integração entre serviços
* persistência
* validação humana

---

### 🔄 Pipeline orquestrado

```
Ingestão → OCR → LangExtract → Validação → Integração
```

---

## 7. 👨‍💼 Validação Humana (Human-in-the-loop)

Interface React:

* visualização do documento
* comparação OCR vs dados extraídos
* correção manual
* aprovação/rejeição

### Estados:

* RECEIVED
* PROCESSING
* EXTRACTED
* PENDING_VALIDATION
* APPROVED
* REJECTED
* SENT_TO_SUPERLOGICA

---

## 8. 🧑‍💼 Perfis de Usuário

### Operador

* valida documentos
* corrige dados extraídos

### Supervisor

* define schemas do LangExtract
* versiona regras de extração
* ajusta campos sem necessidade de deploy

---

## 9. 🔗 Integração Superlógica

Após aprovação:

* envio via API
* integração com contas a pagar
* controle de idempotência (evitar duplicação)

---

## 10. 🏗️ Arquitetura Geral

### Componentes:

* backend-core (Django) → orquestrador
* backend-ocr → OCR + classificação
* langextract-service → LLM extraction microservice
* queue (Redis/RabbitMQ)
* PostgreSQL
* frontend React

---

## 11. 🔄 Arquitetura de Execução

```
Email / WhatsApp / Scanner
          ↓
     Backend Core (Orquestrador)
          ↓
      Queue (Celery)
          ↓
     Backend OCR
          ↓
     raw_text
          ↓
 LangExtract Service (LLM)
          ↓
 structured JSON
          ↓
 Backend Core
          ↓
 Validação Humana
          ↓
 Superlógica API
```




