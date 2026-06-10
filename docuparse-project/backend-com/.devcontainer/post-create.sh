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
    ts-node

echo "Done."
