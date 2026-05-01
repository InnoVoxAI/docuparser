# 📄 Sistema de Ingestão de Documentos – Especificação v3

## 1. 🎯 Objetivo

Construir um sistema distribuído para ingestão, processamento, extração e validação de documentos financeiros (faturas, boletos e documentos em papel digitalizados), com integração a ERPs externos, iniciando pelo **Superlógica**.

A arquitetura inclui agora uma etapa explícita de **classificação de layout de documento**, essencial para suportar múltiplos formatos reais.

O fluxo funcional obrigatório é:

```
captura de dados -> OCR -> Layout -> LangExtract -> validação pelo usuário -> interface com ERP
```

Cada etapa deve ser implementada como módulo/microserviço completo, testável isoladamente e conectado ao restante do sistema pelo orquestrador e por eventos em fila.

---

## 2. 📥 Canais de Entrada de Documentos

### 2.1 Email

* Integração com a arquitetura de e-mail já existente no **backend-com**
* API própria para captura de e-mail, independente da API de WhatsApp
* Suporte a webhook de provedores de e-mail/inbound parse quando disponível
* Suporte a polling/IMAP como adaptador secundário quando o provedor não oferecer webhook
* Suporte a múltiplos anexos
* Cada e-mail pode gerar múltiplos documentos
* Publicação de evento `document.received` para cada anexo aceito

#### API esperada

```http
POST /api/v1/email/webhook
POST /api/v1/email/messages
GET /api/v1/email/accounts
POST /api/v1/email/accounts
```

---

### 2.2 WhatsApp

* Integração com a arquitetura de WhatsApp já existente no **backend-com**
* API própria para captura de WhatsApp, independente da API de e-mail
* Integração via webhook
* Suporte a imagens e PDFs
* Compressão e baixa qualidade devem ser tratados no OCR
* Publicação de evento `document.received` para cada mídia aceita

#### API esperada

```http
POST /api/v1/whatsapp/webhook
GET /api/v1/whatsapp/numbers
POST /api/v1/whatsapp/numbers
POST /api/v1/whatsapp/messages/test
```

---

### 2.3 📄 Documentos em Papel

Documentos físicos recebidos pela empresa serão:

1. Escaneados via scanner corporativo
2. Convertidos para PDF ou imagem
3. Enviados pelo usuário em tela web dedicada
4. Complementados com as informações pertinentes antes do envio ao pipeline

#### Fluxo:

```
Documento físico → Scanner → Upload na interface → Metadados → Pipeline OCR
```

#### Requisitos:

* Upload via interface web como caminho principal
* Pasta monitorada como caminho opcional para automação futura
* Associação opcional a lote (batch)
* Metadados mínimos: operador, data de digitalização, origem = "paper", tenant, condomínio/unidade quando aplicável, tipo esperado do documento, observações
* Validação de formato, tamanho, duplicidade e legibilidade básica antes de publicar o evento de ingestão
* Publicação de evento `document.received` após upload e validação inicial

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
* Aproveitamento da arquitetura já implementada do **backend-ocr**, incluindo FastAPI, classificação básica, roteamento por engine e estratégias de fallback existentes
* Interface síncrona interna para testes e chamadas externas futuras
* Consumidor assíncrono de fila para operação normal no pipeline distribuído
* Publicação do evento `ocr.completed`

---

### 5.2 LangExtract (microserviço)

Transforma texto em dados estruturados com base em:

* document_type
* layout
* versão do schema

O **langextract-service** deve ser um microserviço separado, autônomo e versionado. Ele deve expor API própria para execução isolada, consumir eventos do pipeline e publicar o resultado da extração estruturada.

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
* ERP_INTEGRATION_REQUESTED
* SENT_TO_ERP
* ERP_INTEGRATION_FAILED

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

## 8. 🔗 Integração ERP via Backend CONECT

Após aprovação:

* O **backend-core** publica o evento `erp.integration.requested`
* O **backend-conect** consome o evento, normaliza o payload e envia ao ERP configurado
* O primeiro conector previsto é o **Superlógica**
* O desenho deve permitir novos ERPs sem alterar OCR, Layout, LangExtract ou validação
* Devem existir mapeamento financeiro, controle de idempotência e rastreabilidade por tentativa de envio

---

## 9. 🏗️ Arquitetura

