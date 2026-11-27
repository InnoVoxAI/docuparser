from __future__ import annotations

from contextvars import ContextVar

# Compartilhado entre decorators.py (leitura) e context.py (escrita) — separado
# num módulo próprio pra nenhum dos dois precisar importar o outro.
current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)

# Lista mutável que orchestration_run cria e @task só faz .append() quando o
# resultado é "error" — permite que orchestration_run saiba que uma task falhou
# mesmo quando o código orquestrador não levanta exceção (ex.: só faz
# `if status.status == "error": return`), sem depender de ninguém lembrar de
# sinalizar a falha manualmente.
current_run_errors: ContextVar[list | None] = ContextVar(
    "current_run_errors", default=None
)

# Número da tentativa a gravar no TaskExecution quando quem repete não é o
# tenacity, mas a fila durável (jobqueue): o worker roda a task com
# max_attempts=1 e define aqui o `attempts` do job. None = usa a tentativa do
# tenacity.
current_attempt_override: ContextVar[int | None] = ContextVar(
    "current_attempt_override", default=None
)
