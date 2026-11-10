# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Ouro. O que o negócio consome
# MAGIC
# MAGIC Monta o modelo estrela a partir da prata, calcula as tabelas de KPI do painel e exporta cada uma como Parquet.
# MAGIC
# MAGIC **Contrato da camada.** Fatos com grão declarado, dimensões com uma linha por chave e tabelas pequenas, prontas para o painel ler sem fazer conta.
# MAGIC
# MAGIC **Equivalente local.** O schema `dw` do `003` e as visões do `004`.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.conf.set("spark.sql.session.timeZone", "UTC")
spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.ouro")
# Volume onde os Parquet do painel são gravados. Depois saem daqui para app/data no repositório.
spark.sql("CREATE VOLUME IF NOT EXISTS workspace.ouro.exportacao")
EXPORTACAO = "/Volumes/workspace/ouro/exportacao"

prata = lambda t: spark.table(f"workspace.prata.{t}")

def salvar(df, nome):
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(f"workspace.ouro.{nome}")
    return spark.table(f"workspace.ouro.{nome}")

# Chave de data inteira AAAAMMDD, a mesma do Postgres. Leve para JOIN e legível.
chave_data = lambda col: F.date_format(col, "yyyyMMdd").cast("int")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dimensões

# COMMAND ----------

# dim_data. Um dia por linha, do primeiro ao último pedido, sem buracos.
# sequence trabalha com DATE puro, então o bug do horário de verão que apareceu no Postgres não acontece aqui.
limites = prata("pedidos").agg(F.min(F.to_date("data_compra")).alias("ini"), F.max(F.to_date("data_compra")).alias("fim"))
dim_data = salvar(
    limites.select(F.explode(F.sequence("ini", "fim")).alias("data")).select(
        chave_data("data").alias("data_sk"),
        "data",
        F.year("data").alias("ano"),
        F.month("data").alias("mes"),
        F.date_format("data", "yyyy-MM").alias("ano_mes"),
    ),
    "dim_data",
)

# dim_cliente. Uma PESSOA por linha. Quem se mudou fica com o endereço do pedido mais recente.
mais_recente = Window.partitionBy("cliente_id").orderBy(F.col("data_compra").desc())
REGIAO = (
    F.when(F.col("estado").isin("SP", "RJ", "MG", "ES"), "Sudeste")
    .when(F.col("estado").isin("PR", "SC", "RS"), "Sul")
    .when(F.col("estado").isin("MS", "MT", "GO", "DF"), "Centro-Oeste")
    .when(F.col("estado").isin("BA", "SE", "AL", "PE", "PB", "RN", "CE", "PI", "MA"), "Nordeste")
    .otherwise("Norte")
)
dim_cliente = salvar(
    prata("clientes").join(prata("pedidos"), "cadastro_id")
    .withColumn("ordem", F.row_number().over(mais_recente))
    .filter("ordem = 1")
    .select("cliente_id", "cidade", "estado", REGIAO.alias("regiao")),
    "dim_cliente",
)

dim_produto = salvar(prata("produtos"), "dim_produto")
dim_vendedor = salvar(prata("vendedores"), "dim_vendedor")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fatos
# MAGIC
# MAGIC Dois grãos, igual ao Postgres. Receita sai da fato de itens. Frete do pedido, atraso e nota saem da fato de pedidos.
# MAGIC Numa fato só, um pedido com 3 itens contaria o frete e a nota 3 vezes.

# COMMAND ----------

pedidos_com_pessoa = prata("pedidos").join(prata("clientes").select("cadastro_id", "cliente_id"), "cadastro_id")

# Grão: um item vendido.
fato_itens = salvar(
    prata("itens").join(pedidos_com_pessoa, "pedido_id").select(
        "pedido_id", "item_num",
        chave_data("data_compra").alias("data_compra_sk"),
        "cliente_id", "produto_id", "vendedor_id", "status_pedido", "valor_item", "valor_frete",
    ),
    "fato_itens_pedido",
)

# Grão: um pedido. Itens e pagamentos são agregados por pedido ANTES do join.
# Juntar primeiro e agregar depois multiplicaria linhas.
itens_por_pedido = prata("itens").groupBy("pedido_id").agg(
    F.count("*").alias("qtd_itens"), F.sum("valor_item").alias("valor_itens"), F.sum("valor_frete").alias("valor_frete"),
)
pagos_por_pedido = prata("pagamentos").groupBy("pedido_id").agg(
    F.sum("valor_pago").alias("valor_pago"), F.max("parcelas").alias("parcelas"),
)
entrega, prometida, compra = F.to_date("data_entrega"), F.to_date("data_prometida"), F.to_date("data_compra")

