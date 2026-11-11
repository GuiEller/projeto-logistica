-- =====================================================================================
-- TESTES DE INTEGRIDADE DO MODELO ESTRELA
-- =====================================================================================
-- O QUE ESTE ARQUIVO FAZ, EM PORTUGUÊS SIMPLES
--   É o "fiscal" do pipeline. Depois que o modelo estrela é montado, ele confere seis
--   regras que TÊM que ser verdade. Se uma falhar, o pipeline PARA na hora com uma
--   mensagem de erro, em vez de entregar número errado para a análise.
--   Número errado no painel é pior do que painel nenhum.
--
-- COMO LER
--   Cada teste tem o mesmo desenho: (1) calcula algo, (2) compara com o esperado,
--   (3) se for diferente, levanta um erro (RAISE EXCEPTION) e tudo para.
--
-- Nunca desligue nem pule um destes testes para "fazer o pipeline passar".
-- Se falhar, o problema está nos dados ou no modelo, e é lá que se corrige.
-- =====================================================================================

-- Faz o psql abortar no primeiro erro. Sem isto ele continuaria e o teste não pararia nada.
\set ON_ERROR_STOP on

-- DO $$ ... $$ roda um bloco de código (PL/pgSQL) que pode ter variáveis e IF.
DO $$
DECLARE
    -- Variáveis do bloco, cada uma com o nome do que guarda:
    receita_staging  NUMERIC;  -- receita somada na origem (staging)
    receita_dw       NUMERIC;  -- receita somada no modelo (dw)
    pedidos_staging  INT;      -- quantos pedidos na origem
    pedidos_dw       INT;      -- quantos pedidos no modelo
    qtd_dias         INT;      -- quantos dias existem no calendário
    dias_esperados   INT;      -- quantos dias DEVERIAM existir (do primeiro ao último)
    qtd_problemas    INT;      -- reaproveitada: quantas linhas ruins o teste achou
BEGIN

    -- TESTE 1. A receita do modelo bate centavo por centavo com a da origem.
    --    Se um JOIN perdesse ou duplicasse itens, a soma mudaria e este teste pegaria.
    SELECT SUM(price)      INTO receita_staging FROM staging.order_items;
    SELECT SUM(valor_item) INTO receita_dw      FROM dw.fato_itens_pedido;
    IF receita_staging <> receita_dw THEN
        RAISE EXCEPTION 'Receita divergente. staging % x dw %', receita_staging, receita_dw;
    END IF;

    -- TESTE 2. Nenhum pedido foi perdido nem duplicado na fato de pedidos.
    SELECT COUNT(*) INTO pedidos_staging FROM staging.orders;
    SELECT COUNT(*) INTO pedidos_dw      FROM dw.fato_pedidos;
    IF pedidos_staging <> pedidos_dw THEN
        RAISE EXCEPTION 'Contagem de pedidos divergente. staging % x dw %', pedidos_staging, pedidos_dw;
    END IF;

    -- TESTE 3. O calendário não tem buracos.
    --    Do primeiro ao último dia, a quantidade de linhas tem que ser igual ao número
    --    de dias do intervalo. Foi ESTE teste que pegou o bug do horário de verão.
    SELECT COUNT(*), MAX(data) - MIN(data) + 1 INTO qtd_dias, dias_esperados FROM dw.dim_data;
    IF qtd_dias <> dias_esperados THEN
        RAISE EXCEPTION 'dim_data tem % dias, esperado %', qtd_dias, dias_esperados;
    END IF;

    -- TESTE 4. Toda nota está na escala de 1 a 5.
    SELECT COUNT(*) INTO qtd_problemas FROM dw.fato_pedidos WHERE nota_avaliacao NOT BETWEEN 1 AND 5;
    IF qtd_problemas > 0 THEN
        RAISE EXCEPTION '% pedidos com nota fora de 1 a 5', qtd_problemas;
    END IF;

    -- TESTE 5. Atraso só existe para pedido que foi entregue.
    --    Protege contra alguém trocar a conta por algo como COALESCE(data_entrega, hoje),
    --    que INVENTARIA atraso para pedidos que nem chegaram.
    SELECT COUNT(*) INTO qtd_problemas FROM dw.fato_pedidos
    WHERE dias_entrega IS NULL AND (dias_atraso IS NOT NULL OR entregue_no_prazo IS NOT NULL);
    IF qtd_problemas > 0 THEN
        RAISE EXCEPTION '% pedidos com atraso calculado sem data de entrega', qtd_problemas;
    END IF;

    -- TESTE 6. Uma linha por pessoa na dim_cliente.
    --    COUNT(*) conta linhas, COUNT(DISTINCT ...) conta pessoas diferentes.
    --    Se as duas contagens diferem, há alguém repetido.
    SELECT COUNT(*) - COUNT(DISTINCT cliente_id) INTO qtd_problemas FROM dw.dim_cliente;
    IF qtd_problemas > 0 THEN
        RAISE EXCEPTION '% clientes duplicados na dim_cliente', qtd_problemas;
    END IF;

    -- Chegou aqui, os seis testes passaram. Esta linha é o sinal verde que o
    -- docker compose mostra no log e que o GitHub Actions procura para liberar o CI.
    RAISE NOTICE 'Integridade ok. % pedidos, receita de %', pedidos_dw, receita_dw;
END $$;