Componentes:

* backend-core (orquestrador)
* backend-com (captura de email, WhatsApp e upload manual)
* backend-ocr (OCR + classificação básica)
* serviço de classificação de layout
* langextract-service (LLM)
* backend-conect (normalização e integração com ERPs)
* fila assíncrona / event bus
* PostgreSQL
* frontend React

---

## 10. 🔄 Pipeline Assíncrono (ATUALIZADO)

```
Ingestão
   ↓
Fila: document.received
   ↓
OCR
   ↓
Fila: ocr.completed
   ↓
Classificação de Layout
   ↓
Fila: layout.classified
   ↓
LangExtract
   ↓
Fila: extraction.completed
   ↓
Validação
   ↓
Fila: erp.integration.requested
   ↓
Integração ERP
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

---

## 13. 🏗️ Arquitetura do Sistema (ATUALIZADA)

### 13.1 Microserviços

| Microserviço | Tecnologia | Responsabilidade |
|--------------|------------|------------------|
| **backend-core** | Django | Orquestrador, gerenciamento de jobs, persistência, validação humana |
| **backend-com** | FastAPI/Django | Captura por Email, WhatsApp e upload manual; publicação de eventos de entrada |
| **backend-ocr** | FastAPI | OCR, normalização de imagem/texto, classificação básica de documento |
| **layout-service** | Python/ML | Classificação de layout de documento |
| **langextract-service** | Python + LLM | Extração semântica baseada em schema |
| **backend-conect** | Django/FastAPI | Normalização e integração com ERPs externos, incluindo Superlógica |
| **queue/event bus** | Redis/RabbitMQ/Celery/Kafka | Comunicação assíncrona entre módulos |

### 13.2 Backend COM (NOVO)

O **backend-com** é um microserviço responsável por:

* **Integração com Email API**
  - Recepção de documentos via email
  - Extração de anexos
  - Processamento em lote
  - Endpoint de webhook separado de WhatsApp
  - Uso da arquitetura existente de leitura de email e filas do backend-com

* **Integração com WhatsApp API**
  - Recepção de documentos via webhook
  - Compressão de imagens
  - Tratamento de ruído
  - Endpoint de webhook separado de Email
  - Uso da arquitetura existente de WhatsApp/Twilio do backend-com

* **Gerenciamento de Documentos**
  - Upload via interface
  - Associação a lotes (batches)
  - Metadados de origem
  - Validação inicial de arquivo
  - Publicação de eventos de captura

* **Webhooks**
  - Recepção de webhooks de provedores externos
  - Validação de assinatura/token do provedor
  - Retries automáticos
  - Logging de comunicações

O **backend-com não deve integrar com ERPs**. Integrações ERP pertencem ao **backend-conect**.

### 13.2.1 Backend CONECT (NOVO)

O **backend-conect** é um microserviço responsável por:

* Normalizar dados aprovados para contratos canônicos de contas a pagar, boletos, faturas e anexos
* Mapear dados canônicos para o payload específico de cada ERP
* Implementar conectores plugáveis, começando por `superlogica`
* Controlar idempotência por `document_id`, `tenant_id`, `erp_provider` e chave externa
* Publicar eventos `erp.sent`, `erp.failed` e `erp.retry.scheduled`
* Expor API própria para testes isolados e reprocessamento controlado

#### Contrato canônico de integração

```json
{
  "document_id": "uuid",
  "tenant_id": "uuid",
  "erp_provider": "superlogica",
  "document_type": "boleto",
  "normalized_payload": {
    "supplier": {...},
    "amount": 123.45,
    "due_date": "2026-05-01",
    "barcode": "...",
    "attachments": ["s3://bucket/document.pdf"]
  }
}
```

### 13.3 Fluxo de Integração Completo (ATUALIZADO - Arquitetura Baseada em Eventos)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Fluxo Completo do Sistema                           │
└─────────────────────────────────────────────────────────────────────────────┘

1. [Fonte externa/Frontend] → [Backend COM] (Email, WhatsApp ou upload manual)
   POST /api/v1/documents/manual
   {
     "file": "binary",
     "metadata": {...},
     "source": "manual|email|whatsapp"
   }

2. [Backend COM] → [Queue/Event Bus] (Evento: document.received)
   {
     "event": "document.received",
     "document_id": "uuid",
     "source": "manual",
     "file_path": "...",
     "tenant_id": "uuid",
     "correlation_id": "uuid"
   }

3. [Backend OCR] ← [Queue] (Consumidor de eventos)
   Processa documento via OCR

4. [Backend OCR] → [Queue] (Evento: ocr.completed)
   {
     "event": "ocr.completed",
     "document_id": "uuid",
     "raw_text": "...",
     "document_type": "boleto"
   }

5. [Layout Service] ← [Queue] (Consumidor de eventos)
   Classifica layout do documento

6. [Layout Service] → [Queue] (Evento: layout.classified)
   {
     "event": "layout.classified",
     "document_id": "uuid",
     "layout": "boleto_caixa"
   }

7. [LangExtract Service] ← [Queue] (Consumidor de eventos)
   Extrai campos estruturados

8. [LangExtract Service] → [Queue] (Evento: extraction.completed)
   {
     "event": "extraction.completed",
     "document_id": "uuid",
     "data": {...}
   }

9. [Backend Core] ← [Queue] (Consumidor de eventos)
   Persiste dados e notifica usuário para validação

10. [Backend Core] → [Queue] (Evento: pending.validation)
    {
      "event": "pending.validation",
      "document_id": "uuid"
    }

11. [Frontend] → [Backend Core] (Validação pelo usuário)
    PUT /api/v1/documents/:id/validate

12. [Backend Core] → [Queue] (Evento: erp.integration.requested)
    {
      "event": "erp.integration.requested",
      "document_id": "uuid",
      "tenant_id": "uuid",
      "erp_provider": "superlogica",
      "data": {...}
    }

13. [Backend CONECT] ← [Queue] (Consumidor de eventos)
    Normaliza payload e seleciona conector ERP

14. [Backend CONECT] → [Superlógica API] (Envio para ERP)
    POST https://api.superlogica.com/v1/financeiro

15. [Superlógica API] → [Backend CONECT] (Confirmação)
    {
      "id": "123456",
      "status": "success"
    }

16. [Backend CONECT] → [Queue] (Evento: erp.sent)
    {
      "event": "erp.sent",
      "document_id": "uuid",
      "erp_provider": "superlogica",
      "erp_id": "123456"
    }

17. [Backend Core] ← [Queue] (Consumidor de eventos)
    Atualiza status final
```

