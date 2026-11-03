-- 04_rfm_segmentos.sql
-- Pergunta   Como segmentar a base de clientes para ações de CRM?
-- Método     RFM (Recência, Frequência, Valor). Recência e Valor viram notas de 1 a 5
--            por quintil (NTILE). Frequência é tratada por regra, porque mais de 95%
--            dos clientes compram uma vez só e o quintil não teria sentido.
-- Técnicas   NTILE, CTEs encadeadas, CASE para regra de negócio.

WITH data_ref AS (
    -- "hoje" da análise = dia seguinte ao último pedido da janela
    SELECT DATE '2018-09-01' AS hoje
),
por_cliente AS (
    SELECT
        f.cliente_id,
        (SELECT hoje FROM data_ref) - MAX(d.data) AS recencia_dias,
        COUNT(*)                                  AS frequencia,
        SUM(f.valor_itens)                        AS valor
    FROM dw.fato_pedidos f
    JOIN dw.dim_data d ON d.data_sk = f.data_compra_sk
    WHERE f.status_pedido NOT IN ('canceled', 'unavailable')
      AND d.data BETWEEN DATE '2017-01-01' AND DATE '2018-08-31'
    GROUP BY f.cliente_id
),
notas AS (
    SELECT
        *,
        6 - NTILE(5) OVER (ORDER BY recencia_dias)   AS r,   -- comprou há pouco = 5
        NTILE(5) OVER (ORDER BY valor)               AS v    -- gastou mais = 5
    FROM por_cliente
),
segmentos AS (
    SELECT
        *,
        CASE
            WHEN frequencia >= 2 AND r >= 4             THEN 'Fiéis ativos'
            WHEN frequencia >= 2                        THEN 'Fiéis em risco'
            WHEN r >= 4 AND v >= 4                      THEN 'Novos de alto valor'
            WHEN r >= 4                                 THEN 'Novos'
            WHEN r <= 2 AND v >= 4                      THEN 'Alto valor perdidos'
            ELSE                                             'Inativos'
        END AS segmento
    FROM notas
)
SELECT
    segmento,
    COUNT(*)                                             AS clientes,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS pct_clientes,
    ROUND(SUM(valor), 0)                                  AS receita,
    ROUND(100.0 * SUM(valor) / SUM(SUM(valor)) OVER (), 1) AS pct_receita,
    ROUND(AVG(recencia_dias), 0)                          AS recencia_media_dias,
    ROUND(AVG(valor), 2)                                  AS ticket_medio_cliente
FROM segmentos
GROUP BY segmento
ORDER BY receita DESC;
