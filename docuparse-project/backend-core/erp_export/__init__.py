"""Escrita no ERP (Superlógica): lançar a despesa de um documento aprovado.

Este pacote é separado de `erp_import`, que só lê. O cliente de leitura continua
recusando qualquer método diferente de GET; a escrita passa só pelo
`SuperlogicaWriter`, que tem lista fechada de endpoints e obedece a `policy.py`.

Nada aqui envia ao ERP sem que a política de segurança permita (modo, dry-run,
host autorizado, habilitação por tenant e contrato verificado). Ver `policy.py`.
"""