### 13.4 Contratos de API e Eventos entre Microserviços

Os módulos devem se comunicar por fila/event bus na operação normal. APIs HTTP internas são permitidas para health checks, testes isolados, reprocessamento administrativo e chamadas futuras por sistemas externos.

#### Backend COM — APIs de captura

```python
# Upload manual via interface
POST /api/v1/documents/manual
Request:
{
  "file": "binary",
  "batch_id": "uuid",
  "metadata": {
    "tenant_id": "uuid",
    "operator_id": "uuid",
    "scan_date": "date",
    "expected_document_type": "boleto|fatura|unknown",
    "notes": "string"
  }
}

Response:
{
  "id": "uuid",
  "status": "RECEIVED",
  "created_at": "datetime"
}

# Email webhook
POST /api/v1/email/webhook
Request:
{
  "provider": "sendgrid|mailgun|custom",
  "message_id": "string",
  "attachments": [...]
}

Response:
{
  "accepted_documents": ["uuid"],
  "ignored_attachments": [...]
}

# WhatsApp webhook
POST /api/v1/whatsapp/webhook
Request:
{
  "provider": "twilio|meta|custom",
  "message_id": "string",
  "from": "string",
  "media": [...]
}

Response:
{
  "accepted_documents": ["uuid"],
  "status": "RECEIVED"
}
```

#### Eventos mínimos

```json
{
  "event": "document.received",
  "version": "v1",
  "document_id": "uuid",
  "tenant_id": "uuid",
  "source": "email|whatsapp|manual|watched_folder",
  "file_uri": "s3://bucket/file.pdf",
  "metadata": {},
  "correlation_id": "uuid"
}
```

```json
{
  "event": "ocr.completed",
  "version": "v1",
  "document_id": "uuid",
  "raw_text_uri": "s3://bucket/raw_text.json",
  "document_type": "boleto",
  "content_type": "scanned_pdf",
  "confidence": 0.91
}
```

