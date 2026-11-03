-- 03_coortes_retencao.sql
-- Pergunta   Os clientes voltam a comprar? Quantos e em quanto tempo?
-- Técnicas   MIN() OVER para primeira compra, coortes por mês, AGE para distância em meses.
-- Observação Usa cliente_id = customer_unique_id (a pessoa), não o customer_id da Olist,
--            que muda a cada pedido e esconderia toda recompra.

WITH compras AS (
    SELECT DISTINCT
        f.cliente_id,
        DATE_TRUNC('month', d.data)::DATE AS mes_compra
    FROM dw.fato_pedidos f
    JOIN dw.dim_data d ON d.data_sk = f.data_compra_sk
    WHERE f.status_pedido NOT IN ('canceled', 'unavailable')
      AND d.data BETWEEN DATE '2017-01-01' AND DATE '2018-08-31'
),
com_coorte AS (
    SELECT
        cliente_id,
        mes_compra,
        MIN(mes_compra) OVER (PARTITION BY cliente_id) AS coorte
    FROM compras
),
distancia AS (
    SELECT
        coorte,
        cliente_id,
        (EXTRACT(YEAR FROM AGE(mes_compra, coorte)) * 12
         + EXTRACT(MONTH FROM AGE(mes_compra, coorte)))::INT AS meses_depois
    FROM com_coorte
),
matriz AS (
    SELECT
        coorte,
        COUNT(DISTINCT cliente_id) FILTER (WHERE meses_depois = 0)               AS clientes,
        COUNT(DISTINCT cliente_id) FILTER (WHERE meses_depois BETWEEN 1 AND 3)   AS voltaram_ate_3m,
        COUNT(DISTINCT cliente_id) FILTER (WHERE meses_depois BETWEEN 1 AND 6)   AS voltaram_ate_6m,
        COUNT(DISTINCT cliente_id) FILTER (WHERE meses_depois >= 1)              AS voltaram_algum_dia
    FROM distancia
    GROUP BY coorte
)
SELECT
    TO_CHAR(coorte, 'YYYY-MM')                                   AS coorte,
    clientes,
    ROUND(100.0 * voltaram_ate_3m    / clientes, 2)               AS retencao_3m_pct,
    ROUND(100.0 * voltaram_ate_6m    / clientes, 2)               AS retencao_6m_pct,
    ROUND(100.0 * voltaram_algum_dia / clientes, 2)               AS recompra_total_pct
FROM matriz
ORDER BY coorte;

-- Resumo geral (rode separado)
-- Percentual de clientes da janela que fizeram mais de um pedido
-- SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE pedidos > 1) / COUNT(*), 2) AS pct_recompra
-- FROM (SELECT cliente_id, COUNT(*) AS pedidos FROM dw.fato_pedidos
--       WHERE status_pedido NOT IN ('canceled','unavailable') GROUP BY cliente_id) t;
