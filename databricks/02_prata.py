# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Prata. O dado limpo e tipado
# MAGIC
# MAGIC Lê a bronze, aplica os tipos e as regras de tratamento da seção 7.4 do SDD e grava no schema `prata`.
# MAGIC
# MAGIC **Contrato da camada.** Uma tabela por entidade, com tipo certo, nome em português e uma linha por chave.
# MAGIC Aqui ainda não há fato nem dimensão. Isso é trabalho da ouro.
# MAGIC
# MAGIC **Equivalente local.** A staging tipada do `001` mais as regras que o `003` aplica (avaliação mais recente, categoria nula, cidade padronizada).

# COMMAND ----------

# BLOCO 1. PREPARAÇÃO
# Em português simples: ligamos as ferramentas que o notebook vai usar e combinamos
# as "regras do jogo" (fuso horário, onde guardar e como representar dinheiro).

# "F" guarda as funções de transformação do Spark (renomear coluna, converter tipo...).
# "Window" cria "janelas": grupos de linhas que o Spark olha em conjunto (usado mais abaixo).
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Os horários da Olist não têm fuso. Fixar UTC impede que o Spark converta e mude a data de um pedido feito perto da meia-noite.
spark.conf.set("spark.sql.session.timeZone", "UTC")

# Cria a "pasta" (schema) onde a camada prata vai morar. IF NOT EXISTS = não dá erro se já existir.
spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.prata")

# Atalho para ler uma tabela da camada bronze pelo nome. bronze("pedidos") = "me dê a tabela de pedidos da bronze".
bronze = lambda nome_da_tabela: spark.table(f"workspace.bronze.{nome_da_tabela}")

# Dinheiro em DECIMAL e não em DOUBLE. DOUBLE soma 0,1 + 0,2 como 0,30000000000000004,
# e a receita precisa bater centavo por centavo com o Postgres.
# decimal(10,2) = até 10 dígitos no total, 2 deles depois da vírgula (centavos).
DINHEIRO = "decimal(10,2)"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Spark é preguiçoso
# MAGIC
# MAGIC As células abaixo só **descrevem** transformações (`select`, `withColumn`, `filter`). Nada é lido nem calculado ainda.
# MAGIC O Spark monta um plano e só executa quando aparece uma **ação** (`count`, `display`, `write`).
# MAGIC Com o plano inteiro na mão, ele junta passos, descarta colunas que ninguém usa e lê só o necessário.
# MAGIC É por isso que o `explain()` mais abaixo mostra um plano otimizado, e não a lista de passos na ordem em que foram escritos.

# COMMAND ----------

# BLOCO 2. UMA TABELA POR ENTIDADE (pedidos, itens, pagamentos, clientes, vendedores, produtos)
# Em português simples: a bronze guarda tudo como texto, com nomes em inglês. Aqui escolhemos
# as colunas que importam, convertemos cada uma para o tipo certo e damos nome em português.
#   F.col("x").alias("y")          = pega a coluna x e a renomeia para y
#   F.to_timestamp(...)            = converte o texto "2017-10-02 10:56:33" em data e hora de verdade
#   .cast("int") / .cast(DINHEIRO) = converte para número inteiro / dinheiro

# Pedidos: uma linha por pedido, com as 5 datas da vida do pedido (compra, aprovação, envio, entrega, prometida).
pedidos = bronze("pedidos").select(
    F.col("order_id").alias("pedido_id"),
    F.col("customer_id").alias("cadastro_id"),        # o cadastro daquele pedido (muda a cada pedido)
    F.col("order_status").alias("status_pedido"),
    F.to_timestamp("order_purchase_timestamp").alias("data_compra"),
    F.to_timestamp("order_approved_at").alias("data_aprovacao"),
    F.to_timestamp("order_delivered_carrier_date").alias("data_envio"),
    F.to_timestamp("order_delivered_customer_date").alias("data_entrega"),
    F.to_timestamp("order_estimated_delivery_date").alias("data_prometida"),
)

# Itens: uma linha por item vendido. Preço e frete viram DINHEIRO para somar sem erro de centavo.
itens = bronze("itens").select(
    F.col("order_id").alias("pedido_id"),
    F.col("order_item_id").cast("int").alias("item_num"),    # 1º, 2º, 3º item do pedido
    F.col("product_id").alias("produto_id"),
    F.col("seller_id").alias("vendedor_id"),
    F.col("price").cast(DINHEIRO).alias("valor_item"),
    F.col("freight_value").cast(DINHEIRO).alias("valor_frete"),
)

# Pagamentos: um pedido pode ter várias linhas (ex.: cartão + voucher), uma por forma de pagamento.
pagamentos = bronze("pagamentos").select(
    F.col("order_id").alias("pedido_id"),
    F.col("payment_sequential").cast("int").alias("sequencia"),
    F.col("payment_type").alias("tipo"),
    F.col("payment_installments").cast("int").alias("parcelas"),
    F.col("payment_value").cast(DINHEIRO).alias("valor_pago"),
)

# Cliente da Olist tem dois IDs. customer_id muda a cada pedido (é o cadastro do pedido),
# customer_unique_id é a pessoa. A prata guarda os dois, e a ouro usa a pessoa.
clientes = bronze("clientes").select(
    F.col("customer_id").alias("cadastro_id"),
    F.col("customer_unique_id").alias("cliente_id"),
    F.initcap("customer_city").alias("cidade"),
    F.col("customer_state").alias("estado"),
)

# Vendedores: uma linha por vendedor, com a cidade padronizada.
vendedores = bronze("vendedores").select(
    F.col("seller_id").alias("vendedor_id"),
    # "sao paulo" e "SAO PAULO" viram "Sao Paulo". Sem isso, um GROUP BY por cidade separa a mesma cidade em duas.
    F.initcap("seller_city").alias("cidade"),
    F.col("seller_state").alias("estado"),
)