fato_pedidos = salvar(
    pedidos_com_pessoa
    .join(itens_por_pedido, "pedido_id", "left")
    .join(pagos_por_pedido, "pedido_id", "left")
    .join(prata("avaliacoes").select("pedido_id", F.col("nota").alias("nota_avaliacao")), "pedido_id", "left")
    .select(
        "pedido_id",
        chave_data("data_compra").alias("data_compra_sk"),
        "cliente_id", "status_pedido",
        # Pedido cancelado antes de ter item não tem linha em itens. O nulo vira zero.
        F.coalesce("qtd_itens", F.lit(0)).alias("qtd_itens"),
        F.coalesce("valor_itens", F.lit(0)).alias("valor_itens"),
        F.coalesce("valor_frete", F.lit(0)).alias("valor_frete"),
        "valor_pago", "parcelas",
        # Sem data de entrega o datediff dá nulo, e é isso que queremos. Pedido não entregue não tem atraso.
        F.datediff(entrega, compra).alias("dias_entrega"),
        F.datediff(prometida, compra).alias("dias_prometidos"),
        F.datediff(entrega, prometida).alias("dias_atraso"),
        F.when(entrega.isNotNull(), entrega <= prometida).alias("entregue_no_prazo"),
        "nota_avaliacao",
    ),
    "fato_pedidos",
)

# COMMAND ----------

