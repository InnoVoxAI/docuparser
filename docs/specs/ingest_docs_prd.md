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

---

## 13. 🏗️ Arquitetura do Sistema (ATUALIZADA)

### 13.1 Microserviços

| Microserviço | Tecnologia | Responsabilidade |
|--------------|------------|------------------|
| **backend-core** | Django | Orquestrador, gerenciamento de jobs, persistência |
| **backend-ocr** | FastAPI | OCR, classificação básica de documento |
| **backend-com** | Django/FastAPI | Comunicação com sistemas externos (Email, WhatsApp, Upload manual) |
| **backend-conect** | Django/FastAPI | Integração com ERPs (Superlógica, outros) |
| **layout-service** | Python/ML | Classificação de layout de documento |
| **langextract-service** | Python + LLM | Extração semântica baseada em schema |

### 13.2 Backend COM (NOVO)

O **backend-com** é um microserviço responsável por:

* **Integração com Superlógica API**
  - Envio de dados aprovados
  - Mapeamento financeiro
  - Controle de idempotência

* **Integração com Email API**
  - Recepção de documentos via email
  - Extração de anexos
  - Processamento em lote

* **Integração com WhatsApp API**
  - Recepção de documentos via webhook
  - Compressão de imagens
  - Tratamento de ruído

* **Gerenciamento de Documentos**
  - Upload via interface
  - Associação a lotes (batches)
  - Metadados de origem
  - Status de processamento

* **Webhooks**
  - Gerenciamento de notificações de status
  - Retries automáticos
  - Logging de comunicações

### 13.3 Fluxo de Integração Completo (ATUALIZADO - Arquitetura Baseada em Eventos)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Fluxo Completo do Sistema                           │
└─────────────────────────────────────────────────────────────────────────────┘

1. [Frontend] → [Backend COM] (Upload de documento)
   POST /api/v1/documents/manual
   {
     "file": "binary",
     "metadata": {...}
   }

2. [Backend COM] → [Queue] (Evento: document.received)
   {
     "event": "document.received",
     "document_id": "uuid",
     "source": "manual",
     "file_path": "..."
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

12. [Backend Core] → [Backend CONECT] (Aprovação)
    POST /api/v1/erp/superlogica
    {
      "document_id": "uuid",
      "data": {...}
    }

13. [Backend CONECT] → [Superlógica API] (Envio para ERP)
    POST https://api.superlogica.com/v1/financeiro

14. [Superlógica API] → [Backend CONECT] (Confirmação)
    {
      "id": "123456",
      "status": "success"
    }

15. [Backend CONECT] → [Queue] (Evento: sent.to.erp)
    {
      "event": "sent.to.erp",
      "document_id": "uuid",
      "erp_id": "123456"
    }

16. [Backend Core] ← [Queue] (Consumidor de eventos)
    Atualiza status final
```

### 13.4 Contratos de API entre Microserviços

#### Backend Core ↔ Backend COM

```python
# Backend Core → Backend COM
POST /api/v1/documents
Request:
{
  "file": "binary",
  "batch_id": "uuid",
  "metadata": {...}
}

Response:
{
  "id": "uuid",
  "status": "RECEIVED",
  "created_at": "datetime"
}

# Backend Core → Backend COM
POST /api/v1/documents/:id/approve
Request:
{
  "approved_by": "user_id"
}

Response:
{
  "id": "uuid",
  "status": "APPROVED",
  "approved_at": "datetime"
}

# Backend Core → Backend COM
POST /api/v1/documents/:id/validate
Request:
{
  "data": {...},
  "validated_by": "user_id"
}

Response:
{
  "id": "uuid",
  "status": "PENDING_VALIDATION",
  "validated_at": "datetime"
}
```

### 13.5 Pipeline Assíncrono (ATUALIZADO)

```
Ingestão (Email/WhatsApp/Scanner)
   ↓
Backend Core (Recepção e criação de Document)
   ↓
Backend OCR (OCR + classificação básica)
   ↓
Layout Service (Classificação de layout)
   ↓
LangExtract Service (Extração semântica)
   ↓
Backend Core (Persistência e validação)
   ↓
Backend COM (Aprovação e integração)
   ↓
Superlógica API (Envio para sistema externo)
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
| **API Keys** | Chaves de API para Superlógica, OpenRouter, etc. | PostgreSQL (tenant_api_keys) |
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
    "service": "superlogica|openrouter|ollama",
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
  • Service (dropdown: Superlógica, OpenRouter, Ollama)
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
```

### 14.4 Logging

#### Estrutura de Logs

```python
# Log Format (JSON)
{
    "timestamp": "2026-04-30T10:30:00Z",
    "level": "INFO|WARN|ERROR",
    "service": "backend-core|backend-ocr|backend-com|layout-service|langextract-service",
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

## 15. 📋 Checklist de Implementação

### Fase 1 — Backend COM
- [ ] Criar estrutura de diretórios
- [ ] Implementar endpoints de documentos
- [ ] Implementar endpoints de integrações
- [ ] Integrar com Superlógica API
- [ ] Integrar com Email API
- [ ] Integrar com WhatsApp API

### Fase 2 — Configuração Multi-Tenant
- [ ] Criar models de tenant
- [ ] Implementar endpoints de configuração
- [ ] Criar interface gráfica de configuração
- [ ] Implementar criptografia de credenciais

### Fase 3 — Observabilidade
- [ ] Integrar OpenTelemetry em todos os microserviços
- [ ] Configurar OpenTelemetry Collector
- [ ] Configurar Grafana dashboards
- [ ] Implementar alerts

### Fase 4 — Logging e Tratamento de Exceções
- [ ] Implementar estrutura de logs
- [ ] Criar handlers de exceções
- [ ] Implementar retry automático
- [ ] Criar sistema de notificações

### Fase 5 — Frontend
- [ ] Implementar tela de dashboard
- [ ] Implementar tela de inbox
- [ ] Implementar tela de configuração
- [ ] Implementar tela de validação

---

## 16. 📚 Referências

- [Architecture PRD](./architecture_prd.md)
- [Use Cases](./use_cases.md)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Django Documentation](https://docs.djangoproject.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