```json
{
  "event": "layout.classified",
  "version": "v1",
  "document_id": "uuid",
  "layout": "boleto_caixa",
  "confidence": 0.93,
  "schema_version": "v2"
}
```

```json
{
  "event": "extraction.completed",
  "version": "v1",
  "document_id": "uuid",
  "data": {},
  "confidence": 0.88,
  "requires_human_validation": true
}
```

```json
{
  "event": "erp.integration.requested",
  "version": "v1",
  "document_id": "uuid",
  "tenant_id": "uuid",
  "erp_provider": "superlogica",
  "validated_data": {}
}
```

### 13.5 Pipeline Assíncrono (ATUALIZADO)

```
Ingestão (Email/WhatsApp/Scanner)
   ↓
Backend COM (captura separada por canal e publicação de evento)
   ↓
Queue/Event Bus (document.received)
   ↓
Backend OCR (OCR + classificação básica)
   ↓
Queue/Event Bus (ocr.completed)
   ↓
Layout Service (Classificação de layout)
   ↓
Queue/Event Bus (layout.classified)
   ↓
LangExtract Service (Extração semântica)
   ↓
Queue/Event Bus (extraction.completed)
   ↓
Backend Core (Persistência e validação)
   ↓
Queue/Event Bus (erp.integration.requested)
   ↓
Backend CONECT (normalização e conector ERP)
   ↓
Superlógica API / outros ERPs
   ↓
Backend Core (Atualização de status final)
```

### 13.6 Benefícios da Arquitetura em Microserviços

* **Escalabilidade**: Cada microserviço pode ser escalado independentemente
* **Resiliência**: Falha em um microserviço não afeta os demais
* **Manutenibilidade**: Código mais organizado e fácil de manter
* **Evolução independente**: Cada microserviço pode evoluir separadamente
* **Flexibilidade**: Fácil adicionar novos microserviços ou substituir existentes

---

## 14. ⚙️ Configuração e Observabilidade

### 14.1 Configuração Multi-Tenant

O sistema deve suportar múltiplos inquilinos (tenants) com configurações isoladas:

| Configuração | Descrição | Armazenamento |
|--------------|-----------|---------------|
| **Emails de atendimento** | Endereços de email para recepção de documentos | PostgreSQL (tenant_email) |
| **Números de WhatsApp** | Números de telefone para webhook do WhatsApp | PostgreSQL (tenant_whatsapp) |
| **API Keys** | Chaves de API para ERPs, OpenRouter, Ollama, etc. | PostgreSQL (tenant_api_keys) |
| **Webhooks** | URLs de callback para notificações | PostgreSQL (tenant_webhooks) |
| **Schemas de extração** | Modelos de extração por documento/layout | PostgreSQL (tenant_schemas) |
| **Layouts** | Definições de layout por tenant | PostgreSQL (tenant_layouts) |

#### Modelo de Dados Multi-Tenant

```python
# Tenant Model
{
    "id": "uuid",
    "name": "string",
    "domain": "string",
    "active": "boolean",
    "created_at": "datetime"
}

# Tenant Email Model
{
    "id": "uuid",
    "tenant_id": "uuid",
    "email": "string",
    "provider": "gmail|outlook|yahoo|custom",
    "enabled": "boolean",
    "config": {
        "host": "string",
        "port": "integer",
        "use_ssl": "boolean"
    },
    "created_at": "datetime"
}

# Tenant WhatsApp Model
{
    "id": "uuid",
    "tenant_id": "uuid",
    "phone_number": "string",
    "api_key": "string",
    "webhook_url": "string",
    "enabled": "boolean",
    "created_at": "datetime"
}

# Tenant API Keys Model
{
    "id": "uuid",
    "tenant_id": "uuid",
    "service": "superlogica|openrouter|ollama|outro_erp",
    "api_key": "string",
    "endpoint": "string",
    "enabled": "boolean",
    "created_at": "datetime"
}
```

### 14.2 Interface Gráfica de Configuração

A interface gráfica deve fornecer telas para:

#### Tela 1: Configuração de Emails

```python
# Componente: EmailConfig
- Lista de emails configurados
- Botão "Adicionar Email"
- Formulário de configuração:
  • Email address
  • Provider (dropdown: Gmail, Outlook, Yahoo, Custom)
  • Host, port, SSL settings
  • Test connection button
- Ações:
  • Editar
  • Excluir
  • Testar conexão
  • Habilitar/Desabilitar
```

