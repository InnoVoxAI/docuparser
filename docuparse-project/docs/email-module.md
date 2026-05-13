# Módulo de Email — Documentação

## O que é e para que serve

O DocuParser suporta dois modos de entrada de documentos:

| Modo | Como funciona |
|------|---------------|
| **Tradicional** | O usuário acessa o front-end, faz upload de um arquivo PDF/imagem e acompanha o processamento OCR manualmente |
| **Via email** | Uma caixa de entrada dedicada é monitorada automaticamente. Quando um email com anexo válido chega, o sistema extrai o arquivo e o injeta no pipeline OCR sem intervenção humana |

A aba **Email** na tela de configurações serve exclusivamente para configurar o segundo modo. Ela não processa documentos diretamente — ela define _como_ o `backend-com` (serviço de comunicação) deve se conectar à caixa de entrada e quais anexos deve aceitar.

---

## Fluxo completo

```
Remetente envia email
        │
        ▼
  Caixa de entrada monitorada (IMAP)
        │
        ▼
  backend-com: IMAP poll (periódico ou manual)
        │
        ├── Bloquear remetente? → descartar
        ├── Content-type inválido? → descartar
        └── Tamanho acima do limite? → descartar
        │
        ▼
  Anexo aceito → ingest_document(channel="email")
        │
        ▼
  Evento DocumentReceivedEvent publicado no event bus
        │
        ▼
  Pipeline OCR normal (mesmo fluxo do upload manual)
        │
        ▼
  Documento disponível na lista de documentos do front-end
```

O documento gerado pelo email é idêntico a um documento enviado manualmente, com uma diferença: o campo `channel` fica marcado como `"email"` em vez de `"manual"`.

---

## Campos da tela e o que cada um significa

### Seção: Conta de captura

| Campo | Descrição | Valor padrão |
|-------|-----------|--------------|
| **Provider** | Protocolo de recebimento. `IMAP` = conexão direta com caixa de email. `Webhook` = recebe documentos via HTTP POST de serviços externos (SendGrid, Mailgun etc). `Teste manual` = modo de desenvolvimento sem conexão real | `IMAP` |
| **Ativo** | Liga/desliga a captura. Se `Inativo`, o `backend-com` ignora qualquer tentativa de polling para este tenant | `Ativo` |
| **Pasta monitorada** | Pasta IMAP a ser monitorada. `INBOX` cobre a maioria dos casos. Pode ser alterada para subpastas como `documentos/notas` | `INBOX` |
| **Host IMAP** | Endereço do servidor IMAP. Exemplos: `imap.gmail.com`, `outlook.office365.com`, `imap.empresa.com` | vazio |
| **Porta** | Porta TCP do servidor IMAP. `993` = IMAPS (TLS obrigatório, padrão). `143` = IMAP sem TLS | `993` |
| **Usuário** | Endereço de email da conta de captura. Ex: `documentos@empresa.com` | vazio |
| **Senha/app password** | **Não persiste no banco de dados**. O campo no front-end é apenas visual (desabilitado). A senha real deve ser configurada na variável de ambiente `DOCUPARSE_IMAP_PASSWORD` no servidor onde o `backend-com` roda | — |
| **Webhook URL** | Endpoint do `backend-com` para onde serviços externos (Mailgun, SendGrid etc) devem fazer POST ao receber emails. Só é usado quando o Provider é `Webhook`. Padrão aponta para o `backend-com` local | `http://127.0.0.1:8070/api/v1/email/messages` |

### Seção: Regras de anexos

Estas regras são aplicadas pelo `backend-com` antes de injetar o documento no pipeline. Anexos que não passam nos filtros são descartados silenciosamente.

| Campo | Descrição | Valor padrão |
|-------|-----------|--------------|
| **Tipos aceitos** | Lista de MIME types aceitos, separados por vírgula. Arquivos com tipo diferente são ignorados | `application/pdf, image/jpeg, image/png, image/tiff, image/webp` |
| **Tamanho máximo MB** | Limite de tamanho por anexo em megabytes. Anexos acima desse limite são descartados | `20` |
| **Remetentes bloqueados** | Lista de endereços de email bloqueados, um por linha. Emails desses remetentes são ignorados completamente (nenhum anexo é processado) | vazio |

