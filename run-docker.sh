#!/bin/bash

# DocuParse - Docker Execution Script
# This script orchestrates the startup of the entire DocuParse project using Docker.

# Text colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}          DocuParse - Docker Runner           ${NC}"
echo -e "${BLUE}===============================================${NC}"

# 1. Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# 2. Check for .env file
# The docker-compose.yml explicitly requires a .env file.
if [ ! -f "docuparse-project/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found in docuparse-project/.${NC}"
    echo -e "${BLUE}Creating a default .env file to ensure containers can start...${NC}"
    touch docuparse-project/.env
    echo "# Default .env for DocuParse" > docuparse-project/.env
    echo "DEBUG=True" >> docuparse-project/.env
fi

# 3. Choose docker command (prefer 'docker compose' over 'docker-compose')
DOCKER_CMD="docker compose"
if ! $DOCKER_CMD version >/dev/null 2>&1; then
    DOCKER_CMD="docker-compose"
fi

echo -e "${GREEN}Starting services with $DOCKER_CMD...${NC}"

# 4. Run the project
# We use -f to point to the compose file and cd to ensure relative paths work.
cd docuparse-project && $DOCKER_CMD up --build

# Handle script exit
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Services stopped successfully.${NC}"
else
    echo -e "${RED}An error occurred while running Docker Compose.${NC}"
    exit 1
fi