#### Tela 2: Configuração de WhatsApp

```python
# Componente: WhatsAppConfig
- Lista de números configurados
- Botão "Adicionar Número"
- Formulário de configuração:
  • Phone number (com código do país)
  • API key (Gerada no provedor WhatsApp)
  • Webhook URL (auto-gerado ou customizável)
  • Test connection button
- Ações:
  • Editar
  • Excluir
  • Testar conexão
  • Habilitar/Desabilitar
```

#### Tela 3: Configuração de APIs

```python
# Componente: APIConfig
- Lista de APIs configuradas
- Botão "Adicionar API"
- Formulário de configuração:
  • Service (dropdown: Superlógica, outros ERPs, OpenRouter, Ollama)
  • API key
  • Endpoint URL
  • Test connection button
- Ações:
  • Editar
  • Excluir
  • Testar conexão
  • Habilitar/Desabilitar
```

#### Tela 4: Gerenciamento de Tenants

```python
# Componente: TenantManager
- Lista de tenants
- Botão "Adicionar Tenant"
- Formulário de configuração:
  • Tenant name
  • Domain (subdomínio)
  • Ativar/desativar
- Ações:
  • Editar
  • Excluir
  • Ver configurações
```

### 14.3 Tratamento de Exceções

#### Níveis de Tratamento

| Nível | Descrição | Ação |
|-------|-----------|------|
| **Nível 1** | Erros de validação | Retorno imediato com mensagem clara |
| **Nível 2** | Erros de comunicação | Retry automático (3 tentativas) |
| **Nível 3** | Erros de processamento | Log detalhado + notificação |
| **Nível 4** | Erros críticos | Alerta imediato + rollback |

#### Exceções Específicas

```python
# Erros de Email
class EmailConnectionError(Exception):
    """Erro ao conectar com servidor de email"""
    pass

class EmailAuthenticationError(Exception):
    """Erro de autenticação no servidor de email"""
    pass

class EmailAttachmentError(Exception):
    """Erro ao processar anexo"""
    pass

# Erros de WhatsApp
class WhatsAppWebhookError(Exception):
    """Erro no webhook do WhatsApp"""
    pass

class WhatsAppAPIError(Exception):
    """Erro na API do WhatsApp"""
    pass

# Erros de Superlógica
class SuperlogicaAPIError(Exception):
    """Erro na API do Superlógica"""
    pass

class SuperlogicaIdempotencyError(Exception):
    """Erro de idempotência (duplicate request)"""
    pass

# Erros de integração ERP
class ERPConnectorError(Exception):
    """Erro genérico de conector ERP"""
    pass

class ERPNormalizationError(Exception):
    """Erro ao normalizar dados para contrato canônico"""
    pass
```

### 14.4 Logging

#### Estrutura de Logs

```python
# Log Format (JSON)
{
    "timestamp": "2026-04-30T10:30:00Z",
    "level": "INFO|WARN|ERROR",
    "service": "backend-core|backend-ocr|backend-com|backend-conect|layout-service|langextract-service",
    "tenant_id": "uuid",
    "request_id": "uuid",
    "message": "Descrição do evento",
    "context": {
        "document_id": "uuid",
        "user_id": "uuid",
        "metadata": {...}
    },
    "stack_trace": "..."  # apenas para ERROR
}
```

#### Níveis de Log

| Nível | Uso | Destino |
|-------|-----|---------|
| **DEBUG** | Desenvolvimento | Console + Arquivo |
| **INFO** | Operação normal | Arquivo + Observabilidade |
| **WARN** | Situações atípicas | Arquivo + Observabilidade |
| **ERROR** | Erros | Arquivo + Observabilidade + Alerta |
| **CRITICAL** | Erros críticos | Arquivo + Observabilidade + Alerta + Email |

### 14.5 Observabilidade

#### Recomendação: OpenTelemetry

**OpenTelemetry** é a ferramenta recomendada para observabilidade do sistema:

##### Benefícios

* **Traces**: Rastreamento completo de requisições através dos microserviços
* **Metrics**: Métricas de performance, throughput, erros
* **Logs**: Logs estruturados com correlação automática

