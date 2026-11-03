-- 06_atraso_por_estado.sql
-- Pergunta   Onde o problema de entrega se concentra? Por onde começar a agir?
-- Técnicas   RANK, filtro de amostra mínima com HAVING, prazo prometido vs real.

WITH por_estado AS (
    SELECT
        estado,
        regiao,
        COUNT(*)                                                   AS pedidos,
        AVG(dias_entrega)                                          AS entrega_media,
        AVG(dias_prometidos)                                       AS prazo_prometido_medio,
        AVG((NOT entregue_no_prazo)::INT)                           AS taxa_atraso,
        AVG(nota_avaliacao)                                        AS nota_media
    FROM dw.vw_pedidos_entregues
    GROUP BY estado, regiao
    HAVING COUNT(*) >= 300          -- descarta estados com amostra pequena demais
)
SELECT
    RANK() OVER (ORDER BY taxa_atraso DESC)          AS ranking_atraso,
    estado,
    regiao,
    pedidos,
    ROUND(entrega_media, 1)                          AS entrega_media_dias,
    ROUND(prazo_prometido_medio, 1)                  AS prazo_prometido_dias,
    ROUND(100 * taxa_atraso, 1)                      AS taxa_atraso_pct,
    ROUND(nota_media, 2)                             AS nota_media
FROM por_estado
ORDER BY ranking_atraso;
