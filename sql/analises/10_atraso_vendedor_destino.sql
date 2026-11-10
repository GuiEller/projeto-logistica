-- 10_atraso_vendedor_destino.sql
-- Pergunta   O RJ atrasa por causa dos vendedores que atendem o estado ou por causa da rota até lá?
-- Técnicas   Comparação pareada. O mesmo vendedor aparece com pedidos para cada destino, então
--            a diferença entre destinos não vem de quem vende. CTE com HAVING para vendedor único.

WITH vendedor_unico AS (
    -- Pedido com dois vendedores não tem um responsável só pelo atraso, então fica fora.
    -- Conta vendedores distintos, não itens. Um vendedor com três itens no pedido continua sendo um.
    SELECT pedido_id, MIN(vendedor_id) AS vendedor_id
    FROM dw.fato_itens_pedido
    GROUP BY pedido_id
    HAVING COUNT(DISTINCT vendedor_id) = 1
)
SELECT
    u.vendedor_id,
    v.estado                                         AS estado_vendedor,
    e.estado,
    COUNT(*)                                         AS pedidos,
    COUNT(*) FILTER (WHERE NOT e.entregue_no_prazo)  AS atrasos
FROM dw.vw_pedidos_entregues e
JOIN vendedor_unico   u USING (pedido_id)
JOIN dw.dim_vendedor  v USING (vendedor_id)
WHERE e.estado IN ('RJ', 'SP', 'MG', 'ES')   -- RJ e os vizinhos do Sudeste que servem de controle
GROUP BY u.vendedor_id, v.estado, e.estado
ORDER BY u.vendedor_id, e.estado;
