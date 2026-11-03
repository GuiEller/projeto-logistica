-- 01_kpis_mensais.sql
-- Pergunta   Como receita, pedidos e ticket médio evoluíram mês a mês?
-- Técnicas   CTE, LAG para crescimento mês contra mês, média móvel de 3 meses.

WITH base AS (
    SELECT
        ano_mes,
        pedidos,
        clientes,
        receita,
        receita / NULLIF(pedidos, 0) AS ticket_medio
    FROM dw.vw_receita_mensal
)
SELECT
    ano_mes,
    pedidos,
    ROUND(receita, 0)                                          AS receita,
    ROUND(ticket_medio, 2)                                     AS ticket_medio,
    -- crescimento contra o mês anterior, em %
    ROUND(100.0 * (receita / LAG(receita) OVER w - 1), 1)       AS cresc_receita_mm_pct,
    -- média móvel de 3 meses suaviza picos como a Black Friday de nov/2017
    ROUND(AVG(receita) OVER (w ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS receita_mm3
FROM base
WINDOW w AS (ORDER BY ano_mes)
ORDER BY ano_mes;
