"""Produz o texto bruto (.txt) de cada documento baixado pela Fase B (spec 013).

Varre ``downloads/fases/downloads/<categoria>/`` e, para cada documento, chama o
mesmo backend-ocr que a aplicação usa no fluxo principal (documento → texto
bruto) e grava o resultado em ``Raw Text Docs/<categoria>/<nome>.txt``,
replicando a árvore de categorias.

Execução incremental (retoma o que falta), fail-soft (erros vão para um CSV e a
run continua) e com barra de progresso.
"""
