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

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Os horários da Olist não têm fuso. Fixar UTC impede que o Spark converta e mude a data de um pedido feito perto da meia-noite.
spark.conf.set("spark.sql.session.timeZone", "UTC")
spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.prata")

bronze = lambda t: spark.table(f"workspace.bronze.{t}")
# Dinheiro em DECIMAL e não em DOUBLE. DOUBLE soma 0,1 + 0,2 como 0,30000000000000004,
# e a receita precisa bater centavo por centavo com o Postgres.
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

pedidos = bronze("pedidos").select(
    F.col("order_id").alias("pedido_id"),
    F.col("customer_id").alias("cadastro_id"),
    F.col("order_status").alias("status_pedido"),
    F.to_timestamp("order_purchase_timestamp").alias("data_compra"),
    F.to_timestamp("order_approved_at").alias("data_aprovacao"),
    F.to_timestamp("order_delivered_carrier_date").alias("data_envio"),
    F.to_timestamp("order_delivered_customer_date").alias("data_entrega"),
    F.to_timestamp("order_estimated_delivery_date").alias("data_prometida"),
)

itens = bronze("itens").select(
    F.col("order_id").alias("pedido_id"),
    F.col("order_item_id").cast("int").alias("item_num"),
    F.col("product_id").alias("produto_id"),
    F.col("seller_id").alias("vendedor_id"),
    F.col("price").cast(DINHEIRO).alias("valor_item"),
    F.col("freight_value").cast(DINHEIRO).alias("valor_frete"),
)

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

vendedores = bronze("vendedores").select(
    F.col("seller_id").alias("vendedor_id"),
    # "sao paulo" e "SAO PAULO" viram "Sao Paulo". Sem isso, um GROUP BY por cidade separa a mesma cidade em duas.
    F.initcap("seller_city").alias("cidade"),
    F.col("seller_state").alias("estado"),
)

# LEFT JOIN na tradução porque duas categorias não têm versão em inglês. Com JOIN comum, esses produtos sumiriam.
produtos = (
    bronze("produtos").alias("p")
    .join(bronze("categorias").alias("t"), "product_category_name", "left")
    .select(
        F.col("product_id").alias("produto_id"),
        # 610 produtos vêm sem categoria. Nulo some do GROUP BY sem aviso, então vira 'sem_categoria'.
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

mais_recente_primeiro = Window.partitionBy("order_id").orderBy(F.col("review_answer_timestamp").desc_nulls_last())

avaliacoes = (
    bronze("avaliacoes")
    .withColumn("ordem", F.row_number().over(mais_recente_primeiro))
    .filter("ordem = 1")
    .select(
        F.col("order_id").alias("pedido_id"),
        F.col("review_score").cast("int").alias("nota"),
        F.to_timestamp("review_answer_timestamp").alias("data_resposta"),
    )
)

# Até aqui nenhum dado foi lido. O explain mostra o plano que o Spark montou, com a window e o filtro.
avaliacoes.explain()

# COMMAND ----------

# Agora sim as ações. Cada write executa o plano da tabela.
TABELAS = {
    "pedidos": pedidos, "itens": itens, "pagamentos": pagamentos, "avaliacoes": avaliacoes,
    "clientes": clientes, "vendedores": vendedores, "produtos": produtos,
}
for nome, df in TABELAS.items():
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"workspace.prata.{nome}")
    print(f"prata.{nome:<11} {spark.table(f'workspace.prata.{nome}').count():>7} linhas")

# COMMAND ----------

# Conferência da prata contra a bronze. Limpar não pode perder nem inventar registro.
prata = lambda t: spark.table(f"workspace.prata.{t}")

assert prata("pedidos").count() == bronze("pedidos").count() == 99441
assert prata("itens").count() == 112650
# Uma avaliação por pedido avaliado, e nenhuma nota fora de 1 a 5.
assert prata("avaliacoes").count() == prata("avaliacoes").select("pedido_id").distinct().count()
assert prata("avaliacoes").filter("nota NOT BETWEEN 1 AND 5").count() == 0
# Nenhuma data de compra pode ter ficado nula na conversão de texto para timestamp.
assert prata("pedidos").filter("data_compra IS NULL").count() == 0
# Receita exata, a mesma do Postgres.
receita = prata("itens").agg(F.sum("valor_item")).first()[0]
assert str(receita) == "13591643.70", receita
print("Prata ok. Receita de", receita)
