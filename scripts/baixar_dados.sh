#!/usr/bin/env bash
# Baixa os CSVs da Olist para data/raw. Dado bruto não vai para o Git (está no
# .gitignore), então este script é o que deixa qualquer pessoa chegar nos mesmos arquivos.

# Para no primeiro erro. Sem isso, um curl que falha no arquivo 3 passaria
# despercebido e o pipeline rodaria com dado faltando.
set -euo pipefail

URL_BASE="https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets"

# Fica de fora olist_geolocation_dataset.csv (1 milhão de linhas, 61 MB): não ajuda
# a responder a pergunta do projeto e pesa no processamento.
ARQUIVOS=(
  olist_orders_dataset.csv
  olist_order_items_dataset.csv
  olist_order_payments_dataset.csv
  olist_order_reviews_dataset.csv
  olist_customers_dataset.csv
  olist_products_dataset.csv
  olist_sellers_dataset.csv
  product_category_name_translation.csv
)

# -p: não dá erro se a pasta já existe, então o script pode rodar várias vezes.
mkdir -p data/raw

for arq in "${ARQUIVOS[@]}"; do
  echo "baixando $arq"
  # -f: falha em erro HTTP (404). Sem ele, o curl salvaria a página de erro como se fosse o CSV.
  # -L: segue redirecionamentos.
  curl -fL --silent --show-error "$URL_BASE/$arq" -o "data/raw/$arq"
done

echo "Pronto: ${#ARQUIVOS[@]} arquivos em data/raw"