---

## Persistência de dados

**Sim, há persistência real no banco de dados do `backend-core`.**

A tabela `EmailSettings` (Django model) armazena todos os campos acima, com exceção da senha:

```python
# backend-core/documents/models.py
class EmailSettings(TimeStampedModel):
    tenant          = OneToOneField(Tenant, ...)   # um registro por tenant
    provider        = CharField(...)                # imap | webhook | manual_test
    inbox_folder    = CharField(...)
    imap_host       = CharField(...)
    imap_port       = PositiveIntegerField(...)
    username        = CharField(...)
    webhook_url     = CharField(...)
    accepted_content_types = CharField(...)
    max_attachment_mb      = PositiveIntegerField(...)
    blocked_senders        = TextField(...)
    is_active       = BooleanField(...)
    # senha: ausente — não armazenada
```

O front-end usa dois endpoints do `backend-core`:

| Operação | Endpoint | Quando ocorre |
|----------|----------|---------------|
| Carregamento inicial | `GET /settings/email?tenant=<slug>` | Ao abrir a aplicação (`useEffect` no mount) |
| Salvar configuração | `PATCH /settings/email` | Ao clicar em "Salvar email" |

---

## O botão "Testar captura IMAP"

Este botão aciona manualmente um ciclo de polling no `backend-com`:

1. Salva as configurações atuais (equivale a clicar em "Salvar email")
2. Faz `POST /api/v1/email/poll?tenant_id=<slug>` no `backend-com`
3. O `backend-com` abre uma conexão IMAP, busca os emails **não lidos** na pasta monitorada, filtra os anexos pelas regras configuradas e injeta os válidos no pipeline
4. O front-end exibe quantos documentos foram importados: `"Captura IMAP executada: N documento(s) importado(s)."`

Em produção, este polling deve ser chamado periodicamente por um agendador externo (cron, Celery beat, etc.). O botão na tela serve para testar a configuração sem esperar o ciclo automático.

---

## Relação entre os serviços

```
frontend
  │  GET/PATCH /settings/email
  └──────────────────────────────▶ backend-core (Django)
                                        │ salva em banco de dados
                                        │
  │  POST /api/v1/email/poll            │ GET /settings/email
  └──────────────────────────────▶ backend-com (FastAPI)
                                        │ lê configurações do backend-core
                                        │ conecta ao servidor IMAP
                                        │ processa anexos
                                        │
                                        └──▶ pipeline OCR (mesmo fluxo manual)
```

O `backend-com` não armazena configurações localmente — ele sempre consulta o `backend-core` antes de cada ciclo de polling via `GET /settings/email`.

---

## A senha não persiste — por quê?

Por segurança, credenciais de acesso a email não são armazenadas no banco de dados. A senha deve ser definida como variável de ambiente no servidor onde o `backend-com` é executado:

```bash
DOCUPARSE_IMAP_PASSWORD=sua_app_password_aqui
```

No Gmail/Google Workspace, recomenda-se usar uma **App Password** (senha de aplicativo) em vez da senha principal da conta, especialmente se a autenticação em dois fatores estiver ativada.

---

## Resumo rápido

- **A tela de email não é mockada** — todos os campos são persistidos no banco e todos os botões fazem chamadas reais à API
- **A senha é a única exceção** — está fora do banco e deve ser configurada via env var no servidor
- **O pipeline de processamento é idêntico** ao do upload manual — email é apenas um canal de entrada diferente
- **O botão "Testar captura IMAP"** é a forma de acionar manualmente o ciclo que em produção seria chamado por um agendador
- **As regras de anexos** (tipo, tamanho, remetentes bloqueados) são a primeira linha de filtragem antes do OCR
