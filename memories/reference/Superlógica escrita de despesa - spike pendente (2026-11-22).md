---
title: Superlógica escrita de despesa - spike pendente (2026-11-22)
type: note
permalink: docuparser/reference/superlogica-escrita-de-despesa-spike-pendente
tags:
- superlogica
- integracao
- escrita
- spike
---

Ticket 1 do épico "Escrita no Superlógica". **Não foi concluído:** exige uma licença de
teste, e os tokens que o projeto tem hoje são de um ambiente real. Nenhuma chamada de
escrita foi feita. Esta nota separa o que se sabe do que ainda é hipótese, e deixa o roteiro
pronto para quando houver ambiente de teste. Sem dados de cliente, tokens nem payload bruto.

## Verificado

- Padrão `https://api.superlogica.net/v2/condor/CONTROLLER/ACTION`; headers `app_token` e
  `access_token`; corpo JSON ou `application/x-www-form-urlencoded` em alguns casos.
- Data enviada como `MM/DD/AAAA` (documentação oficial). As respostas de leitura usam
  `dd/mm/aaaa`, então o formato de envio e o de resposta são diferentes.
- Os nomes dos parâmetros **diferenciam maiúsculas de minúsculas**.
- O token herda as permissões do usuário que o criou (a escrita pode ser negada por isso).
- Leitura de despesas (`GET despesas`, já usada pela importação): `id_despesa_des`,
  `st_cpfcnpjrecebedor_con` (ou `st_cpf_con`), `apropriacao[].st_conta_cont` e
  `apropriacao[].vl_valor_apro`, `dt_vencimento_pdes`, `dt_despesa_des`, `id_planoconta_plc`.
  A consulta de duplicidade do conector usa só esses campos.
- A documentação pública (Postman) é renderizada por JavaScript e a rota de metadados não
  traz as requisições (sem `item`). Não dá para obter o contrato de escrita por ela; é preciso
  exportar a coleção do Postman ou inspecionar o tráfego da tela do ERP (aba Network).

## Hipótese (não verificado)

Tudo em `erp_export/payload.py`: o caminho `despesas` para o POST, os nomes dos campos do
corpo (`ID_CONDOMINIO_COND`, `ID_FORNECEDOR_FOR`, `APROPRIACAO`, `PARCELAS` etc., derivados
dos nomes de leitura), a leitura de fornecedores (`fornecedores`, parâmetro `pesquisa`, chaves
de id e de CNPJ) e a chave do id da despesa criada. `CONTRACT_VERIFIED` é `False`, o que
bloqueia o modo `live` por código.

## Roteiro do spike (repetível, só em licença de teste)

1. Obter uma licença de teste do Superlógica e criar o App Token nela. Guardar os tokens só
   pela tela de integrações do tenant de teste (cifrados), nunca em arquivo.
2. Configurar o tenant de teste: `superlogica_mode=sandbox`, a URL do ambiente de teste,
   `SUPERLOGICA_SANDBOX_HOSTS` com esse host e `superlogica_dry_run` ligado.
3. Com dry-run ligado, aprovar e confirmar um documento fictício: o conector monta e valida a
   despesa sem enviar. Conferir o resumo na tela.
4. Descobrir o contrato real: exportar a coleção do Postman, ou lançar uma despesa fictícia
   pela tela do ERP de teste e ler o tráfego (Network). Registrar endpoint, método, campos
   obrigatórios, formato do campo de conta, como identificar o fornecedor e como a resposta
   devolve o id da despesa.
5. Corrigir os nomes em `erp_export/payload.py`, desligar o dry-run e repetir com um único
   documento fictício. Conferir a despesa criada no ERP de teste.
6. Verificar: resposta de erro de validação, consulta de despesa existente, limite de taxa,
   anexo do PDF (URL, base64 ou multipart), estorno ou cancelamento e a permissão de escrita
   do token.
7. Só então trocar `CONTRACT_VERIFIED` para `True`, em commit próprio, e atualizar esta nota
   para "verificado" ou "não suportado" em cada item.

## Critérios de aceite do ticket 1

- [ ] Cada item acima verificado ou marcado "não suportado", sem hipótese restante.
- [ ] Payload de exemplo com valores fictícios.
- [x] Nenhuma escrita fora do ambiente de teste (nenhuma escrita foi feita).

## Relations

- relates_to [[docuparser/reference/superlogica-api-condominios-fatos-verificados]]
- relates_to [[docuparser/decisions/escrita-no-superlogica-conector-com-travas]]
