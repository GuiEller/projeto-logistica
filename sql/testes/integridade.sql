-- Testes de integridade do modelo estrela. Cada bloco levanta erro se a regra falhar,
-- e o pipeline para na hora em vez de entregar número errado para a análise.
-- Número errado no painel é pior do que painel nenhum.

\set ON_ERROR_STOP on

DO $$
DECLARE
    v_stg NUMERIC; v_dw NUMERIC; n_stg INT; n_dw INT; n_dias INT; n_esperado INT; n INT;
BEGIN
    -- 1. A receita do fato bate centavo por centavo com a staging.
    --    Se um JOIN perdesse ou duplicasse itens, a soma mudaria.
    SELECT SUM(price)      INTO v_stg FROM staging.order_items;
    SELECT SUM(valor_item) INTO v_dw  FROM dw.fato_itens_pedido;
    IF v_stg <> v_dw THEN
        RAISE EXCEPTION 'Receita divergente. staging % x dw %', v_stg, v_dw;
    END IF;

    -- 2. Nenhum pedido perdido ou duplicado na fato de pedidos.
    SELECT COUNT(*) INTO n_stg FROM staging.orders;
    SELECT COUNT(*) INTO n_dw  FROM dw.fato_pedidos;
    IF n_stg <> n_dw THEN
        RAISE EXCEPTION 'Contagem de pedidos divergente. staging % x dw %', n_stg, n_dw;
    END IF;

    -- 3. Calendário sem buracos. Foi este teste que pegou o bug do horário de verão.
    SELECT COUNT(*), MAX(data) - MIN(data) + 1 INTO n_dias, n_esperado FROM dw.dim_data;
    IF n_dias <> n_esperado THEN
        RAISE EXCEPTION 'dim_data tem % dias, esperado %', n_dias, n_esperado;
    END IF;

    -- 4. Notas dentro da escala de 1 a 5.
    SELECT COUNT(*) INTO n FROM dw.fato_pedidos WHERE nota_avaliacao NOT BETWEEN 1 AND 5;
    IF n > 0 THEN
        RAISE EXCEPTION '% pedidos com nota fora de 1 a 5', n;
    END IF;

    -- 5. Atraso só existe para pedido entregue. Protege contra alguém trocar a conta
    --    por algo como COALESCE(data_entrega, hoje), que inventaria atraso.
    SELECT COUNT(*) INTO n FROM dw.fato_pedidos
    WHERE dias_entrega IS NULL AND (dias_atraso IS NOT NULL OR entregue_no_prazo IS NOT NULL);
    IF n > 0 THEN
        RAISE EXCEPTION '% pedidos com atraso calculado sem data de entrega', n;
    END IF;

    -- 6. Uma linha por pessoa na dim_cliente.
    SELECT COUNT(*) - COUNT(DISTINCT cliente_id) INTO n FROM dw.dim_cliente;
    IF n > 0 THEN
        RAISE EXCEPTION '% clientes duplicados na dim_cliente', n;
    END IF;

    RAISE NOTICE 'Integridade ok. % pedidos, receita de %', n_dw, v_dw;
END $$;
