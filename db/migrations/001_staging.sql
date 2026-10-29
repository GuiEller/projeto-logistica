-- Staging: uma tabela por CSV, com os tipos certos e nenhuma regra de negócio.
-- A carga (002) só copia o arquivo. Toda transformação fica para a etapa seguinte,
-- assim, se um número sair errado, dá para comparar com a staging e achar o culpado.

CREATE SCHEMA IF NOT EXISTS staging;

-- Colunas sem NOT NULL aceitam vazio (NULL). É o caso das datas de aprovação e
-- entrega: pedido cancelado ou ainda a caminho não tem essas datas.
CREATE TABLE staging.orders (
    order_id                       TEXT PRIMARY KEY,
    customer_id                    TEXT,
    order_status                   TEXT,
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);

-- Chave composta: um pedido tem vários itens, então só a dupla identifica a linha.
-- Dinheiro é NUMERIC(10,2) porque FLOAT é aproximado e o total não fecharia ao centavo.
CREATE TABLE staging.order_items (
    order_id             TEXT,
    order_item_id        INTEGER,
    product_id           TEXT,
    seller_id            TEXT,
    shipping_limit_date  TIMESTAMP,
    price                NUMERIC(10,2),
    freight_value        NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

-- Um pedido pode ser pago em mais de uma forma, então a chave é pedido + sequência.
CREATE TABLE staging.order_payments (
    order_id              TEXT,
    payment_sequential    INTEGER,
    payment_type          TEXT,
    payment_installments  INTEGER,
    payment_value         NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

-- Sem chave primária de propósito: o review_id se repete em 789 casos na origem.
-- A staging guarda o dado como veio. Ficar com a avaliação mais recente é regra de
-- negócio e acontece na etapa seguinte.
CREATE TABLE staging.order_reviews (
    review_id                TEXT,
    order_id                 TEXT,
    review_score             INTEGER,
    review_comment_title     TEXT,
    review_comment_message   TEXT,
    review_creation_date     TIMESTAMP,
    review_answer_timestamp  TIMESTAMP
);

-- customer_id muda a cada pedido. A pessoa real é customer_unique_id.
-- CEP é TEXT: é código, não número, e o zero da frente importa.
CREATE TABLE staging.customers (
    customer_id               TEXT PRIMARY KEY,
    customer_unique_id        TEXT,
    customer_zip_code_prefix  TEXT,
    customer_city             TEXT,
    customer_state            TEXT
);

-- Os nomes product_name_lenght e product_description_lenght estão escritos errado
-- na origem. Mantidos assim para a carga bater com o cabeçalho do CSV.
-- Medidas e fotos ficam vazias em alguns produtos, então aceitam NULL.
CREATE TABLE staging.products (
    product_id                  TEXT PRIMARY KEY,
    product_category_name       TEXT,
    product_name_lenght         INTEGER,
    product_description_lenght  INTEGER,
    product_photos_qty          INTEGER,
    product_weight_g            INTEGER,
    product_length_cm           INTEGER,
    product_height_cm           INTEGER,
    product_width_cm            INTEGER
);

CREATE TABLE staging.sellers (
    seller_id               TEXT PRIMARY KEY,
    seller_zip_code_prefix  TEXT,
    seller_city             TEXT,
    seller_state            TEXT
);

CREATE TABLE staging.product_category_name_translation (
    product_category_name          TEXT PRIMARY KEY,
    product_category_name_english  TEXT
);
