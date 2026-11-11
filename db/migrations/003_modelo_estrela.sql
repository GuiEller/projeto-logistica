-- =====================================================================================
-- 003  MODELO ESTRELA (schema "dw")
-- =====================================================================================
-- O QUE ESTE ARQUIVO FAZ, EM PORTUGUÊS SIMPLES
--   Pega os dados "crus" da staging (a cópia fiel dos CSVs da Olist) e monta tabelas
--   organizadas, prontas para responder perguntas de negócio. Pense numa cozinha:
--   a staging é a feira, com tudo como veio da roça. O "dw" é a bancada, com os
--   ingredientes lavados, cortados e etiquetados.
--
-- PALAVRAS QUE APARECEM AQUI
--   staging   Sala de espera dos dados: o CSV copiado como chegou, sem tratamento.
--   dw        "Data warehouse", o armazém organizado onde as análises acontecem.
--   fato      Tabela de ACONTECIMENTOS. Cada linha é uma coisa que aconteceu
--             (um item vendido, um pedido feito). Tem números para somar.
--   dimensão  Tabela de DESCRIÇÃO. Cada linha descreve quem, o quê ou quando
--             (um cliente, um produto, um dia). Dá contexto aos fatos.
--   grão      O que UMA linha da tabela representa. É a decisão mais importante.
--             Misturar grãos numa mesma conta infla os números sem dar erro nenhum.
--   chave primária (PRIMARY KEY)   Identificador único. O banco proíbe repetir.
--   chave estrangeira (FOREIGN KEY) Ponteiro para outra tabela. O banco proíbe apontar
--                                   para algo que não existe.
--
-- POR QUE "ESTRELA"
--   Dois fatos no centro e quatro dimensões em volta, como pontas de uma estrela:
--
--       fato_itens_pedido  grão = UM ITEM vendido   (receita, produto, vendedor)
--       fato_pedidos       grão = UM PEDIDO         (frete total, atraso, pagamento, nota)
--
--   Se fosse uma tabela só, um pedido com 3 itens repetiria o frete e a nota 3 vezes,
--   e o total do frete e da nota ficaria errado.
--
-- OS NOMES EM INGLÊS DA STAGING (customer_id, order_id...) VÊM DA OLIST.
--   Ao entrar no dw, tudo é traduzido para português (pedido_id, cliente_id...).
-- =====================================================================================


-- O dw é sempre reconstruído do zero a partir da staging. Apagar e recriar é seguro,
-- e deixa o arquivo "repetível": rodar duas vezes dá exatamente o mesmo resultado.
DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;


-- ------------------------------------------------------------------- dim_vendedor
-- DIMENSÃO. Grão: um vendedor por linha.
-- INITCAP deixa só a primeira letra de cada palavra em maiúscula, para "sao paulo"
-- e "SAO PAULO" virarem a mesma cidade, "Sao Paulo".
CREATE TABLE dw.dim_vendedor AS
SELECT
    seller_id            AS vendedor_id,
    INITCAP(seller_city) AS cidade,
    seller_state         AS estado
FROM staging.sellers;

ALTER TABLE dw.dim_vendedor ADD PRIMARY KEY (vendedor_id);


-- -------------------------------------------------------------------- dim_produto
-- DIMENSÃO. Grão: um produto por linha.
--
-- Dois cuidados com os dados:
--   1. 610 produtos vêm SEM categoria (valor nulo). Um nulo desaparece de um GROUP BY
--      sem ninguém perceber. Então trocamos o nulo pelo texto 'sem_categoria', e a
--      receita desses produtos continua contando no total.
--      COALESCE(a, b, c) devolve o primeiro valor que NÃO é nulo.
--   2. Duas categorias não têm tradução para o inglês. Por isso o LEFT JOIN: ele
--      mantém o produto mesmo sem tradução. Com um JOIN comum esses produtos
--      sumiriam da dimensão e os itens vendidos deles ficariam "órfãos".
CREATE TABLE dw.dim_produto AS
SELECT
    produto.product_id                                        AS produto_id,
    COALESCE(produto.product_category_name, 'sem_categoria')  AS categoria,
    COALESCE(traducao.product_category_name_english,
             produto.product_category_name, 'sem_categoria')  AS categoria_en,
    produto.product_photos_qty                                AS qtd_fotos,
    produto.product_weight_g                                  AS peso_g