##### Implementação por Microserviço

```python
# Exemplo de configuração OpenTelemetry (Python)

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configurar tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Exportar para collector (Jaeger, Tempo, etc.)
otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Instrumentar FastAPI/Django
FastAPIInstrumentor().instrument()
RequestsInstrumentor().instrument()
```

##### Componentes de Observabilidade

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Observabilidade                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Microserviços (backend-core, backend-ocr, etc.)                           │
│  └── OpenTelemetry SDK (traces, metrics, logs)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  OpenTelemetry Collector (Jaeger, Prometheus, Loki)                        │
│  └── Recebe dados, processa e exporta                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Visualização (Grafana)                                                    │
│  └── Dashboards, alerts, logs, traces                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### Métricas Recomendadas

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `document.processing.duration` | Histogram | Tempo de processamento de documentos |
| `document.processing.errors` | Counter | Número de erros por tipo |
| `api.requests.total` | Counter | Total de requisições API |
| `api.requests.duration` | Histogram | Duração das requisições API |
| `queue.jobs.pending` | Gauge | Jobs pendentes na fila |
| `queue.jobs.processed` | Counter | Jobs processados |
| `external_api.calls.total` | Counter | Chamadas a APIs externas |
| `external_api.errors` | Counter | Erros em chamadas a APIs externas |

##### Alerts Recomendados

```yaml
# Exemplo de alertas (Prometheus AlertManager)
alerts:
  - name: high-error-rate
    expr: rate(document_processing_errors[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Alta taxa de erros no processamento de documentos"
      description: "Mais de 10% dos documentos estão falhando no processamento"

  - name: queue-backlog
    expr: queue_jobs_pending > 100
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Backlog na fila de processamento"
      description: "Mais de 100 jobs pendentes na fila"

  - name: external-api-errors
    expr: rate(external_api_errors[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Alta taxa de erros em APIs externas"
      description: "Mais de 5% das chamadas a APIs externas estão falhando"
```

### 14.6 Segurança

#### Armazenamento de Credenciais

* **Não armazenar em código**: Usar variáveis de ambiente ou secrets manager
* **Criptografia em repouso**: Credenciais criptografadas no banco de dados
* **Rotação automática**: Implementar rotação periódica de credenciais
* **Acesso baseado em papel**: Apenas administradores podem visualizar credenciais

#### Exemplo de Armazenamento Seguro

```python
# Usando cryptography library
from cryptography.fernet import Fernet

# Gerar chave (armazenar em environment variable)
key = os.environ.get('ENCRYPTION_KEY')
cipher = Fernet(key)

# Criptografar
encrypted = cipher.encrypt(b'api_key_secreta')

# Descriptografar
decrypted = cipher.decrypt(encrypted)
```

---

## 15. 🧪 Estratégia de Testes e Módulos Autônomos

### 15.1 Definição de módulo completo

Cada módulo deve poder ser executado e validado de forma independente, com:

* API própria documentada para chamadas externas futuras
* Consumidor e publicador de eventos quando participar do pipeline
* Health check, readiness check e métricas básicas
* Contratos de entrada e saída versionados
* Testes unitários, testes de contrato e testes de integração do módulo
* Idempotência para eventos reprocessados
* Logs com `correlation_id`, `tenant_id` e `document_id`

### 15.2 Testes isolados por módulo

| Módulo | Testes obrigatórios |
|--------|---------------------|
| **backend-com/email** | Webhook de email, parsing de anexos, múltiplos documentos por mensagem, rejeição de anexos inválidos, publicação de `document.received` |
| **backend-com/whatsapp** | Webhook WhatsApp, validação de assinatura/token, download de mídia, tratamento de imagem/PDF, publicação de `document.received` |
| **backend-com/upload manual** | Upload via tela, validação de metadados, associação a batch, duplicidade, publicação de `document.received` |
| **backend-ocr** | Processamento por engine, OCR de PDF texto/scanned/image, normalização de ruído, fallback, publicação de `ocr.completed` |
| **layout-service** | Classificação por heurística/modelo/LLM, score de confiança, fallback para layout genérico, publicação de `layout.classified` |
| **langextract-service** | Seleção de schema por layout/versão, extração estruturada, validação de campos obrigatórios, publicação de `extraction.completed` |
| **backend-core** | Orquestração por eventos, persistência de estados, tela/API de validação, aprovação/rejeição, publicação de `erp.integration.requested` |
| **backend-conect** | Normalização canônica, conector Superlógica, idempotência, retry, publicação de `erp.sent` e `erp.failed` |
| **frontend** | Upload manual, inbox, visualização de documento, edição/validação de campos, estados de erro e sucesso |

