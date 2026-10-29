-- Carga da staging: só copia os CSVs para as tabelas, sem transformar nada.
-- Os caminhos são os que o psql enxerga dentro do container, onde data/raw
-- é espelhada em /data/raw pelo Docker Compose.
-- Cada \copy precisa ficar em uma linha só, é comando do psql e não SQL comum.

-- Esvazia antes de carregar, para poder rodar de novo sem duplicar linhas
-- (a staging de avaliações não tem chave primária para barrar repetição).
TRUNCATE staging.orders, staging.order_items, staging.order_payments,
         staging.order_reviews, staging.customers, staging.products,
         staging.sellers, staging.product_category_name_translation;

-- HEADER true pula a primeira linha de cada arquivo (o cabeçalho). CSV trata
-- as aspas, o que importa nas avaliações, que têm quebra de linha dentro do comentário.
\copy staging.orders FROM '/data/raw/olist_orders_dataset.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.order_items FROM '/data/raw/olist_order_items_dataset.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.order_payments FROM '/data/raw/olist_order_payments_dataset.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.order_reviews FROM '/data/raw/olist_order_reviews_dataset.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.customers FROM '/data/raw/olist_customers_dataset.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.products FROM '/data/raw/olist_products_dataset.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.sellers FROM '/data/raw/olist_sellers_dataset.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy staging.product_category_name_translation FROM '/data/raw/product_category_name_translation.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
