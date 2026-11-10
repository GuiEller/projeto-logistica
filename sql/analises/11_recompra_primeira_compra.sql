-- 11_recompra_primeira_compra.sql
-- Pergunta   Quem teve a primeira compra atrasada volta menos?
-- Técnicas   DISTINCT ON para a primeira linha de cada pessoa. O desempate por pedido_id
--            garante a mesma escolha toda vez quando duas compras têm o mesmo horário.

WITH vendas AS (
    -- O horário completo da compra está no staging. A fato só guarda a chave do dia.
    SELECT f.pedido_id, f.cliente_id, o.order_purchase_timestamp
    FROM dw.fato_pedidos f
    JOIN staging.orders o ON o.order_id = f.pedido_id
    WHERE f.status_pedido NOT IN ('canceled', 'unavailable')
),
primeira AS (
    SELECT DISTINCT ON (cliente_id) cliente_id, pedido_id
    FROM vendas
    ORDER BY cliente_id, order_purchase_timestamp, pedido_id
),
compras AS (
    SELECT cliente_id, COUNT(*) AS vendas FROM vendas GROUP BY cliente_id
)
SELECT
    NOT e.entregue_no_prazo                     AS primeira_atrasada,
    COUNT(*)                                    AS pessoas,
    COUNT(*) FILTER (WHERE c.vendas > 1)        AS voltaram
FROM primeira p
JOIN dw.vw_pedidos_entregues e USING (pedido_id)   -- só primeira compra entregue e dentro da janela
JOIN compras c USING (cliente_id)
GROUP BY primeira_atrasada
ORDER BY primeira_atrasada;
