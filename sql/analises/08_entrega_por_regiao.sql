-- 08_entrega_por_regiao.sql
-- Pergunta   A entrega é menos previsível em algumas regiões?
-- Técnicas   Percentil exato com percentile_cont (interpola entre os dois valores vizinhos).
--            A distância entre p10 e p90 mede a imprevisibilidade melhor do que a média,
--            que esconde quem chega muito cedo e quem chega muito tarde.

SELECT
    regiao,
    COUNT(*)                                                       AS pedidos,
    percentile_cont(0.10) WITHIN GROUP (ORDER BY dias_atraso)      AS p10,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY dias_atraso)      AS p25,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY dias_atraso)      AS p50,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY dias_atraso)      AS p75,
    percentile_cont(0.90) WITHIN GROUP (ORDER BY dias_atraso)      AS p90
FROM dw.vw_pedidos_entregues
GROUP BY regiao
ORDER BY regiao;
