# Guia do Banco de Dados

**Audiência**: Desenvolvedor — sem conhecimento prévio da configuração do banco

---

## Visão Geral

O sistema usa dois mecanismos de armazenamento diferentes dependendo do ambiente:

| Ambiente | Banco de dados | Onde fica |
|----------|----------------|-----------|
| Docker (aplicação rodando) | **PostgreSQL 16** | Container `postgres`, volume Docker `postgres-data` |
| Local (sem Docker) | **SQLite** | Arquivo `backend-core/db.sqlite3` |

> **Importante**: são dois bancos completamente separados. Rodar comandos localmente (sem Docker) lê e escreve no SQLite — isso não afeta em nada o que está rodando no Docker. Para qualquer operação que afete a aplicação real, use `docker compose exec`.

---

## Como o banco é escolhido automaticamente

O arquivo [settings.py](../../../docuparse-project/backend-core/core/settings.py#L77) detecta a variável de ambiente `POSTGRES_HOST`:

```
POSTGRES_HOST definida?
    ├── Sim → PostgreSQL (Docker injeta essa variável automaticamente)
    └── Não → SQLite (ambiente local sem Docker)
```

Você não precisa configurar nada manualmente — o Docker já faz isso via `docker-compose.yml`.

---

## O que é armazenado no banco

O banco possui tabelas organizadas em dois módulos: **documents** (documentos e configurações) e **users** (autenticação e controle de acesso).

### Módulo: documents

#### Tenant (Organização)
Representa a empresa/organização dona dos documentos. Atualmente o sistema opera com um único tenant.

| Campo | O que guarda |
|-------|-------------|
| `slug` | Identificador único (ex: `tenant-demo`) |
| `name` | Nome da organização |
| `is_active` | Se o tenant está ativo |

---

#### Document (Documento)
O registro principal de cada documento que entra no sistema.

| Campo | O que guarda |
|-------|-------------|
| `status` | Estado atual no fluxo de processamento (ver tabela de estados abaixo) |
| `channel` | Como chegou: `upload`, `email`, etc. |
| `file_uri` | Caminho do arquivo no MinIO (armazenamento de arquivos) |
| `raw_text_uri` | Caminho do texto extraído pelo OCR |
| `original_filename` | Nome original do arquivo enviado |
| `content_type` | Tipo MIME (ex: `application/pdf`) |
| `size_bytes` | Tamanho em bytes |
| `sha256` | Hash do arquivo (usado para detectar duplicatas) |
| `document_type` | Classificação do tipo de documento |
| `layout` | Layout identificado (ex: `nfe`, `boleto`) |
| `received_at` | Quando chegou ao sistema |
| `metadata` | JSON livre com dados adicionais |

**Estados possíveis de um documento:**

```
RECEIVED → OCR_COMPLETED → LAYOUT_CLASSIFIED → EXTRACTION_COMPLETED
                                                        ↓
                                              VALIDATION_PENDING
                                              ↙           ↘
                                        APPROVED        REJECTED
                                            ↓
                                  ERP_INTEGRATION_REQUESTED → ERP_SENT
                                                            → ERP_FAILED
```

---

#### DocumentEvent (Histórico de Eventos)
Cada ação relevante no ciclo de vida de um documento gera um evento aqui. Funciona como um log imutável de tudo que aconteceu.

| Campo | O que guarda |
|-------|-------------|
| `event_type` | Tipo do evento (ex: `document.received`, `document.approved`) |
| `source` | Serviço que gerou o evento |
| `occurred_at` | Quando ocorreu |
| `payload` | JSON com os dados do evento |
| `correlation_id` | Liga eventos relacionados ao mesmo fluxo |

---

#### ExtractionResult (Resultado da Extração)
O resultado do processamento do OCR + extração de dados estruturados. Cada documento tem no máximo um registro aqui.

| Campo | O que guarda |
|-------|-------------|
| `schema_id` | Qual esquema de extração foi usado |
| `fields` | JSON com os campos extraídos (ex: `{"numero_nota": "12345", "valor": "R$ 1.200,00"}`) |
| `confidence` | Nível de confiança da extração (0.0 a 1.0) |
| `requires_human_validation` | Se precisa de revisão humana |

---

#### ValidationDecision (Decisão de Validação)
Registra cada aprovação ou rejeição feita por um operador humano.

| Campo | O que guarda |
|-------|-------------|
| `decision` | `approved`, `rejected` ou `corrected` |
| `decided_by` | Usuário que tomou a decisão |
| `corrected_fields` | Campos corrigidos manualmente (JSON) |
| `notes` | Observações do operador |

---

#### ERPIntegrationAttempt (Tentativas de Integração)
Cada tentativa de enviar um documento aprovado para o ERP externo.

| Campo | O que guarda |
|-------|-------------|
| `connector` | Nome do conector ERP usado |
| `status` | `requested`, `sent` ou `failed` |
| `request_payload` | O que foi enviado ao ERP |
| `response_payload` | O que o ERP respondeu |
| `retry_count` | Número de tentativas |

---

#### SchemaConfig (Esquema de Extração)
Define quais campos devem ser extraídos de cada tipo de documento.

| Campo | O que guarda |
|-------|-------------|
| `schema_id` | Identificador do esquema |
| `version` | Versão do esquema |
| `definition` | JSON com a definição dos campos a extrair |
| `is_active` | Se está ativo |

---

#### LayoutConfig (Configuração de Layout)
Mapeia um layout de documento ao seu esquema de extração.

| Campo | O que guarda |
|-------|-------------|
| `layout` | Nome do layout (ex: `nfe`, `boleto`) |
| `document_type` | Tipo do documento |
| `schema_config` | Qual SchemaConfig usar |
| `confidence_threshold` | Confiança mínima para aprovação automática |

---

#### IntegrationSettings, OCRSettings, EmailSettings
Configurações por tenant para os três sistemas externos:
- **IntegrationSettings**: como exportar documentos aprovados (diretório, formato JSON/JSONL, Superlogica)
- **OCRSettings**: qual engine OCR usar (Docling, OpenRouter, Tesseract) para cada tipo de documento
- **EmailSettings**: configuração da caixa de entrada IMAP ou webhook para receber documentos por e-mail

---

### Módulo: users

#### User (Usuário Django)
Tabela nativa do Django (`auth_user`). Armazena as credenciais de acesso.

| Campo | O que guarda |
|-------|-------------|
| `username` | Igual ao e-mail |
| `email` | E-mail de acesso |
| `password` | Senha com hash (bcrypt) |
| `is_active` | Se pode fazer login |
| `first_name` | Nome do usuário |

---

#### UserProfile (Perfil do Usuário)
Extensão do usuário Django com dados específicos do Docuparse.

| Campo | O que guarda |
|-------|-------------|
| `user` | Referência ao User Django |
| `tenant` | A organização a que pertence |
| `role_ref` | A role atual do usuário |

---

#### Role (Papel/Perfil de Acesso)
Define um conjunto nomeado de permissões.

| Campo | O que guarda |
|-------|-------------|
| `name` | Nome da role (ex: `Administrador`, `Operador`) |
| `permissions` | Lista de permissões associadas (relação N:N) |

---

#### Permission (Permissão)
Cada funcionalidade controlável do sistema. Criada pelo comando `seed_permissions` — não podem ser criadas pela interface.

| Código | Descrição |
|--------|-----------|
| `inbox.view` | Ver lista de documentos |
| `documents.send` | Enviar/fazer upload de documentos |
| `documents.validate` | Aprovar ou rejeitar documentos |
| `models.create` | Criar modelos de extração |
| `models.edit` | Editar modelos de extração |
| `operations.access` | Acessar tela de operações |
| `users.manage` | Gerenciar usuários |
| `roles.manage` | Gerenciar roles |

---

#### Tokens JWT (Blacklist)
Tabela gerenciada automaticamente pela biblioteca `djangorestframework-simplejwt`. Armazena tokens invalidados após logout ou rotação.

---

## Arquivos — o que NÃO fica no banco

Arquivos físicos (PDFs, imagens, textos OCR) **não são armazenados no PostgreSQL**. Eles ficam no **MinIO**, que é um serviço de armazenamento de objetos compatível com S3.

| O que | Onde |
|-------|------|
| Arquivos de documentos (PDF, imagem) | MinIO — bucket interno |
| Textos extraídos pelo OCR | MinIO — bucket interno |
| Volume Docker | `minio-data` |
| Console web do MinIO | `http://localhost:9001` |
| Credenciais padrão | usuário: `docuparse` / senha: `docuparse-local` |

O banco guarda apenas o **caminho** (`file_uri`, `raw_text_uri`) que aponta para o arquivo no MinIO.

---

## Como visualizar o banco de dados

### Opção 1 — pgAdmin (interface gráfica, recomendado)

pgAdmin é uma ferramenta visual para PostgreSQL. Como o Docker expõe a porta `5432`, você pode conectar qualquer cliente PostgreSQL ao banco local.

**Instalação do pgAdmin** (não precisa de Docker):
- Acesse [pgadmin.org/download](https://www.pgadmin.org/download/) e instale para o seu sistema

**Configuração da conexão:**

| Campo | Valor |
|-------|-------|
| Host | `localhost` |
| Porta | `5432` |
| Banco de dados | `docuparse` |
| Usuário | `docuparse` |
| Senha | `docuparse` |

> Esses valores vêm do `docker-compose.yml` — são os padrões de desenvolvimento local.

Com a conexão criada, você verá todas as tabelas em:
`Servers → (sua conexão) → Databases → docuparse → Schemas → public → Tables`

---

### Opção 2 — DBeaver (alternativa gratuita multi-banco)

DBeaver suporta PostgreSQL, SQLite e dezenas de outros bancos numa mesma ferramenta.

- Baixe em [dbeaver.io](https://dbeaver.io/download/) (Community Edition é gratuita)
- Configure uma nova conexão PostgreSQL com os mesmos valores da tabela acima

---

### Opção 3 — Terminal (via docker compose exec)

Acesse o banco diretamente pelo terminal, sem instalar nada:

```bash
cd docuparse-project

# Abrir o cliente psql dentro do container
docker compose exec postgres psql -U docuparse -d docuparse
```

Comandos úteis dentro do `psql`:

```sql
-- Listar todas as tabelas
\dt

-- Ver estrutura de uma tabela
\d documents_document

-- Contar documentos por status
SELECT status, count(*) FROM documents_document GROUP BY status;

-- Ver usuários cadastrados
SELECT username, email, is_active FROM auth_user;

-- Listar roles e suas permissões
SELECT r.name, p.code
FROM users_role r
JOIN users_role_permissions rp ON r.id = rp.role_id
JOIN users_permission p ON rp.permission_id = p.id
ORDER BY r.name, p.code;

-- Sair do psql
\q
```

---

### Opção 4 — Django Admin (interface web embutida)

O Django tem uma interface de administração nativa acessível em:

```
http://localhost:8000/admin
```

Para acessar, o usuário precisa ter `is_staff = true` no banco. Ative via terminal:

```bash
cd docuparse-project
docker compose exec backend-core python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(email='admin@docuparse.com')
u.is_staff = True
u.is_superuser = True
u.save()
print('OK')
"
```

Após isso, acesse `http://localhost:8000/admin` com as credenciais de admin e você terá uma interface web para navegar em todas as tabelas.

---

## Diagrama resumido das tabelas

```
auth_user (Django nativo)
    │
    └── documents_userprofile ──→ users_role ──→ users_permission
                    │
                    └──→ documents_tenant
                                │
                                ├── documents_document
                                │       │
                                │       ├── documents_documentevent
                                │       ├── documents_extractionresult
                                │       ├── documents_validationdecision
                                │       └── documents_erpintegrationattempt
                                │
                                ├── documents_schemaconfig
                                │       └── documents_layoutconfig
                                │
                                ├── documents_integrationsettings
                                ├── documents_ocrsettings
                                └── documents_emailsettings
```

---

## Dados persistentes vs. dados voláteis

| Dado | Persiste? | Onde |
|------|-----------|------|
| Documentos e status | Sim | PostgreSQL, volume `postgres-data` |
| Usuários e roles | Sim | PostgreSQL, volume `postgres-data` |
| Arquivos físicos (PDF/imagem) | Sim | MinIO, volume `minio-data` |
| Tokens JWT ativos | Sim (até expirar) | PostgreSQL |
| Filas de eventos | Sim (appendonly) | Redis, volume `redis-data` |

Os volumes Docker persistem os dados mesmo após `docker compose down`. Para apagar tudo e começar do zero:

```bash
cd docuparse-project

# Para os containers e remove os volumes (APAGA TODOS OS DADOS)
docker compose down -v
```

> **Cuidado**: `down -v` é irreversível. Todos os documentos, usuários e configurações serão perdidos.
