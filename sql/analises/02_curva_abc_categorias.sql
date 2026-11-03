-- 02_curva_abc_categorias.sql
-- Pergunta   Quais categorias concentram a receita? (curva ABC / Pareto)
-- Regra      A = até 80% da receita acumulada, B = de 80% a 95%, C = o restante.
-- Técnicas   SUM() OVER com ordenação para acumulado, classificação por CASE.

WITH receita_categoria AS (
    SELECT
        p.categoria,
        SUM(f.valor_item)           AS receita,
        COUNT(*)                    AS itens_vendidos
    FROM dw.fato_itens_pedido f
    JOIN dw.dim_produto p ON p.produto_id = f.produto_id
    JOIN dw.dim_data    d ON d.data_sk    = f.data_compra_sk
    WHERE f.status_pedido NOT IN ('canceled', 'unavailable')
      AND d.data BETWEEN DATE '2017-01-01' AND DATE '2018-08-31'
    GROUP BY p.categoria
),
acumulado AS (
    SELECT
        *,
        receita / SUM(receita) OVER ()                                   AS participacao,
        SUM(receita) OVER (ORDER BY receita DESC
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            / SUM(receita) OVER ()                                       AS participacao_acumulada,
        ROW_NUMBER() OVER (ORDER BY receita DESC)                         AS ranking
    FROM receita_categoria
)
SELECT
    ranking,
    categoria,
    ROUND(receita, 0)                          AS receita,
    itens_vendidos,
    ROUND(100 * participacao, 1)               AS participacao_pct,
    ROUND(100 * participacao_acumulada, 1)     AS acumulado_pct,
    -- a categoria que cruza a linha dos 80% ainda entra na classe A
    CASE
        WHEN participacao_acumulada - participacao < 0.80 THEN 'A'
        WHEN participacao_acumulada - participacao < 0.95 THEN 'B'
        ELSE 'C'
    END AS classe_abc
FROM acumulado
ORDER BY ranking;
