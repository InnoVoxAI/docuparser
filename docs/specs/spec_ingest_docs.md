# 📄 Sistema de Ingestão de Documentos – Especificação v2

## 1. 🎯 Objetivo

Construir um sistema distribuído para ingestão, processamento, extração e validação de documentos financeiros (faturas, boletos e documentos em papel digitalizados), com integração ao sistema de gestão de condomínios via API do **Superlógica**.

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

### 2.3 📄 Documentos em Papel (NOVO)

Documentos físicos recebidos pela empresa serão:

1. Escaneados via scanner corporativo
2. Convertidos para PDF ou imagem
3. Inseridos manualmente ou automaticamente no sistema

#### Fluxo:

```
Documento físico → Scanner → Upload na aplicação → Pipeline OCR
```

#### Requisitos:

* Upload via interface web ou pasta monitorada
* Associação opcional a lote (batch)
* Metadados: operador, data de digitalização, origem = "paper"

---

## 3. 🧠 Classificação de Documento

O sistema deve classificar automaticamente:

* PDF com texto
* PDF escaneado
* Imagem (JPG/PNG)
* Documento escaneado de papel

Saída:

```json
{
  "type": "boleto | fatura",
  "content_type": "pdf_text | scanned_pdf | image | paper_scan"
}
```

---

## 4. 🔍 OCR + LangExtract

### 4.1 OCR

* Extração de texto bruto
* Normalização de ruído (scan/whatsapp)

---

### 4.2 LangExtract (Extração Estruturada)

Transforma texto em dados estruturados:

Exemplo:

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

## 5. 👨‍💼 Validação Humana (Human-in-the-loop)

Interface React para operadores:

* Visualização do documento original
* Dados extraídos pelo sistema
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

## 6. 🧑‍💼 Perfis de Usuário

### Operador

* Visualiza documentos
* Corrige dados
* Aprova/rejeita

---

### Supervisor (NOVO)

Responsável por **configuração avançada de extração**:

#### Permissões:

* Editar templates do LangExtract
* Ajustar regras de parsing
* Definir novos campos extraídos
* Versionar configurações

#### Exemplo de configuração:

```json
{
  "document_type": "boleto",
  "fields": [
    {"name": "valor", "type": "currency"},
    {"name": "vencimento", "type": "date"},
    {"name": "fornecedor", "type": "string"}
  ]
}
```

#### Impacto:

* Ajusta comportamento do pipeline sem deploy
* Versionamento de schemas

---

## 7. 🔗 Integração Superlógica

Após aprovação:

* Envio via API
* Mapeamento de contas a pagar
* Controle de idempotência

---

## 8. 🏗️ Arquitetura

### Componentes:

* backend-core (Django)
* backend-ocr (Python)
* fila assíncrona (Redis/RabbitMQ)
* PostgreSQL
* frontend React

---

## 9. 🔄 Pipeline Assíncrono

```
Ingestão → Classificação → OCR → LangExtract → Validação → Integração
```

* Celery (chain / group / chord)
* Processamento distribuído
* Escalabilidade horizontal OCR


