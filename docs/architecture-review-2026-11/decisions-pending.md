# Decisões pendentes (só o usuário decide)

Responda aqui mesmo, editando a linha **Decisão:**, ou registre no basic-memory
(`decisions/`). Cada decisão destrava as tarefas listadas.

---

## D-01 — Fila de jobs durável: qual tecnologia?
- **Opções:** A) fila em Postgres (procrastinate, django-q2 ORM ou tabela própria com SKIP
  LOCKED) · B) Celery + Redis · C) manter o ThreadPool e só endurecer.
- **Recomendação:** A. Detalhes em [target-architecture.md §3](target-architecture.md).
- **Destrava:** AR-30..AR-36 e a decisão sobre o Redis (AR-40).
- **Decisão:** opção A.

## D-02 — Fundir o langextract-service no backend-ocr?
- **Opções:** a) fundir no backend-ocr como `/api/v1/extract` · b) fundir no backend-core
  (chamada direta ao OpenRouter) · c) manter separado.
- **Recomendação:** a. Mantém o core sem chamadas de LLM e concentra rate limit e custo
  num lugar só.
- **Destrava:** AR-50..AR-53.
- **Decisão:** opção A.

## D-03 — Entrega backend-com → core
- **Opções:** a) retry com backoff + reconciliação · b) o com envia os bytes ao core, e o
  core grava no storage e cria o documento numa transação.
- **Recomendação:** a já (paliativo) e b depois.
- **Destrava:** AR-60..AR-62.
- **Decisão:** como recomendação

## D-04 — O que fazer com o publish no barramento (`docuparse_events`)
- **Contexto:** com a fila durável (D-01 = A), o publish no Redis não tem leitor nem
  propósito. O fluxo do ERP usa as mensagens em processo.
- **Opções:** a) remover o publish e o pacote, deixando só a auditoria em `DocumentEvent` ·
  b) manter só o backend `local`/JSONL para auditoria · c) manter como está.
- **Recomendação:** a, depois de D-01.
- **Decisão:** _pendente_

## D-05 — Renomear a permissão `operations.access`?
- **Contexto:** ela continua de propósito (dashboard de processos e retry de etapa), mas o
  nome remete à tela Operações, que foi removida. Renomear exige migração de dados nas
  roles de todos os tenants.
- **Recomendação:** não renomear agora, e documentar o significado. Baixo valor.
- **Decisão:** _pendente_

## D-06 — Segredos versionados no repo de deploy
- **Contexto:** `apps/voicekeeper/.env` e `secrets/k3s-token-novo.txt` estão em texto puro no
  `innovox-kubernetes-deployments`. Não são do DocuParser, mas o token do k3s dá acesso ao
  cluster onde o DocuParser roda.
- **Ação sugerida:** rotacionar o token do k3s e os segredos do voicekeeper, remover os
  arquivos e limpar o histórico (`git filter-repo`), ou ao menos rotacionar. **Só o usuário**
  pode decidir, porque envolve credenciais de produção, e o CLAUDE.md proíbe agentes de
  editar segredos.
- **Decisão:** ignorar, está dentro de repo de referência para deploy, adicionado no gitgnore (usar repo como indica em CLAUDE.md)

## D-07 — Unificação dos classificadores de tipo de documento
- **Contexto:** `backend-ocr/domain/classifier.py` (tipo de arquivo e imagem),
  `backend-core/models/classifier.py` (texto → schema_id) e o catálogo global (018).
  Quem é o dono de "qual é o tipo de documento"?
- **Recomendação:** o core (catálogo + classifier de texto) decide o `schema_id`. O
  classifier do backend-ocr fica restrito a escolher o motor de OCR (PDF nativo, imagem,
  manuscrito). Isso precisa ser confirmado contra o roadmap "Doc Type Identification" do Jira.
- **Decisão:** _pendente_
