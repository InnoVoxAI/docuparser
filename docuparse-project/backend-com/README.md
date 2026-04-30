# Atoms

Mini tools for building big things

## Visão Geral

Atoms é um conjunto de ferramentas modulares para construir aplicações robustas e escaláveis, focando em integração com filas, mensageria, automação de processos (Camunda, Zeebe), leitura de e-mails, WhatsApp (Twilio), logging estruturado e APIs FastAPI.

O projeto é altamente tipado (Pydantic), assíncrono e com backends plugáveis para filas (memória, Postgres, Redis/Celery).

---

## Estrutura do Projeto

```
src/atoms/
	camunda_decorator.py      # Decoradores/utilitários para Camunda
	camunda_server.py         # Worker Camunda standalone
	config.py                 # Configuração centralizada (Pydantic)
	debounce/                 # Fila com debounce (Memory, Postgres, Celery)
	email_reader/             # Leitura de e-mails via IMAP
	fastapi_app.py            # App FastAPI principal
	fastapi_decorator.py      # Daemons/background para FastAPI
	logging.py                # Logging estruturado (structlog)
	send_to_webhook.py        # Utilitário para webhooks HTTP
	whatsapp/                 # Integração WhatsApp via Twilio
	zeebe_decorator.py        # Decoradores/utilitários para Zeebe
	zeebe_server.py           # Worker Zeebe standalone
```

---

## Principais Módulos

### 1. DebouncedQueue (debounce/debounced_queue.py)
Fila genérica com debounce, tipagem forte e backends plugáveis:
- **MemoryBackend**: para testes/dev, zero dependências.
- **PostgresBackend**: persistente, seguro para múltiplos workers.
- **CeleryBackend**: push-based, ideal para infraestruturas com Celery/Redis.

**Exemplo de uso:**
```python
queue = DebouncedQueue(
	schema=IncomingMessage,
	key_fn=lambda m: m.conversation_id,
	on_flush=handle_turn,
	backend=PostgresBackend(pool=pg_pool),
	delay=3.0,
	max_wait=30.0,
	on_error=my_error_handler,
)
await queue.start()
await queue.enqueue(IncomingMessage(...))
```

### 2. Email Reader (email_reader/)
Leitura de e-mails via IMAP, com suporte a anexos, HTML, imagens inline e integração com Camunda/Zeebe.

**Exemplo de task Camunda:**
```python
@camunda_task(topic_name="email_reader_fetch_unread")
def camunda_email_fetch_unread(...):
	...
```

### 3. WhatsApp Twilio (whatsapp/twilio/)
Envio de mensagens WhatsApp via Twilio, com autenticação por API Key e suporte a modos de entrega (real/mock).

**Exemplo de uso:**
```python
client = TwilioClient(...)
sid = await client.send_message(to="+5511...", body="Olá!")
```

### 4. FastAPI App (fastapi_app.py)
App FastAPI com rotas para e-mail, WhatsApp, webhooks e suporte a daemons/background tasks via decoradores.

### 5. Logging Estruturado (logging.py)
Configuração de logging com structlog, pronto para produção (JSON) ou desenvolvimento (console).

---

## Instalação

Requer Python >= 3.13

```bash
pip install .[debounce,email-reader,whatsapp-twilio,camunda8]
```

Veja `pyproject.toml` para dependências opcionais.

---

## Exemplos

- **Fila com debounce:** Veja `debounce/example.py`
- **Leitura de e-mails:** Veja `email_reader/service/email_reader.py`
- **API WhatsApp:** Veja `whatsapp/twilio/api/v1/fastapi.py`

---

## Licença

MIT. Veja o arquivo LICENSE.
