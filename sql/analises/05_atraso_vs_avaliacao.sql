-- 05_atraso_vs_avaliacao.sql
-- Pergunta   O atraso na entrega derruba a nota que o cliente dá?
-- Técnicas   Agregação condicional com FILTER, comparação entre grupos.
-- O teste estatístico formal (Mann-Whitney e qui-quadrado) está em analise/teste_hipotese.py.

SELECT
    faixa_atraso,
    COUNT(*)                                                        AS pedidos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS pct_pedidos,
    ROUND(AVG(nota_avaliacao), 2)                                   AS nota_media,
    ROUND(100.0 * COUNT(*) FILTER (WHERE nota_baixa)
          / NULLIF(COUNT(nota_avaliacao), 0), 1)                    AS pct_nota_1_ou_2,
    ROUND(100.0 * COUNT(*) FILTER (WHERE nota_avaliacao = 5)
          / NULLIF(COUNT(nota_avaliacao), 0), 1)                    AS pct_nota_5
FROM dw.vw_pedidos_entregues
GROUP BY faixa_atraso
ORDER BY faixa_atraso;
