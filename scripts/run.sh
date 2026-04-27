#!/bin/bash

cd /Users/dirceusilva/Documents/development/src/OCR/liteparse_demo/scripts
source .venv/bin/activate
python ocr_olmocr_pipeline.py \
  --input ../data/input \
  --output-dir ../data/output_json \
  --prompt "Extraia texto e retorne JSON com campos-chave."


# python ocr_olmocr_pipeline.py \
#   --input ../data/input/algum_arquivo.pdf \
#   --output-dir ../data/output_json \
#   --ensure-container
