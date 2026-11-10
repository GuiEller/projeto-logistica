-- 09_nota_por_regiao_atraso.sql
-- Pergunta   A nota baixa do Nordeste vem da região ou do atraso?
-- Técnicas   Estratificação. Comparar regiões dentro do mesmo grupo (no prazo ou atrasado)
--            separa o efeito do atraso do efeito do lugar.

SELECT
    regiao,
    NOT entregue_no_prazo                  AS atrasado,
    COUNT(*)                               AS pedidos,
    COUNT(*) FILTER (WHERE nota_baixa)     AS notas_baixas,
    SUM(nota_avaliacao)                    AS soma_notas
FROM dw.vw_pedidos_entregues
WHERE nota_avaliacao IS NOT NULL
GROUP BY regiao, atrasado
ORDER BY regiao, atrasado;
