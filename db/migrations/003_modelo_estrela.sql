-- Modelo estrela, schema dw. Lê da staging e entrega tabelas prontas para análise.
-- Cada tabela diz o seu grão (o que uma linha representa), porque misturar grãos
-- numa mesma conta infla os números sem dar erro.
--
-- Duas tabelas fato dividem as mesmas dimensões.
--   fato_itens_pedido  grão = um item vendido   (receita, produto, vendedor)
--   fato_pedidos       grão = um pedido         (frete total, atraso, pagamento, nota)
-- Numa fato só, um pedido com 3 itens contaria o frete e a nota 3 vezes.

-- O dw é sempre reconstruído a partir da staging, então apagar e recriar é seguro
-- e deixa o arquivo repetível: rodar duas vezes dá o mesmo resultado.
DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;

-- ---------------------------------------------------------------- dim_vendedor
-- Grão: um vendedor por linha. INITCAP padroniza "sao paulo" para "Sao Paulo".
CREATE TABLE dw.dim_vendedor AS
SELECT
    seller_id            AS vendedor_id,
    INITCAP(seller_city) AS cidade,
    seller_state         AS estado
FROM staging.sellers;

ALTER TABLE dw.dim_vendedor ADD PRIMARY KEY (vendedor_id);

-- ---------------------------------------------------------------- dim_produto
-- Grão: um produto por linha. 610 produtos vêm sem categoria. Nulo some de um
-- GROUP BY sem ninguém perceber, então vira 'sem_categoria' e a receita continua no total.
-- LEFT JOIN na tradução porque duas categorias não têm versão em inglês. Com JOIN
-- comum, esses produtos sumiriam da dimensão e os itens deles ficariam órfãos.
CREATE TABLE dw.dim_produto AS
SELECT
    p.product_id                                        AS produto_id,
    COALESCE(p.product_category_name, 'sem_categoria')  AS categoria,
    COALESCE(t.product_category_name_english,
             p.product_category_name, 'sem_categoria')  AS categoria_en,
    p.product_photos_qty                                AS qtd_fotos,
    p.product_weight_g                                  AS peso_g
FROM staging.products p
LEFT JOIN staging.product_category_name_translation t USING (product_category_name);

ALTER TABLE dw.dim_produto ADD PRIMARY KEY (produto_id);

-- ---------------------------------------------------------------- dim_cliente
-- Grão: uma PESSOA por linha. customer_id muda a cada pedido, então a pessoa real
-- é customer_unique_id. Com customer_id a recompra daria exatamente zero.
-- A pessoa pode ter se mudado. ROW_NUMBER numera os pedidos dela do mais novo
-- para o mais antigo, e ficamos com o endereço do número 1 (o mais recente).
CREATE TABLE dw.dim_cliente AS
WITH ultimo_endereco AS (
    SELECT
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id
                           ORDER BY o.order_purchase_timestamp DESC) AS ordem
    FROM staging.customers c
    JOIN staging.orders    o USING (customer_id)
)
SELECT
    customer_unique_id      AS cliente_id,
    INITCAP(customer_city)  AS cidade,
    customer_state          AS estado,
    CASE
        WHEN customer_state IN ('SP','RJ','MG','ES')                          THEN 'Sudeste'
        WHEN customer_state IN ('PR','SC','RS')                               THEN 'Sul'
        WHEN customer_state IN ('MS','MT','GO','DF')                          THEN 'Centro-Oeste'
        WHEN customer_state IN ('BA','SE','AL','PE','PB','RN','CE','PI','MA') THEN 'Nordeste'
        ELSE 'Norte'
    END AS regiao
FROM ultimo_endereco
WHERE ordem = 1;

ALTER TABLE dw.dim_cliente ADD PRIMARY KEY (cliente_id);

-- ---------------------------------------------------------------- dim_data
-- Grão: um dia por linha, do primeiro ao último pedido, sem buracos.
-- Chave inteira AAAAMMDD (20170315): leve para o JOIN e legível para quem abre a tabela.
-- O cast para TIMESTAMP sem fuso é obrigatório. Com DATE puro o Postgres usa
-- TIMESTAMPTZ, e o horário de verão brasileiro (que existia de 2016 a 2018)
-- faz a série pular ou repetir um dia, quebrando a chave primária.
CREATE TABLE dw.dim_data AS
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INT          AS data_sk,
    d::DATE                              AS data,
    EXTRACT(YEAR    FROM d)::INT         AS ano,
    EXTRACT(QUARTER FROM d)::INT         AS trimestre,
    EXTRACT(MONTH   FROM d)::INT         AS mes,
    TO_CHAR(d, 'YYYY-MM')                AS ano_mes,
    (ARRAY['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'])
        [EXTRACT(MONTH FROM d)::INT]     AS nome_mes,
    EXTRACT(ISODOW FROM d)::INT          AS dia_semana_num,   -- 1 = segunda
    (ARRAY['segunda','terça','quarta','quinta','sexta','sábado','domingo'])
        [EXTRACT(ISODOW FROM d)::INT]    AS dia_semana,
    EXTRACT(ISODOW FROM d) IN (6, 7)     AS fim_de_semana
FROM GENERATE_SERIES(
        (SELECT MIN(order_purchase_timestamp)::DATE FROM staging.orders)::TIMESTAMP,
        (SELECT MAX(order_purchase_timestamp)::DATE FROM staging.orders)::TIMESTAMP,
        INTERVAL '1 day') AS d;

