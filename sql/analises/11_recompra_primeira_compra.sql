-- 11_recompra_primeira_compra.sql
-- Pergunta   Quem teve a primeira compra atrasada volta menos?
-- Técnicas   Window functions numa passada só. ROW_NUMBER acha a primeira compra de cada pessoa
--            e COUNT OVER conta as compras dela, sem juntar a tabela com ela mesma.
--            O desempate por pedido_id garante a mesma escolha toda vez quando duas compras têm o mesmo horário.
--
-- Uma versão anterior juntava uma CTE com ela mesma. No banco recém-criado do CI, sem ANALYZE,
-- o Postgres estimava 200 linhas de cada lado e escolhia um laço aninhado de bilhões de comparações.

WITH vendas AS (
    -- O horário completo da compra está no staging. A fato só guarda a chave do dia.
    SELECT
        f.pedido_id,
        ROW_NUMBER() OVER (PARTITION BY f.cliente_id
                           ORDER BY o.order_purchase_timestamp, f.pedido_id)  AS ordem,
        COUNT(*)     OVER (PARTITION BY f.cliente_id)                         AS vendas
    FROM dw.fato_pedidos f
    JOIN staging.orders o ON o.order_id = f.pedido_id
    WHERE f.status_pedido NOT IN ('canceled', 'unavailable')
)
SELECT
    NOT e.entregue_no_prazo                     AS primeira_atrasada,
    COUNT(*)                                    AS pessoas,
    COUNT(*) FILTER (WHERE v.vendas > 1)        AS voltaram
FROM vendas v
JOIN dw.vw_pedidos_entregues e USING (pedido_id)   -- só primeira compra entregue e dentro da janela
WHERE v.ordem = 1
GROUP BY primeira_atrasada
ORDER BY primeira_atrasada;
