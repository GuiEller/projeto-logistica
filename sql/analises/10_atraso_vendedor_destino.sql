
-- 10_atraso_vendedor_destino.sql
-- Pergunta   O RJ atrasa por causa dos vendedores que atendem o estado ou por causa da rota até lá?
-- Técnicas   Comparação pareada. O mesmo vendedor aparece com pedidos para cada destino, então
--            a diferença entre destinos não vem de quem vende. CTE com HAVING para vendedor único.
--
-- EM PORTUGUÊS SIMPLES
--   Para saber se o problema é o VENDEDOR ou o CAMINHO, comparamos o vendedor com ele mesmo.
--   Pegamos cada vendedor e olhamos quantos pedidos dele atrasaram quando o destino era o RJ
--   e quantos atrasaram quando o destino era SP, MG ou ES. Se o mesmo vendedor atrasa muito
--   mais para o RJ, a culpa não é dele: está no trajeto até o cliente.
--   (É como testar se um aluno é fraco ou se a prova daquela sala é que era difícil,
--   dando a mesma prova para o mesmo aluno em salas diferentes.)

-- CTE (tabela temporária desta consulta): só os pedidos que tiveram UM único vendedor.
WITH vendedor_unico AS (
    -- Pedido com dois vendedores não tem um responsável só pelo atraso, então fica fora.
    -- Conta vendedores distintos, não itens. Um vendedor com três itens no pedido continua sendo um.
    SELECT pedido_id, MIN(vendedor_id) AS vendedor_id   -- com um só vendedor, MIN() é ele mesmo
    FROM dw.fato_itens_pedido
    GROUP BY pedido_id
    HAVING COUNT(DISTINCT vendedor_id) = 1              -- HAVING filtra DEPOIS de agrupar

)
SELECT
    vendedor_do_pedido.vendedor_id,
    vendedor.estado                                       AS estado_vendedor,   -- de onde ele envia
    entrega.estado,                                                             -- para onde enviou
    COUNT(*)                                              AS pedidos,
    -- FILTER conta só as linhas que atendem à condição: aqui, os pedidos fora do prazo.
    COUNT(*) FILTER (WHERE NOT entrega.entregue_no_prazo) AS atrasos
FROM dw.vw_pedidos_entregues AS entrega
JOIN vendedor_unico          AS vendedor_do_pedido USING (pedido_id)
JOIN dw.dim_vendedor         AS vendedor           USING (vendedor_id)
WHERE entrega.estado IN ('RJ', 'SP', 'MG', 'ES')   -- RJ e os vizinhos do Sudeste que servem de controle
GROUP BY vendedor_do_pedido.vendedor_id, vendedor.estado, entrega.estado
ORDER BY vendedor_do_pedido.vendedor_id, entrega.estado;