FROM staging.products AS produto
LEFT JOIN staging.product_category_name_translation AS traducao
       USING (product_category_name);

ALTER TABLE dw.dim_produto ADD PRIMARY KEY (produto_id);


-- -------------------------------------------------------------------- dim_cliente
-- DIMENSÃO. Grão: uma PESSOA por linha.
--
-- A Olist tem dois códigos de cliente, e confundir os dois estraga a análise:
--   customer_id         muda a cada pedido (é o "cadastro daquele pedido").
--   customer_unique_id  é a pessoa de verdade, igual em todos os pedidos dela.
-- Se usássemos customer_id, ninguém jamais "voltaria a comprar" e a recompra daria zero.
--
-- A pessoa pode ter mudado de endereço entre pedidos. Para ficar com UM endereço só:
-- ROW_NUMBER numera os pedidos de cada pessoa do mais novo (1) para o mais antigo
-- (2, 3...), e guardamos só o número 1, o endereço mais recente.
CREATE TABLE dw.dim_cliente AS
WITH ultimo_endereco AS (
    SELECT
        cadastro.customer_unique_id,
        cadastro.customer_city,
        cadastro.customer_state,
        ROW_NUMBER() OVER (
            PARTITION BY cadastro.customer_unique_id        -- uma contagem por pessoa
            ORDER BY pedido.order_purchase_timestamp DESC   -- do pedido mais novo ao mais antigo
        ) AS ordem
    FROM staging.customers AS cadastro
    JOIN staging.orders    AS pedido USING (customer_id)
)
SELECT
    customer_unique_id      AS cliente_id,
    INITCAP(customer_city)  AS cidade,
    customer_state          AS estado,
    -- Agrupa os estados nas 5 regiões do Brasil, para analisar por região.
    CASE
        WHEN customer_state IN ('SP','RJ','MG','ES')                          THEN 'Sudeste'
        WHEN customer_state IN ('PR','SC','RS')                               THEN 'Sul'
        WHEN customer_state IN ('MS','MT','GO','DF')                          THEN 'Centro-Oeste'
        WHEN customer_state IN ('BA','SE','AL','PE','PB','RN','CE','PI','MA') THEN 'Nordeste'
        ELSE 'Norte'
    END AS regiao
FROM ultimo_endereco
WHERE ordem = 1;   -- só o endereço mais recente de cada pessoa

ALTER TABLE dw.dim_cliente ADD PRIMARY KEY (cliente_id);


-- ----------------------------------------------------------------------- dim_data
-- DIMENSÃO. Grão: um DIA por linha, do primeiro ao último pedido, sem pular nenhum.
-- Serve para agrupar por mês, trimestre, dia da semana e fim de semana.
--
-- A chave é um número no formato AAAAMMDD (15/03/2017 vira 20170315): é leve para
-- o JOIN e dá para ler a data só de bater o olho na tabela.
--
-- ATENÇÃO, este detalhe já quebrou o projeto uma vez. O cast "::TIMESTAMP" (data e
-- hora SEM fuso horário) é obrigatório. Com DATE puro o Postgres usa TIMESTAMPTZ
-- (COM fuso), e o horário de verão brasileiro (que existiu de 2016 a 2018) fazia a
-- sequência pular ou repetir um dia, repetindo a chave primária e dando erro.
CREATE TABLE dw.dim_data AS
SELECT
    TO_CHAR(dia, 'YYYYMMDD')::INT        AS data_sk,   -- a chave, ex. 20170315
    dia::DATE                            AS data,
    EXTRACT(YEAR    FROM dia)::INT       AS ano,
    EXTRACT(QUARTER FROM dia)::INT       AS trimestre,
    EXTRACT(MONTH   FROM dia)::INT       AS mes,
    TO_CHAR(dia, 'YYYY-MM')              AS ano_mes,
    (ARRAY['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'])
        [EXTRACT(MONTH FROM dia)::INT]   AS nome_mes,
    EXTRACT(ISODOW FROM dia)::INT        AS dia_semana_num,   -- 1 = segunda ... 7 = domingo
    (ARRAY['segunda','terça','quarta','quinta','sexta','sábado','domingo'])
        [EXTRACT(ISODOW FROM dia)::INT]  AS dia_semana,
    EXTRACT(ISODOW FROM dia) IN (6, 7)   AS fim_de_semana
