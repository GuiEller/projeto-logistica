-- 12_faixa_por_estado.sql
-- Pergunta   Como a nota cai a cada faixa de atraso dentro de um estado só?
-- Técnicas   Agregação por dois níveis (estado e faixa) com FILTER. Guarda contagens e somas,
--            para o painel somar qualquer grupo de estados sem fazer média de médias.

SELECT
    estado,
    faixa_atraso,
    COUNT(*)                               AS pedidos,
    COUNT(*) FILTER (WHERE nota_baixa)     AS notas_baixas,
    SUM(nota_avaliacao)                    AS soma_notas
FROM dw.vw_pedidos_entregues
WHERE nota_avaliacao IS NOT NULL
GROUP BY estado, faixa_atraso
ORDER BY estado, faixa_atraso;
