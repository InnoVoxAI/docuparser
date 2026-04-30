# 📋 Recomendações de Integração e Arquitetura

**Data:** 2026-04-30  
**Versão:** 2.0  
**Status:** Análise e Recomendações (Atualizada)

---

## 1. 🎯 Visão Geral

Este documento apresenta as recomendações para integração dos módulos do sistema de ingestão de documentos, incluindo a definição do **backend-com** como microserviço e a arquitetura completa com orquestração e interface gráfica.

---

## 2. 🏗️ Arquitetura Proposta

### 2.1 Diagrama de Containers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Arquitetura Completa                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React)                               │
│                         Interface Gráfica do Usuário                        │
│  • Upload de documentos                                                     │
│  • Validação manual                                                         │
│  • Visualização de dados extraídos                                          │
│  • Aprovação/Rejeição                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓ HTTP
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Backend Core (Django)                              │
│                         Orquestrador do Sistema                             │
│  • Gerenciamento de jobs                                                    │
│  • Coordenação entre serviços                                               │
│  • Persistência (PostgreSQL)                                                │
│  • Integração com Superlógica                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
        ┌───────────────────────────┼───────────────────────────┐
        ↓                           ↓                           ↓
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Backend OCR       │  │   Backend COM       │  │   Layout Service    │
│   (FastAPI)         │  │   (Django/FastAPI)  │  │   (Python/ML)       │
│                     │  │                     │  │                     │
│  • OCR (Tesseract,  │  │  • Superlógica API  │  │  • Identificação    │
│    Paddle, EasyOCR, │  │    integração       │  │    de layout        │
│    OpenRouter,      │  │  • Documento        │  │  • Classificação    │
│    DeepSeek, TrOCR) │  │    status           │  │    de conteúdo      │
│  • Classificação    │  │  • Webhooks         │  │  • Mapeamento       │
│    básica           │  │    de status        │  │    para schema      │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
                                    ↓
                          ┌─────────────────────┐
                          │  LangExtract        │
                          │  Service (LLM)      │
                          │                     │
                          │  • Extração         │
                          │    semântica        │
                          │  • Validação        │
                          │  • Formatação       │
                          └─────────────────────┘
                                    ↓
                          ┌─────────────────────┐
                          │     Queue (Redis)   │
                          │     (Celery)        │
                          └─────────────────────┘
                                    ↓
                          ┌─────────────────────┐
                          │   PostgreSQL        │
                          │   (Persistência)    │
                          └─────────────────────┘
```

---

## 3. 📦 Definição do Backend COM

### 3.1 Objetivo

O **backend-com** é um microserviço responsável por:

1. **Comunicação com sistemas externos**
   - Superlógica API (envio de dados aprovados)
   - Email API (recepção de documentos)
   - WhatsApp API (recepção de documentos)
   - Scanner corporativo (upload de documentos físicos)

2. **Gerenciamento de integrações**
   - Webhooks
   - Credenciais e tokens
   - Retry automático
   - Logging de comunicações

3. **Gerenciamento de documentos**
   - Upload via interface
   - Associação a lotes (batches)
   - Metadados de origem

### 3.2 Responsabilidades

| Responsabilidade | Detalhes |
|------------------|----------|
| **Superlógica Integration** | Envio de dados aprovados, mapeamento financeiro, controle de idempotência |
| **Email Integration** | Recepção de documentos via email, extração de anexos |
| **WhatsApp Integration** | Recepção de documentos via webhook, compressão de imagens |
| **Scanner Integration** | Upload de documentos digitalizados, associação a lotes |
| **Document Status** | Gerenciamento de estados (RECEIVED, PROCESSING, APPROVED, etc.) |
| **Webhooks** | Gerenciamento de notificações de status |

### 3.3 Contrato de API

```python
# Endpoints do Backend COM

GET  /api/v1/integrations              # Listar integrações disponíveis
GET  /api/v1/integrations/:id          # Detalhes da integração
POST /api/v1/integrations              # Criar integração
PUT  /api/v1/integrations/:id          # Atualizar integração
DELETE /api/v1/integrations/:id        # Remover integração

GET  /api/v1/documents                 # Listar documentos
GET  /api/v1/documents/:id             # Detalhes do documento
POST /api/v1/documents                 # Upload de documento
PUT  /api/v1/documents/:id             # Atualizar metadados
DELETE /api/v1/documents/:id           # Remover documento

GET  /api/v1/batches                   # Listar lotes
GET  /api/v1/batches/:id               # Detalhes do lote
POST /api/v1/batches                   # Criar lote
PUT  /api/v1/batches/:id               # Atualizar lote

POST /api/v1/documents/:id/validate    # Validar documento
POST /api/v1/documents/:id/approve     # Aprovar documento
POST /api/v1/documents/:id/reject      # Rejeitar documento