-- GENERATE_SERIES gera uma linha por dia, do dia do primeiro pedido ao do último.
FROM GENERATE_SERIES(
        (SELECT MIN(order_purchase_timestamp)::DATE FROM staging.orders)::TIMESTAMP,
        (SELECT MAX(order_purchase_timestamp)::DATE FROM staging.orders)::TIMESTAMP,
        INTERVAL '1 day') AS dia;

ALTER TABLE dw.dim_data ADD PRIMARY KEY (data_sk);


-- ------------------------------------------------------------- fato_itens_pedido
-- FATO. Grão: um ITEM vendido por linha. A receita da empresa sai daqui
-- (soma de valor_item).
-- O frete desta tabela é o frete DO ITEM. O frete do pedido inteiro vem da
-- fato_pedidos, nunca daqui, para não contar duas vezes.
CREATE TABLE dw.fato_itens_pedido AS
SELECT
    item.order_id                                              AS pedido_id,
    item.order_item_id                                         AS item_num,    -- 1º, 2º, 3º item do pedido
    TO_CHAR(pedido.order_purchase_timestamp, 'YYYYMMDD')::INT  AS data_compra_sk,
    cadastro.customer_unique_id                                AS cliente_id,  -- a pessoa, não o cadastro
    item.product_id                                            AS produto_id,
    item.seller_id                                             AS vendedor_id,
    pedido.order_status                                        AS status_pedido,
    item.price                                                 AS valor_item,
    item.freight_value                                         AS valor_frete
FROM staging.order_items AS item
JOIN staging.orders      AS pedido   USING (order_id)
JOIN staging.customers   AS cadastro USING (customer_id);

-- Chave composta: o mesmo pedido aparece uma vez por item, então a identidade
-- de uma linha é "pedido + número do item".
ALTER TABLE dw.fato_itens_pedido ADD PRIMARY KEY (pedido_id, item_num);


