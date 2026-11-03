-- 004_views_analiticas.sql
-- Views de apoio usadas pelas análises, pelo teste de hipótese e pelo painel.
--
-- Janela de análise de 01/2017 a 08/2018. Os meses antes e depois disso têm
-- poucos pedidos (início da operação e corte da extração) e distorcem tendência.

CREATE OR REPLACE VIEW dw.vw_pedidos_entregues AS
SELECT
    f.pedido_id,
    d.data          AS data_compra,
    d.ano_mes,
    c.estado,
    c.regiao,
    f.valor_itens,
    f.valor_frete,
    f.dias_entrega,
    f.dias_prometidos,
    f.dias_atraso,
    f.entregue_no_prazo,
    f.nota_avaliacao,
    f.nota_avaliacao <= 2 AS nota_baixa,
    CASE
        WHEN f.dias_atraso <= -10 THEN '1. 10+ dias adiantado'
        WHEN f.dias_atraso <=   0 THEN '2. até 10 dias adiantado / no dia'
        WHEN f.dias_atraso <=   3 THEN '3. 1 a 3 dias de atraso'
        WHEN f.dias_atraso <=   7 THEN '4. 4 a 7 dias de atraso'
        ELSE                           '5. mais de 7 dias de atraso'
    END AS faixa_atraso
FROM dw.fato_pedidos f
JOIN dw.dim_data    d ON d.data_sk    = f.data_compra_sk
JOIN dw.dim_cliente c ON c.cliente_id = f.cliente_id
WHERE f.status_pedido = 'delivered'
  AND f.dias_atraso IS NOT NULL
  AND d.data BETWEEN DATE '2017-01-01' AND DATE '2018-08-31';

CREATE OR REPLACE VIEW dw.vw_receita_mensal AS
SELECT
    d.ano_mes,
    COUNT(DISTINCT f.pedido_id)  AS pedidos,
    COUNT(DISTINCT f.cliente_id) AS clientes,
    SUM(f.valor_item)            AS receita
FROM dw.fato_itens_pedido f
JOIN dw.dim_data d ON d.data_sk = f.data_compra_sk
WHERE f.status_pedido NOT IN ('canceled', 'unavailable')
  AND d.data BETWEEN DATE '2017-01-01' AND DATE '2018-08-31'
GROUP BY d.ano_mes;