# Produtos: cada produto com sua categoria e a tradução para o inglês.
# LEFT JOIN na tradução porque duas categorias não têm versão em inglês. Com JOIN comum, esses produtos sumiriam.
# ("left" mantém todo produto, mesmo sem tradução; a coluna de tradução fica vazia nesses casos.)
produtos = (
    bronze("produtos").alias("p")
    .join(bronze("categorias").alias("t"), "product_category_name", "left")
    .select(
        F.col("product_id").alias("produto_id"),
        # 610 produtos vêm sem categoria. Nulo some do GROUP BY sem aviso, então vira 'sem_categoria'.
        # coalesce(a, b, c) devolve o primeiro valor que NÃO é nulo.
        F.coalesce("product_category_name", F.lit("sem_categoria")).alias("categoria"),
        F.coalesce("product_category_name_english", "product_category_name", F.lit("sem_categoria")).alias("categoria_en"),
        F.col("product_photos_qty").cast("int").alias("qtd_fotos"),
        F.col("product_weight_g").cast("int").alias("peso_g"),
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Avaliação duplicada fica com a mais recente
# MAGIC
# MAGIC Alguns pedidos têm mais de uma avaliação. No Postgres isso foi resolvido com `DISTINCT ON`.
# MAGIC O Spark não tem `DISTINCT ON`, então o caminho é a window function `row_number`, a mesma ideia do `ROW_NUMBER` da `dim_cliente` no `003`.

# COMMAND ----------

# BLOCO 3. AVALIAÇÃO: FICAR COM UMA SÓ POR PEDIDO (a mais recente)
# Em português simples: se um cliente avaliou o mesmo pedido duas vezes, vale a última
# resposta. Para escolher, numeramos as avaliações de cada pedido da mais nova para a
# mais antiga e ficamos com a de número 1.

# "Janela" = um grupo de linhas olhado em conjunto. Aqui, uma janela por pedido (partitionBy),
# com as avaliações dele ordenadas da mais recente para a mais antiga (orderBy ... desc).
# desc_nulls_last joga avaliações sem data para o fim da fila.
mais_recente_primeiro = (
    Window.partitionBy("order_id")
    .orderBy(F.col("review_answer_timestamp").desc_nulls_last())
)

avaliacoes = (
    bronze("avaliacoes")
    # row_number numera as linhas dentro de cada janela: 1 = avaliação mais recente do pedido.
    .withColumn("ordem", F.row_number().over(mais_recente_primeiro))
    .filter("ordem = 1")  # fica só a número 1 de cada pedido
    .select(
        F.col("order_id").alias("pedido_id"),
        F.col("review_score").cast("int").alias("nota"),
        F.to_timestamp("review_answer_timestamp").alias("data_resposta"),
    )
)

# Até aqui nenhum dado foi lido. O explain mostra o plano que o Spark montou, com a window e o filtro.
avaliacoes.explain()

# COMMAND ----------

# BLOCO 4. GRAVAR AS TABELAS DA PRATA
# Em português simples: até agora só descrevemos as transformações. Gravar é a "ação" que
# faz o Spark finalmente ler os dados, calcular e salvar cada tabela no schema prata.

# Agora sim as ações. Cada write executa o plano da tabela.
TABELAS = {
    "pedidos": pedidos, "itens": itens, "pagamentos": pagamentos, "avaliacoes": avaliacoes,
    "clientes": clientes, "vendedores": vendedores, "produtos": produtos,
}
for nome, df in TABELAS.items():
    # mode("overwrite") = se a tabela já existe, substitui (rodar de novo dá o mesmo resultado).
    # overwriteSchema = aceita trocar as colunas, caso o desenho da tabela tenha mudado.
    # saveAsTable grava como tabela Delta, que o Databricks consegue consultar por nome.
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"workspace.prata.{nome}")
    # Confere na hora: lê a tabela que acabou de gravar e imprime quantas linhas ficaram.
    print(f"prata.{nome:<11} {spark.table(f'workspace.prata.{nome}').count():>7} linhas")

# COMMAND ----------

# BLOCO 5. CONFERÊNCIA DA PRATA CONTRA A BRONZE
# Em português simples: antes de seguir, o notebook confere o próprio trabalho. Se algum
# número não bater, ele PARA com erro e a camada ouro nunca recebe dado errado.

# Conferência da prata contra a bronze. Limpar não pode perder nem inventar registro.
# "assert" é uma trava: se a afirmação for falsa, o notebook PARA com erro na hora,
# e uma camada errada nunca chega à camada seguinte.
prata = lambda nome_da_tabela: spark.table(f"workspace.prata.{nome_da_tabela}")

# Mesma quantidade de pedidos na prata e na bronze (e igual ao total conhecido do Postgres).
assert prata("pedidos").count() == bronze("pedidos").count() == 99441
assert prata("itens").count() == 112650  # total de itens vendidos, o mesmo do Postgres
# Uma avaliação por pedido avaliado, e nenhuma nota fora de 1 a 5.
assert prata("avaliacoes").count() == prata("avaliacoes").select("pedido_id").distinct().count()
assert prata("avaliacoes").filter("nota NOT BETWEEN 1 AND 5").count() == 0
# Nenhuma data de compra pode ter ficado nula na conversão de texto para timestamp.
assert prata("pedidos").filter("data_compra IS NULL").count() == 0
# Receita exata, a mesma do Postgres.
receita = prata("itens").agg(F.sum("valor_item")).first()[0]
assert str(receita) == "13591643.70", receita
print("Prata ok. Receita de", receita)