### 15.3 Testes de integração

* Integração por evento entre cada par de módulos: `backend-com -> backend-ocr`, `backend-ocr -> layout-service`, `layout-service -> langextract-service`, `langextract-service -> backend-core`, `backend-core -> backend-conect`
* Teste end-to-end por canal: email, WhatsApp e upload manual
* Teste de reprocessamento de evento duplicado para validar idempotência
* Teste de indisponibilidade temporária de módulo com retry e dead-letter queue
* Teste de aprovação pelo usuário e envio ao Superlógica com API mockada
* Teste de substituição do ERP por conector mock para validar extensibilidade do `backend-conect`

### 15.4 Critério de aceite técnico

O pipeline só deve ser considerado pronto quando cada módulo passar isoladamente e o fluxo completo executar com sucesso:

```
captura -> document.received -> OCR -> ocr.completed -> Layout -> layout.classified -> LangExtract -> extraction.completed -> validação -> erp.integration.requested -> backend-conect -> erp.sent
```

---

## 16. 📋 Checklist de Implementação

### Fase 1 — Backend COM
- [ ] Aproveitar arquitetura existente do backend-com
- [ ] Implementar API/webhook de Email separada
- [ ] Implementar API/webhook de WhatsApp separada
- [ ] Implementar upload manual via interface
- [ ] Publicar eventos `document.received`
- [ ] Criar testes isolados de Email, WhatsApp e upload manual

### Fase 2 — Pipeline OCR, Layout e LangExtract
- [ ] Aproveitar arquitetura existente do backend-ocr
- [ ] Implementar consumidor de eventos no backend-ocr
- [ ] Implementar/publicar `ocr.completed`
- [ ] Implementar layout-service como módulo testável
- [ ] Implementar langextract-service como microserviço separado
- [ ] Criar testes isolados para OCR, layout e LangExtract

### Fase 3 — Backend Core e Orquestração
- [ ] Consumir eventos do pipeline
- [ ] Persistir estados do documento
- [ ] Implementar validação humana
- [ ] Publicar `erp.integration.requested`
- [ ] Criar testes de orquestração e estados

### Fase 4 — Backend CONECT
- [ ] Criar microserviço backend-conect
- [ ] Definir contrato canônico de normalização
- [ ] Implementar conector Superlógica
- [ ] Implementar idempotência, retry e dead-letter
- [ ] Preparar estrutura para novos ERPs
- [ ] Criar testes isolados e com ERP mockado

### Fase 5 — Configuração Multi-Tenant
- [ ] Criar models de tenant
- [ ] Implementar endpoints de configuração
- [ ] Criar interface gráfica de configuração
- [ ] Implementar criptografia de credenciais

### Fase 6 — Observabilidade
- [ ] Integrar OpenTelemetry em todos os microserviços
- [ ] Configurar OpenTelemetry Collector
- [ ] Configurar Grafana dashboards
- [ ] Implementar alerts

### Fase 7 — Logging e Tratamento de Exceções
- [ ] Implementar estrutura de logs
- [ ] Criar handlers de exceções
- [ ] Implementar retry automático
- [ ] Criar sistema de notificações

### Fase 8 — Frontend
- [ ] Implementar tela de dashboard
- [ ] Implementar tela de inbox
- [ ] Implementar tela de upload manual com metadados
- [ ] Implementar tela de configuração
- [ ] Implementar tela de validação
- [ ] Criar testes de UI para upload e validação

### Fase 9 — Integração ponta a ponta
- [ ] Testar fluxo completo de Email até ERP
- [ ] Testar fluxo completo de WhatsApp até ERP
- [ ] Testar fluxo completo de upload manual até ERP
- [ ] Testar falhas, retries, DLQ e reprocessamento

---

## 17. 📚 Referências

- [Architecture PRD](./architecture_prd.md)
- [Use Cases](./use_cases.md)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Django Documentation](https://docs.djangoproject.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
