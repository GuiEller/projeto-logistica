# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Bronze. O dado como chegou
# MAGIC
# MAGIC Lê os 8 CSVs da Olist que estão no volume e grava cada um como tabela Delta no schema `bronze`.
# MAGIC
# MAGIC **Contrato da camada.** Nada é corrigido aqui. Todas as colunas ficam como texto, do jeito que vieram no arquivo.
# MAGIC Se uma regra de limpeza mudar amanhã, a prata é refeita a partir da bronze, sem baixar nada de novo.
# MAGIC
# MAGIC **Equivalente local.** Os CSVs em `data/raw` e a staging do `001`/`002`.

# COMMAND ----------

# O volume é a "pasta" do Unity Catalog onde os CSVs foram enviados pela interface.
ORIGEM = "/Volumes/workspace/default/olist_raw"

# Nome da tabela bronze -> arquivo de origem, com a contagem de registros conferida
# no Postgres. Contar com wc -l daria errado nas avaliações, que têm quebra de linha dentro das aspas.
ARQUIVOS = {
    "pedidos":    ("olist_orders_dataset.csv",              99441),
    "itens":      ("olist_order_items_dataset.csv",        112650),
    "pagamentos": ("olist_order_payments_dataset.csv",     103886),
    "avaliacoes": ("olist_order_reviews_dataset.csv",       99224),
    "clientes":   ("olist_customers_dataset.csv",           99441),
    "produtos":   ("olist_products_dataset.csv",            32951),
    "vendedores": ("olist_sellers_dataset.csv",              3095),
    "categorias": ("product_category_name_translation.csv",    71),
}

spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.bronze")

# COMMAND ----------

from pyspark.sql import functions as F

for tabela, (arquivo, esperado) in ARQUIVOS.items():
    df = (
        spark.read
        .option("header", True)
        # Comentário de avaliação pode ter quebra de linha dentro das aspas. Sem multiLine,
        # o Spark cortaria o registro no meio e criaria linhas falsas.
        .option("multiLine", True)
        .option("escape", '"')
        .csv(f"{ORIGEM}/{arquivo}")
        # Linhagem. Daqui a seis meses dá para saber de que arquivo e de quando veio cada linha.
        .withColumn("_arquivo_origem", F.lit(arquivo))
        .withColumn("_carregado_em", F.current_timestamp())
    )
    # O CSV de tradução começa com BOM, um caractere invisível que grudaria no nome da primeira coluna.
    df = df.toDF(*[c.replace("﻿", "") for c in df.columns])

    # overwrite deixa o notebook repetível. Rodar duas vezes dá o mesmo resultado.
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"workspace.bronze.{tabela}")

    n = spark.table(f"workspace.bronze.{tabela}").count()
    status = "ok" if n == esperado else "DIVERGENTE"
    print(f"{tabela:<11} {n:>7} linhas (esperado {esperado:>7})  {status}")
    # Camada que chega com linha a mais ou a menos não pode seguir para a prata.
    assert n == esperado, f"bronze.{tabela} com {n} linhas, esperado {esperado}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## O que é uma tabela Delta
# MAGIC
# MAGIC Por baixo são arquivos Parquet mais um log de transações (`_delta_log`). O log dá três coisas que CSV e Parquet puros não dão.
# MAGIC 1. **Transação.** Uma escrita que falha no meio não deixa a tabela pela metade.
# MAGIC 2. **Histórico.** Cada escrita vira uma versão. `DESCRIBE HISTORY` mostra quem gravou o quê e quando.
# MAGIC 3. **Time travel.** Dá para ler a versão de ontem com `VERSION AS OF`.

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE HISTORY workspace.bronze.pedidos

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Tudo texto, como prometido. A tipagem acontece na prata.
# MAGIC SELECT * FROM workspace.bronze.pedidos LIMIT 5