# Os mesmos testes de integridade do Postgres. Se algum falhar, o painel não recebe número errado.
assert fato_pedidos.count() == prata("pedidos").count() == 99441, "pedido perdido ou duplicado"
assert str(fato_itens.agg(F.sum("valor_item")).first()[0]) == "13591643.70", "receita divergente"
n_dias = dim_data.count()
dias_esperados = dim_data.agg(F.datediff(F.max("data"), F.min("data")) + 1).first()[0]
assert n_dias == dias_esperados, "calendário com buraco"
assert fato_pedidos.filter("dias_entrega IS NULL AND (dias_atraso IS NOT NULL OR entregue_no_prazo IS NOT NULL)").count() == 0
assert dim_cliente.count() == dim_cliente.select("cliente_id").distinct().count(), "cliente duplicado"
print(f"Integridade ok. {fato_pedidos.count()} pedidos, {dim_cliente.count()} clientes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pedidos entregues na janela de análise
# MAGIC
# MAGIC Equivale à `vw_pedidos_entregues`. Janela de 01/2017 a 08/2018, porque antes e depois há poucos pedidos e a tendência distorce.

# COMMAND ----------

NA_JANELA = F.col("data").between("2017-01-01", "2018-08-31")
VENDA_VALIDA = ~F.col("status_pedido").isin("canceled", "unavailable")

pedidos_entregues = salvar(
    fato_pedidos.join(dim_data, F.col("data_compra_sk") == F.col("data_sk"))
    .join(dim_cliente.select("cliente_id", "estado", "regiao"), "cliente_id")
    .filter((F.col("status_pedido") == "delivered") & F.col("dias_atraso").isNotNull() & NA_JANELA)
    .select(
        "pedido_id", F.col("data").alias("data_compra"), "ano_mes", "estado", "regiao",
        "valor_itens", "valor_frete", "dias_entrega", "dias_prometidos", "dias_atraso",
        "entregue_no_prazo", "nota_avaliacao",
        (F.col("nota_avaliacao") <= 2).alias("nota_baixa"),
        F.when(F.col("dias_atraso") <= -10, "1. 10+ dias adiantado")
        .when(F.col("dias_atraso") <= 0, "2. até 10 dias adiantado / no dia")
        .when(F.col("dias_atraso") <= 3, "3. 1 a 3 dias de atraso")
        .when(F.col("dias_atraso") <= 7, "4. 4 a 7 dias de atraso")
        .otherwise("5. mais de 7 dias de atraso").alias("faixa_atraso"),
    ),
    "pedidos_entregues",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tabelas do painel
# MAGIC
# MAGIC Cada uma responde uma página. São pequenas (dezenas de linhas), então o painel abre rápido e não precisa de banco.

# COMMAND ----------

atrasado = (~F.col("entregue_no_prazo")).cast("int")

# Visão geral e Vendas. Receita, pedidos e clientes por mês, igual à vw_receita_mensal.
receita_mes = (
    fato_itens.join(dim_data, F.col("data_compra_sk") == F.col("data_sk"))
    .filter(VENDA_VALIDA & NA_JANELA)
    .groupBy("ano_mes")
    .agg(F.countDistinct("pedido_id").alias("pedidos"), F.countDistinct("cliente_id").alias("clientes"),
         F.sum("valor_item").alias("receita"))
)
nota_mes = (
    fato_pedidos.join(dim_data, F.col("data_compra_sk") == F.col("data_sk"))
    .filter(VENDA_VALIDA & NA_JANELA)
    .groupBy("ano_mes").agg(F.avg("nota_avaliacao").alias("nota_media"))
)
atraso_mes = pedidos_entregues.groupBy("ano_mes").agg(F.avg(atrasado).alias("taxa_atraso"))
kpis_mensais = salvar(
    receita_mes.join(nota_mes, "ano_mes", "left").join(atraso_mes, "ano_mes", "left")
    .withColumn("ticket_medio", F.col("receita") / F.col("pedidos"))
    .orderBy("ano_mes"),
    "kpis_mensais",
)

# Vendas. Curva ABC por categoria, a mesma regra da análise 02.
por_receita = Window.orderBy(F.desc("receita"))
total = Window.partitionBy()
categorias_abc = salvar(
    fato_itens.join(dim_data, F.col("data_compra_sk") == F.col("data_sk"))
    .filter(VENDA_VALIDA & NA_JANELA)
    .join(dim_produto, "produto_id")
    .groupBy("categoria", "categoria_en")
    .agg(F.sum("valor_item").alias("receita"), F.count("*").alias("itens"))
    .withColumn("participacao", F.col("receita") / F.sum("receita").over(total))
    .withColumn("acumulado", F.sum("participacao").over(por_receita.rowsBetween(Window.unboundedPreceding, 0)))
    .withColumn("ranking", F.row_number().over(por_receita))
    # A categoria que cruza a linha dos 80% ainda entra na classe A.
    .withColumn("classe_abc", F.when(F.col("acumulado") - F.col("participacao") < 0.80, "A")
                .when(F.col("acumulado") - F.col("participacao") < 0.95, "B").otherwise("C")),
    "categorias_abc",
)

# Logística. Atraso, prazo e frete por estado.
entrega_por_estado = salvar(
    pedidos_entregues.groupBy("estado", "regiao").agg(
        F.count("*").alias("pedidos"),
        F.avg("dias_entrega").alias("entrega_media"),
        F.avg("dias_prometidos").alias("prazo_medio"),
        F.avg(atrasado).alias("taxa_atraso"),
        F.avg("valor_frete").alias("frete_medio"),
        F.avg("nota_avaliacao").alias("nota_media"),
    ),
    "entrega_por_estado",
)

# Cliente. Nota por faixa de atraso.
nota_por_faixa = salvar(
    pedidos_entregues.filter("nota_avaliacao IS NOT NULL").groupBy("faixa_atraso").agg(
        F.count("*").alias("pedidos"),
        F.avg("nota_avaliacao").alias("nota_media"),
        F.avg(F.col("nota_baixa").cast("int")).alias("pct_nota_baixa"),
    ).orderBy("faixa_atraso"),
    "nota_por_faixa",
)

# Resumo de uma linha. Os três primeiros números são os que a conferência compara com o Postgres.
compras_por_pessoa = fato_pedidos.filter(VENDA_VALIDA).groupBy("cliente_id").count()
avaliados = pedidos_entregues.filter("nota_avaliacao IS NOT NULL")
resumo = salvar(
    spark.range(1).select(
        F.lit(fato_pedidos.count()).alias("pedidos_total"),
        F.lit(fato_itens.agg(F.sum("valor_item")).first()[0]).alias("receita_total"),
        F.lit(dim_cliente.count()).alias("clientes_total"),
        F.lit(compras_por_pessoa.filter("count > 1").count() / compras_por_pessoa.count()).alias("pct_recompra"),
        F.lit(avaliados.agg(F.avg(atrasado)).first()[0]).alias("pct_atrasados"),
        F.lit(avaliados.filter("nota_baixa AND NOT entregue_no_prazo").count()
              / avaliados.filter("nota_baixa").count()).alias("parcela_notas_baixas_atraso"),
    ),
    "resumo",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Databricks SQL
# MAGIC
# MAGIC As tabelas da ouro estão no catálogo e podem ser consultadas em SQL puro, aqui ou no SQL Editor.

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT estado, pedidos, ROUND(100 * taxa_atraso, 1) AS taxa_atraso_pct, ROUND(nota_media, 2) AS nota_media
# MAGIC FROM workspace.ouro.entrega_por_estado
# MAGIC WHERE pedidos >= 300
# MAGIC ORDER BY taxa_atraso DESC
# MAGIC LIMIT 10

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exportação para o painel
# MAGIC
# MAGIC Cada tabela vira **um** arquivo Parquet. O Spark gravaria uma pasta com vários pedaços, e o painel quer um arquivo simples,
# MAGIC então a tabela (pequena) passa pelo pandas. DECIMAL vira DOUBLE porque o pandas leria DECIMAL como objeto Python, lento e chato de plotar.

# COMMAND ----------

from pyspark.sql.types import DecimalType

PAINEL = ["kpis_mensais", "categorias_abc", "entrega_por_estado", "nota_por_faixa", "resumo"]
for nome in PAINEL:
    df = spark.table(f"workspace.ouro.{nome}")
    df = df.select([F.col(c.name).cast("double") if isinstance(c.dataType, DecimalType) else F.col(c.name) for c in df.schema])
    tabela = df.toPandas()
    # No Serverless (Spark Connect), o toPandas guarda métricas da execução em attrs. O pandas
    # tenta gravar attrs no Parquet como JSON e quebra com "PlanMetrics is not JSON serializable".
    # As métricas não são dado, então saem antes de gravar.
    tabela.attrs = {}
    tabela.to_parquet(f"{EXPORTACAO}/{nome}.parquet", index=False)
    print(f"{nome}.parquet  {df.count()} linhas")

display(spark.table("workspace.ouro.resumo"))
