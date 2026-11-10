-- 07_nota_por_dia_atraso.sql
-- Pergunta   A partir de que dia de atraso a nota despenca?
-- Técnicas   Agregação por valor exato com FILTER. Guarda contagens e somas, não taxa pronta,
--            para que o painel possa juntar dias em faixas sem fazer média de médias.

SELECT
    dias_atraso,
    COUNT(*)                               AS pedidos,
    COUNT(*) FILTER (WHERE nota_baixa)     AS notas_baixas,
    SUM(nota_avaliacao)                    AS soma_notas
FROM dw.vw_pedidos_entregues
WHERE nota_avaliacao IS NOT NULL           -- sem nota não há o que medir
GROUP BY dias_atraso
ORDER BY dias_atraso;
