#!/bin/bash

set -e

echo "Installing Python tools..."

pip install --upgrade pip

pip install \
    uv \
    ruff \
    black \
    pytest \
    ipython

echo "Installing Node tools..."

npm install -g \
    pnpm \
    typescript \
    ts-node \
    @anthropic-ai/claude-code \
    task-master-ai

echo "Installing MCP tool servers (basic-memory)..."

export UV_PYTHON_PREFERENCE=only-managed
uv python install 3.12
uv tool install --python 3.12 basic-memory

echo "Installing pre-commit (required by .git/hooks/pre-commit)..."
uv tool install pre-commit

echo "Ensuring basic-memory 'docuparser' project points to /docuparser/memories..."
mkdir -p /docuparser/memories

# Toca o CLI primeiro com um comando somente-leitura. Isso dispara o
# bootstrap de primeira execução (criação do config.json e do projeto
# padrão 'main') sem dar erro em rebuilds onde esse bootstrap já rodou.
basic-memory project list >/dev/null 2>&1 || true

if basic-memory project list 2>/dev/null | grep -qw docuparser; then
    echo "basic-memory project 'docuparser' already exists, skipping."
else
    basic-memory project add docuparser /docuparser/memories
fi

echo "Registering MCP servers in Claude Code (project scope)..."

register_mcp() {
    local name="$1"
    shift
    if claude mcp get "$name" >/dev/null 2>&1; then
        echo "MCP server '$name' already registered, skipping."
    else
        claude mcp add "$name" --scope project -- "$@"
    fi
}

register_mcp basic-memory basic-memory mcp

if claude mcp get task-master >/dev/null 2>&1; then
    echo "MCP server 'task-master' already registered, skipping."
else
    claude mcp add-json task-master '{"command":"npx","args":["-y","task-master-ai"],"env":{"MODEL":"claude-code"}}' --scope project
fi

echo "Done."