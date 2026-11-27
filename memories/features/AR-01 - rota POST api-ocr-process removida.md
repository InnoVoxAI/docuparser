---
title: AR-01 - rota POST /api/ocr/process removida
type: note
permalink: docuparser/features/ar-01-rota-post-api-ocr-process-removida
tags:
- seguranca
- backend-core
- revisao-arquitetura
---

# AR-01 - rota POST /api/ocr/process removida

Branch `fix/ar-01-remove-ocr-process` (commit 3a5ebe85, a partir de `dev` @ 797aea22), 2026-11-27.

- [contexto] `process_document_view` era uma view Django pura, com `@csrf_exempt` e sem autenticação, que recebia um arquivo e chamava `OCRClient().process_document` (OCR pago). #seguranca
- [investigacao] Nenhum cliente usava a rota: nem o frontend, nem o backend-com, nem testes. Só aparecia em `docs/TECHNICAL.md` como "legado".
- [decisao] Remover em vez de autenticar. Também saíram os imports `csrf_exempt` e `require_POST`, que só ela usava.
- [teste] `documents/tests/test_removed_routes.py`: POST sem credencial → 404 e o OCR não é chamado. Falha no código antigo.
- [verificacao] Suíte inteira do backend-core: 569 passed, em cerca de 30 min (é lenta, então para as próximas mudanças vale rodar só os testes específicos).
- [aberto] `GET /api/ocr/engines` (`list_engines_view`) também é view Django pura e sem autenticação. É só leitura e não tem custo, mas fica de candidata a fechar junto com o AR-64.

Relacionado: [[Revisão de arquitetura 2026-11]]
