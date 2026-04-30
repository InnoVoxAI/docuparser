#! /usr/bin/env bash

echo "Running Atoms pre-start_dev.sh"
# run server
echo "Running server..."
uvicorn atoms.fastapi_app:app --proxy-headers --host 0.0.0.0 --port 8000 --reload
