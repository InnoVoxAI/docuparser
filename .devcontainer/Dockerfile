FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    htop \
    jq \
    zsh \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*


# Garante que vscode existe com UID 1000 (padrão da imagem base)
# Se o seu usuário no host tiver UID diferente, ajuste aqui:
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

RUN if ! id -u ${USERNAME} > /dev/null 2>&1; then \
      groupadd --gid ${USER_GID} ${USERNAME} && \
      useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}; \
    fi

RUN echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER ${USERNAME}