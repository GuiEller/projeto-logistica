-- 13_recompra_por_estado.sql
-- Pergunta   A recompra muda de um estado para outro?
-- Técnicas   Agregação em dois passos. Primeiro conta as compras de cada pessoa, depois agrupa
--            as pessoas pelo estado do endereço mais recente. É a mesma regra do resumo do painel.

WITH compras AS (
    SELECT cliente_id, COUNT(*) AS vendas
    FROM dw.fato_pedidos
    WHERE status_pedido NOT IN ('canceled', 'unavailable')
    GROUP BY cliente_id
)
SELECT
    c.estado,
    COUNT(*)                                AS clientes,
    COUNT(*) FILTER (WHERE p.vendas > 1)    AS voltaram
FROM compras p
JOIN dw.dim_cliente c USING (cliente_id)
GROUP BY c.estado
ORDER BY c.estado;