GET  /api/v1/status                    # Status do sistema
```

### 3.4 Modelo de Dados

```python
# Document Model
{
    "id": "uuid",
    "batch_id": "uuid",
    "filename": "string",
    "file_type": "pdf|image|jpeg|png",
    "file_size": "integer",
    "source": "email|whatsapp|scanner|manual",
    "status": "RECEIVED|PROCESSING|EXTRACTED|PENDING_VALIDATION|APPROVED|REJECTED|SENT_TO_SUPERLOGICA",
    "metadata": {
        "operador": "string",
        "data_scan": "datetime",
        "origem": "string"
    },
    "created_at": "datetime",
    "updated_at": "datetime"
}

# Batch Model
{
    "id": "uuid",
    "name": "string",
    "description": "string",
    "document_count": "integer",
    "status": "PENDING|PROCESSING|COMPLETED|FAILED",
    "documents": ["uuid", "uuid", ...],
    "created_at": "datetime",
    "updated_at": "datetime"
}

# Integration Model
{
    "id": "uuid",
    "name": "string",
    "type": "superlogica|email|whatsapp|scanner",
    "enabled": "boolean",
    "config": {
        "api_key": "string",
        "endpoint": "string",
        "webhook_url": "string"
    },
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

---

## 4. 🔗 Integração entre Microserviços

### 4.1 Fluxo de Comunicação

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Fluxo de Integração                                 │
└─────────────────────────────────────────────────────────────────────────────┘

1. Frontend → Backend Core (Upload de documento)
   POST /api/v1/documents
   {
     "file": "binary",
     "batch_id": "uuid",
     "metadata": {...}
   }

2. Backend Core → Backend OCR (Processamento OCR)
   POST http://backend-ocr:8080/process
   {
     "file": "binary",
     "engine": "openrouter"
   }

3. Backend OCR → Backend Core (Resultado OCR)
   {
     "document_type": "boleto",
     "content_type": "scanned_pdf",
     "raw_text": "...",
     "confidence": 0.95,
     "engine_used": "openrouter"
   }

4. Backend Core → Layout Service (Classificação de layout)
   POST http://layout-service:8000/classify
   {
     "raw_text": "...",
     "document_type": "boleto"
   }

5. Layout Service → Backend Core (Resultado layout)
   {
     "layout": "boleto_caixa",
     "confidence": 0.93
   }

6. Backend Core → LangExtract Service (Extração semântica)
   POST http://langextract-service:8000/extract
   {
     "raw_text": "...",
     "document_type": "boleto",
     "layout": "boleto_caixa",
     "schema_version": "v2"
   }

7. LangExtract Service → Backend Core (Dados estruturados)
   {
     "valor": 123.45,
     "vencimento": "2026-05-01",
     "linha_digitavel": "...",
     "cpf_cnpj": "..."
   }

8. Backend Core → Backend COM (Validação e aprovação)
   POST http://backend-com:8000/api/v1/documents/:id/validate
   {
     "data": {...},
     "validated_by": "user_id",
     "validated_at": "datetime"
   }

9. Backend Core → Backend COM (Aprovação)
   POST http://backend-com:8000/api/v1/documents/:id/approve
   {
     "approved_by": "user_id",
     "approved_at": "datetime"
   }

10. Backend COM → Superlógica API (Envio de dados)
    POST https://api.superlogica.com/v1/financeiro
    {
      "valor": 123.45,
      "vencimento": "2026-05-01",
      "cpf_cnpj": "...",
      "tipo": "boleto"
    }

11. Superlógica API → Backend COM (Confirmação)
    {
      "id": "123456",
      "status": "success"
    }

12. Backend COM → Backend Core (Atualização de status)
    PUT http://backend-core:8000/api/v1/documents/:id
    {
      "status": "SENT_TO_SUPERLOGICA",
      "superlogica_id": "123456"
    }
```

### 4.2 Contratos de API entre Microserviços

#### Backend Core ↔ Backend OCR

```python
# Backend Core → Backend OCR
POST /process
Request:
{
  "file": "binary",
  "engine": "openrouter"  # opcional
}

Response:
{
  "document_type": "boleto",
  "content_type": "scanned_pdf",
  "raw_text": "...",
  "confidence": 0.95,
  "engine_used": "openrouter",
  "pages": [...]
}

# Backend Core → Backend OCR
GET /engines
Response:
{
  "engines": [
    {"name": "openrouter", "description": "OpenRouter LLM"},
    {"name": "tesseract", "description": "Tesseract OCR"},
    ...
  ]
}
```

#### Backend Core ↔ Layout Service

```python
# Backend Core → Layout Service
POST /classify
Request:
{
  "raw_text": "...",
  "document_type": "boleto"
}

Response:
{
  "layout": "boleto_caixa",
  "confidence": 0.93,
  "schema_version": "v2"
}
```

#### Backend Core ↔ LangExtract Service

```python
# Backend Core → LangExtract Service
POST /extract
Request:
{
  "raw_text": "...",
  "document_type": "boleto",
  "layout": "boleto_caixa",
  "schema_version": "v2"
}

Response:
{
  "valor": 123.45,
  "vencimento": "2026-05-01",
  "linha_digitavel": "...",
  "cpf_cnpj": "...",
  "validado": true
}
```

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
```

---

## 5. 🖥️ Interface Gráfica (Frontend)

### 5.1 Telas e Funcionalidades

#### Tela 1: Dashboard

```python
# Componente: Dashboard
- Visão geral do sistema
- Total de documentos recebidos
- Documentos pendentes de validação
- Documentos aprovados hoje
- Últimos documentos processados
- Ações rápidas:
  • Upload de documento
  • Ver lotes
  • Configurações
```

#### Tela 2: Inbox de Documentos

```python
# Componente: DocumentList
- Lista de documentos
- Filtros:
  • Status (RECEIVED, PROCESSING, APPROVED, etc.)
  • Data de recebimento
  • Fonte (email, whatsapp, scanner)
- Ordenação:
  • Data (mais recentes primeiro)
  • Status
- Ações:
  • Visualizar documento
  • Editar metadados
  • Aprovar/Rejeitar
```

#### Tela 3: Detalhe do Documento

```python
# Componente: DocumentDetail
- Split view:
  • Esquerda: Visualização do documento (PDF/Image viewer)
  • Direita: Dados extraídos (JSON editor)
- Abas:
  • Visualização
  • Dados extraídos
  • Histórico
  • Metadados
- Ações:
  • Editar campos
  • Aprovar
  • Rejeitar
  • Enviar para validação
```

#### Tela 4: Validação de Dados

```python
# Componente: ValidationForm
- Formulário para correção de dados
- Validação em tempo real
- Sugestões de correção
- Botões:
  • Corrigir e aprovar
  • Rejeitar
  • Enviar para revisão
```

#### Tela 5: Configurações

```python
# Componente: Settings
- Gerenciamento de integrações
- Configuração de schemas
- Configuração de layouts
- Gerenciamento de usuários
- Logs do sistema
```

### 5.2 Comunicação com Backend Core

```python
# Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_CORE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

# Endpoints
api.get('/api/v1/documents')
api.post('/api/v1/documents', formData)
api.put('/api/v1/documents/:id', data)
api.post('/api/v1/documents/:id/approve')
api.post('/api/v1/documents/:id/reject')
api.get('/api/v1/batches')
api.post('/api/v1/batches', data)
api.get('/api/v1/integrations')
```

---

## 6. 📁 Estrutura de Diretórios Proposta

### 6.1 Backend COM

```
backend-com/
├── api/
│   ├── app.py                    # FastAPI setup
│   ├── routes/
│   │   ├── documents.py          # Endpoints de documentos
│   │   ├── batches.py            # Endpoints de lotes
│   │   ├── integrations.py       # Endpoints de integrações
│   │   └── status.py             # Status do sistema
│   └── schemas/
│       ├── document.py           # Pydantic models
│       ├── batch.py
│       └── integration.py
├── application/
│   └── services/
│       ├── superlogica.py        # Integração Superlógica
│       ├── email.py              # Integração email
│       ├── whatsapp.py           # Integração whatsapp
│       └── scanner.py            # Integração scanner
├── domain/
│   ├── models.py                 # Models Django
│   ├── validators.py             # Validações
│   └── services.py               # Lógica de negócio
├── infrastructure/
│   ├── queue/                    # Celery tasks
│   └── repositories/             # Repositórios
├── shared/
│   └── utils.py                  # Utilitários
├── tests/
│   └── test_*.py
├── requirements.txt
├── Dockerfile
└── README.md
```

### 6.2 Backend Core (Atualizado)

```
backend-core/
├── core/
│   ├── settings.py               # Configurações
│   ├── urls.py                   # URLs principais
│   └── asgi.py / wsgi.py
├── documents/
│   ├── models.py                 # Models Django
│   ├── views.py                  # Views Django
│   ├── urls.py                   # URLs
│   ├── services/
│   │   ├── ocr_client.py         # Cliente OCR
│   │   ├── layout_client.py      # Cliente Layout Service
│   │   ├── langextract_client.py # Cliente LangExtract
│   │   └── com_client.py         # Cliente Backend COM
│   └── tasks.py                  # Celery tasks
├── integrations/
│   ├── models.py                 # Models de integrações
│   ├── services/
│   │   ├── superlogica.py        # Integração Superlógica
│   │   ├── email.py              # Integração email
│   │   └── whatsapp.py           # Integração whatsapp
│   └── tasks.py                  # Tasks de integração
├── queue/
│   └── celery.py                 # Configuração Celery
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 7. 🚀 Próximos Passos

### 7.1 Prioridade Alta

1. **Documentar backend-com**
   - Especificar contratos de API
   - Definir modelos de dados
   - Criar diagramas de arquitetura

2. **Atualizar specs**
   - Atualizar `ingest_docs_prd.md` com backend-com
   - Atualizar diagramas de arquitetura
   - Especificar fluxos de integração

3. **Implementar backend-com**
   - Criar estrutura de diretórios
   - Implementar endpoints principais
   - Integrar com Superlógica API

4. **Implementar integrações**
   - Email API
   - WhatsApp API
   - Scanner integration

### 7.2 Prioridade Média

5. **Layout Classification Service**
   - Especificar contratos
   - Implementar classificação
   - Treinar modelo ML (se necessário)

6. **LangExtract Service**
   - Especificar contratos
   - Implementar extração semântica
   - Integrar com LLM

7. **Frontend**
   - Implementar telas principais
   - Integrar com backend-core
   - Testar fluxos completos

### 7.3 Prioridade Baixa

8. **Otimizações**
   - Cache de resultados
   - Paralelização de processamento
   - Otimização de performance

9. **Monitoramento**
   - Logs centralizados
   - Métricas de performance
   - Alertas e notificações

10. **Documentação**
    - API documentation (OpenAPI/Swagger)
    - Guia de contribuição
    - Guia de deploy

---

## 8. 📚 Referências

- [Architecture PRD](./architecture_prd.md)
- [Ingestion Docs PRD](./ingest_docs_prd.md)
- [Use Cases](./use_cases.md)
- [Backend OCR README](../docuparse-project/backend-ocr/README.md)
- [Backend Core README](../docuparse-project/backend-core/README.md)

---

## 9. 📝 Histórico de Versões

| Versão | Data | Autor | Descrição |
|--------|------|-------|-----------|
| 1.0 | 2026-04-30 | AI Assistant | Análise inicial e recomendações |

---

## 10. ⚙️ Configuração e Observabilidade (NOVO)

### 10.1 Configuração Multi-Tenant

O sistema deve suportar múltiplos inquilinos (tenants) com configurações isoladas:

| Configuração | Descrição | Armazenamento |
|--------------|-----------|---------------|
| **Emails de atendimento** | Endereços de email para recepção de documentos | PostgreSQL (tenant_email) |
| **Números de WhatsApp** | Números de telefone para webhook do WhatsApp | PostgreSQL (tenant_whatsapp) |
| **API Keys** | Chaves de API para Superlógica, OpenRouter, etc. | PostgreSQL (tenant_api_keys) |
| **Webhooks** | URLs de callback para notificações | PostgreSQL (tenant_webhooks) |
| **Schemas de extração** | Modelos de extração por documento/layout | PostgreSQL (tenant_schemas) |
| **Layouts** | Definições de layout por tenant | PostgreSQL (tenant_layouts) |

#### Interface Gráfica de Configuração

A interface gráfica deve fornecer telas para:

* **Configuração de Emails**: Lista de emails, adicionar/editar/excluir, testar conexão
* **Configuração de WhatsApp**: Lista de números, adicionar/editar/excluir, testar conexão
* **Configuração de APIs**: Lista de APIs, adicionar/editar/excluir, testar conexão
* **Gerenciamento de Tenants**: Lista de tenants, adicionar/editar/excluir

### 10.2 Observabilidade (OpenTelemetry)

**Recomendação: OpenTelemetry** para observabilidade completa do sistema:

#### Benefícios

* **Traces**: Rastreamento completo de requisições através dos microserviços
* **Metrics**: Métricas de performance, throughput, erros
* **Logs**: Logs estruturados com correlação automática

#### Componentes Recomendados

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

#### Métricas Recomendadas

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

### 10.3 Segurança

#### Armazenamento de Credenciais

* **Não armazenar em código**: Usar variáveis de ambiente ou secrets manager
* **Criptografia em repouso**: Credenciais criptografadas no banco de dados
* **Rotação automática**: Implementar rotação periódica de credenciais
* **Acesso baseado em papel**: Apenas administradores podem visualizar credenciais

---

## 11. 📝 Histórico de Versões

| Versão | Data | Autor | Descrição |
|--------|------|-------|-----------|
| 1.0 | 2026-04-30 | AI Assistant | Análise inicial e recomendações |
| 1.1 | 2026-04-30 | AI Assistant | Adicionado seção de Configuração e Observabilidade |