-- ------------------------------------------------------------------ fato_pedidos
-- FATO. Grão: um PEDIDO por linha. Frete total, atraso, pagamento e nota ficam aqui.
--
-- Regra de ouro: as 3 tabelas auxiliares abaixo (CTEs, "tabelas temporárias de uma
-- consulta só") resumem coisas que têm VÁRIAS linhas por pedido (itens, pagamentos,
-- avaliações) para UMA linha por pedido ANTES do JOIN. Se juntássemos primeiro e
-- somássemos depois, cada pedido se multiplicaria e os valores inflariam.
CREATE TABLE dw.fato_pedidos AS
WITH avaliacao_mais_recente AS (
    -- Alguns pedidos foram avaliados mais de uma vez. DISTINCT ON (order_id) guarda
    -- a PRIMEIRA linha de cada pedido na ordem pedida, que é a resposta mais recente.
    -- NULLS LAST joga respostas sem data para o fim da fila.
    SELECT DISTINCT ON (order_id)
        order_id, review_score
    FROM staging.order_reviews
    ORDER BY order_id, review_answer_timestamp DESC NULLS LAST
),
totais_dos_itens AS (
    -- Quantos itens, quanto valem e quanto custou o frete, por pedido.
    SELECT order_id,
           COUNT(*)           AS qtd_itens,
           SUM(price)         AS valor_itens,
           SUM(freight_value) AS valor_frete
    FROM staging.order_items
    GROUP BY order_id
),
totais_de_pagamento AS (
    -- Um pedido pode ser pago de várias formas (cartão + voucher). Somamos tudo.
    SELECT order_id,
           SUM(payment_value)        AS valor_pago,
           MAX(payment_installments) AS parcelas
    FROM staging.order_payments
    GROUP BY order_id
)
SELECT
    pedido.order_id                                            AS pedido_id,
    TO_CHAR(pedido.order_purchase_timestamp, 'YYYYMMDD')::INT  AS data_compra_sk,
    cadastro.customer_unique_id                                AS cliente_id,
    pedido.order_status                                        AS status_pedido,
    -- Pedido cancelado antes de ter item não aparece em "totais_dos_itens", o que
    -- deixaria o valor nulo. COALESCE troca o nulo por 0 para a conta fechar.
    COALESCE(itens.qtd_itens, 0)                               AS qtd_itens,
    COALESCE(itens.valor_itens, 0)                             AS valor_itens,
    COALESCE(itens.valor_frete, 0)                             AS valor_frete,
    pagamento.valor_pago,
    pagamento.parcelas,
    -- Subtrair duas DATAs dá a diferença em dias inteiros. Se o pedido não foi
    -- entregue, a data de entrega é nula e o resultado também. É isso mesmo que
    -- queremos: pedido não entregue não tem atraso.
    pedido.order_delivered_customer_date::DATE - pedido.order_purchase_timestamp::DATE       AS dias_entrega,
    pedido.order_estimated_delivery_date::DATE - pedido.order_purchase_timestamp::DATE       AS dias_prometidos,
    -- dias_atraso: positivo = chegou DEPOIS do prometido. Negativo = chegou adiantado.
    pedido.order_delivered_customer_date::DATE - pedido.order_estimated_delivery_date::DATE  AS dias_atraso,
    CASE WHEN pedido.order_delivered_customer_date IS NULL THEN NULL
         ELSE pedido.order_delivered_customer_date::DATE
              <= pedido.order_estimated_delivery_date::DATE END    AS entregue_no_prazo,
    avaliacao.review_score                                     AS nota_avaliacao
FROM staging.orders AS pedido
JOIN      staging.customers         AS cadastro  USING (customer_id)
LEFT JOIN totais_dos_itens          AS itens     USING (order_id)
LEFT JOIN totais_de_pagamento       AS pagamento USING (order_id)
LEFT JOIN avaliacao_mais_recente    AS avaliacao USING (order_id);

ALTER TABLE dw.fato_pedidos ADD PRIMARY KEY (pedido_id);


-- ------------------------------------------------------------------ relacionamentos
-- As chaves estrangeiras formam a "estrela" de verdade: o banco recusa um fato que
-- aponte para um cliente, produto, vendedor ou dia que não existe na dimensão.
ALTER TABLE dw.fato_itens_pedido
    ADD FOREIGN KEY (data_compra_sk) REFERENCES dw.dim_data     (data_sk),
    ADD FOREIGN KEY (cliente_id)     REFERENCES dw.dim_cliente  (cliente_id),
    ADD FOREIGN KEY (produto_id)     REFERENCES dw.dim_produto  (produto_id),
    ADD FOREIGN KEY (vendedor_id)    REFERENCES dw.dim_vendedor (vendedor_id);

ALTER TABLE dw.fato_pedidos
    ADD FOREIGN KEY (data_compra_sk) REFERENCES dw.dim_data    (data_sk),
    ADD FOREIGN KEY (cliente_id)     REFERENCES dw.dim_cliente (cliente_id);

-- Índices: como o índice de um livro, ajudam o banco a achar linhas sem ler a
-- tabela inteira. Ficam nas colunas mais usadas em JOIN e filtro das análises.
CREATE INDEX ON dw.fato_itens_pedido (data_compra_sk);
CREATE INDEX ON dw.fato_itens_pedido (produto_id);
CREATE INDEX ON dw.fato_pedidos      (data_compra_sk);
CREATE INDEX ON dw.fato_pedidos      (cliente_id);
