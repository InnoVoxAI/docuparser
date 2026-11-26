# Revisão de arquitetura — DocuParser (2026-11-26)

Varredura feita no dia em que o pipeline por eventos, o Camunda, as DLQs e o layout-service
foram removidos (PR #66). O objetivo é responder três perguntas: **a arquitetura está boa?**,
**sobra algum componente?** e **falta algum?**. Os arquivos desta pasta também servem para
outro agente continuar o trabalho.

> Nada foi implementado nesta revisão. Por preferência registrada do usuário, nenhuma tarefa
> daqui deve ser implementada até ele pedir explicitamente ("comece a implementação").

## Resposta curta

- **O formato geral está certo.** O backend-core é um monólito modular (Django,
  schema-por-tenant). Em volta dele há adaptadores sem estado: backend-com para entrada,
  backend-ocr e langextract para computação e LLM. Para o tamanho do time e do produto, esse
  é o desenho adequado. A limpeza de hoje removeu justamente o que contrariava esse formato.
- **Os problemas reais estão em três lugares, não no desenho:**
  1. **O processamento não é durável.** É um `ThreadPoolExecutor` em memória: trabalho em
     andamento se perde num restart, os retries cobram o OCR pago de novo e não há
     coordenação entre réplicas.
  2. **A implantação não está endurecida.** Em prod rodam `runserver` e `DEBUG=True`, sem
     probes e sem resource limits, e o CI não executa nenhum teste de backend.
  3. **Há sobras e fronteiras fracas.** O barramento Redis só recebe publicações e ninguém
     lê; o langextract (574 LOC, um único chamador) é um serviço inteiro; existem três
     classificadores; e há endpoints internos sem autenticação.
- **Sobra:** o barramento de eventos como infraestrutura, o langextract como serviço
  separado e várias sobras de código e configuração (lista em [findings.md](findings.md)).
- **Falta:** uma fila de jobs durável, um agendador (sweeper e polls), um servidor WSGI de
  produção, testes de backend no CI, um rate limiter e circuit breaker para o OpenRouter, uma
  entrega durável do backend-com para o core e métricas com alertas.

## Arquivos

| Arquivo | Para quê |
|---|---|
| [findings.md](findings.md) | Achados por área, com evidência (arquivo:linha) e severidade |
| [target-architecture.md](target-architecture.md) | Arquitetura-alvo: o que fica, o que sai, o que se funde, o que entra |
| [roadmap.md](roadmap.md) | Plano em fases, com ordem e dependências |
| [tasks.md](tasks.md) | Backlog acionável (IDs `AR-xx`), com critérios de aceite e arquivos |
| [decisions-pending.md](decisions-pending.md) | Perguntas que **só o usuário** decide, antes das fases 2 e 3 |
| [handoff.md](handoff.md) | Instruções para o próximo agente: contexto, regras e armadilhas |
| [work_in_progress.md](work_in_progress.md) | Estado de cada tarefa (atualizar a cada sessão) |

## Método

Quatro varreduras somente leitura (`code-scout`): backend-core; backend-ocr, langextract e
backend-com; shared, contracts e infra (compose, k8s, CI); e frontend. Os achados de maior
severidade foram conferidos à mão. Uma afirmação do scout estava errada e foi corrigida: o
`process_document_view` é `@require_POST`, não GET. O problema real dele é outro: é aberto,
sem autenticação, e dispara OCR pago.