ALTER TABLE dw.dim_data ADD PRIMARY KEY (data_sk);

-- ---------------------------------------------------------------- fato_itens_pedido
-- Grão: um item vendido. É daqui que sai a receita (soma de valor_item).
-- O frete aqui é o do item. Frete do pedido vem da fato_pedidos, nunca daqui.
CREATE TABLE dw.fato_itens_pedido AS
SELECT
    i.order_id                                            AS pedido_id,
    i.order_item_id                                       AS item_num,
    TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::INT  AS data_compra_sk,
    c.customer_unique_id                                  AS cliente_id,
    i.product_id                                          AS produto_id,
    i.seller_id                                           AS vendedor_id,
    o.order_status                                        AS status_pedido,
    i.price                                               AS valor_item,
    i.freight_value                                       AS valor_frete
FROM staging.order_items i
JOIN staging.orders    o USING (order_id)
JOIN staging.customers c USING (customer_id);

ALTER TABLE dw.fato_itens_pedido ADD PRIMARY KEY (pedido_id, item_num);

-- ---------------------------------------------------------------- fato_pedidos
-- Grão: um pedido. Cada CTE abaixo leva uma tabela de outro grão para o grão de
-- pedido ANTES do JOIN. Juntar primeiro e agregar depois multiplicaria linhas.
CREATE TABLE dw.fato_pedidos AS
WITH avaliacao_final AS (
    -- Alguns pedidos têm mais de uma avaliação. DISTINCT ON fica com a primeira
    -- linha de cada order_id na ordem pedida, ou seja, a resposta mais recente.
    SELECT DISTINCT ON (order_id)
        order_id, review_score
    FROM staging.order_reviews
    ORDER BY order_id, review_answer_timestamp DESC NULLS LAST
),
itens AS (
    SELECT order_id,
           COUNT(*)           AS qtd_itens,
           SUM(price)         AS valor_itens,
           SUM(freight_value) AS valor_frete
    FROM staging.order_items
    GROUP BY order_id
),
pagos AS (
    -- Um pedido pode ter várias formas de pagamento (cartão + voucher).
    SELECT order_id,
           SUM(payment_value)        AS valor_pago,
           MAX(payment_installments) AS parcelas
    FROM staging.order_payments
    GROUP BY order_id
)
SELECT
    o.order_id                                                AS pedido_id,
    TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::INT      AS data_compra_sk,
    c.customer_unique_id                                      AS cliente_id,
    o.order_status                                            AS status_pedido,
    -- Pedido cancelado antes de ter item não aparece em "itens". COALESCE troca o nulo por 0.
    COALESCE(i.qtd_itens, 0)                                  AS qtd_itens,
    COALESCE(i.valor_itens, 0)                                AS valor_itens,
    COALESCE(i.valor_frete, 0)                                AS valor_frete,
    pg.valor_pago,
    pg.parcelas,
    -- Diferença entre DATEs dá dias inteiros. Sem entrega, o resultado é nulo, e é
    -- isso que queremos: pedido não entregue não tem atraso.
    o.order_delivered_customer_date::DATE - o.order_purchase_timestamp::DATE       AS dias_entrega,
    o.order_estimated_delivery_date::DATE - o.order_purchase_timestamp::DATE       AS dias_prometidos,
    -- Positivo = chegou depois do prometido. Negativo = adiantado.
    o.order_delivered_customer_date::DATE - o.order_estimated_delivery_date::DATE  AS dias_atraso,
    CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
         ELSE o.order_delivered_customer_date::DATE
              <= o.order_estimated_delivery_date::DATE END    AS entregue_no_prazo,
    a.review_score                                            AS nota_avaliacao
FROM staging.orders o
JOIN staging.customers     c USING (customer_id)
LEFT JOIN itens            i USING (order_id)
LEFT JOIN pagos           pg USING (order_id)
LEFT JOIN avaliacao_final  a USING (order_id);

ALTER TABLE dw.fato_pedidos ADD PRIMARY KEY (pedido_id);

-- ---------------------------------------------------------------- relacionamentos
-- As chaves estrangeiras são a "estrela" de verdade: o banco recusa um fato que
-- aponte para cliente, produto ou dia que não existe na dimensão.
ALTER TABLE dw.fato_itens_pedido
    ADD FOREIGN KEY (data_compra_sk) REFERENCES dw.dim_data     (data_sk),
    ADD FOREIGN KEY (cliente_id)     REFERENCES dw.dim_cliente  (cliente_id),
    ADD FOREIGN KEY (produto_id)     REFERENCES dw.dim_produto  (produto_id),
    ADD FOREIGN KEY (vendedor_id)    REFERENCES dw.dim_vendedor (vendedor_id);

ALTER TABLE dw.fato_pedidos
    ADD FOREIGN KEY (data_compra_sk) REFERENCES dw.dim_data    (data_sk),
    ADD FOREIGN KEY (cliente_id)     REFERENCES dw.dim_cliente (cliente_id);

-- Índices nas colunas mais usadas em JOIN e filtro das análises.
CREATE INDEX ON dw.fato_itens_pedido (data_compra_sk);
CREATE INDEX ON dw.fato_itens_pedido (produto_id);
CREATE INDEX ON dw.fato_pedidos      (data_compra_sk);
CREATE INDEX ON dw.fato_pedidos      (cliente_id);
