#!/usr/bin/env bash
# Exporta a visão de pedidos entregues para CSV, que é a entrada do teste de hipótese.
#   analise/dados/pedidos_entregues.csv
# Roda o psql de dentro do container, então não precisa de Postgres instalado na máquina.
# O \copy ... TO STDOUT manda o resultado para a saída, e o > grava o arquivo do lado de fora.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p analise/dados
docker exec olist-db psql -U postgres -d olist -q -c \
  "\copy (SELECT * FROM dw.vw_pedidos_entregues) TO STDOUT WITH (FORMAT csv, HEADER true)" \
  > analise/dados/pedidos_entregues.csv
echo "ok  analise/dados/pedidos_entregues.csv"
