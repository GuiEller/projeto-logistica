"""
Conferência da camada ouro (Parquet exportado do Databricks) contra o PostgreSQL.

Duas fontes que deveriam ser iguais e não foram conferidas são duas fontes de erro.
Os testes que precisam do banco consultam o container olist-db. Sem o container
(por exemplo, no job de pytest do CI, que não sobe banco), eles são pulados.
O job do pipeline SQL sobe o banco e roda esta conferência.
"""

import io
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "app" / "data"


# Tabela da camada ouro, análise SQL equivalente e as colunas que formam o grão (uma linha por combinação).
TABELAS_DO_RELATORIO = {
    "nota_por_dia_atraso": ("07_nota_por_dia_atraso.sql", ["dias_atraso"]),
    "entrega_por_regiao": ("08_entrega_por_regiao.sql", ["regiao"]),
    "nota_por_regiao_atraso": ("09_nota_por_regiao_atraso.sql", ["regiao", "atrasado"]),
    "atraso_vendedor_destino": ("10_atraso_vendedor_destino.sql", ["vendedor_id", "estado"]),
    "recompra_primeira_compra": ("11_recompra_primeira_compra.sql", ["primeira_atrasada"]),
}


def ler(nome):
    return pd.read_parquet(DADOS / f"{nome}.parquet")


def postgres(sql):
    """Roda uma consulta no container e devolve as linhas como listas de texto."""
    saida = subprocess.run(
        ["docker", "exec", "olist-db", "psql", "-U", "postgres", "-d", "olist", "-At", "-F", "|", "-c", sql],
        capture_output=True, text=True, check=True,
    ).stdout
    return [linha.split("|") for linha in saida.strip().splitlines()]


def analise_pg(arquivo):
    """Roda um arquivo de sql/analises no container e devolve o resultado com cabeçalho.

    O arquivo vai pelo stdin porque o container não enxerga a pasta do repositório.
    O psql escreve booleano como t/f no CSV. true_values e false_values convertem,
    senão pg[pg.atrasado] filtraria texto em vez de booleano.
    """
    saida = subprocess.run(
        ["docker", "exec", "-i", "olist-db", "psql", "-U", "postgres", "-d", "olist", "--csv", "-v", "ON_ERROR_STOP=1", "-f", "-"],
        input=(RAIZ / "sql" / "analises" / arquivo).read_text(encoding="utf-8"),
        # UTF-8 explícito. No Windows o padrão é cp1252, os acentos dos comentários chegam
        # corrompidos e o psql descarta a consulta. ON_ERROR_STOP faz esse erro virar falha.
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    return pd.read_csv(io.StringIO(saida), true_values=["t"], false_values=["f"])


def banco_disponivel():
    if not shutil.which("docker"):
        return False
    try:
        return postgres("SELECT 1") == [["1"]]
    except subprocess.CalledProcessError:
        return False


precisa_banco = pytest.mark.skipif(not banco_disponivel(), reason="container olist-db fora do ar")


# ------------------------------------------------------------ sem banco

def test_parquets_do_painel_existem():
    for nome in ["kpis_mensais", "categorias_abc", "entrega_por_estado", "nota_por_faixa", "resumo",
                 *TABELAS_DO_RELATORIO]:
        assert (DADOS / f"{nome}.parquet").exists(), f"falta app/data/{nome}.parquet"


def test_receita_das_categorias_bate_com_a_mensal():
    # As duas tabelas usam o mesmo filtro (venda válida e janela). Se uma regra mudar só numa, a soma diverge.
    assert ler("categorias_abc").receita.sum() == pytest.approx(ler("kpis_mensais").receita.sum(), abs=0.01)


def test_janela_de_analise():
    meses = ler("kpis_mensais").ano_mes
    assert meses.min() == "2017-01" and meses.max() == "2018-08" and len(meses) == 20


def test_curva_abc_em_ordem():
    abc = ler("categorias_abc").sort_values("ranking")
    # A classe nunca volta atrás. Uma categoria C antes de uma A quer dizer acumulado errado.
    assert list(abc.classe_abc) == sorted(abc.classe_abc)
    assert abc.acumulado.iloc[-1] == pytest.approx(1.0)


def test_dia_atraso_fecha_com_as_faixas():
    # As faixas são os mesmos dias agrupados. Pedidos e notas baixas somados precisam dar o mesmo total.
    dia, faixa = ler("nota_por_dia_atraso"), ler("nota_por_faixa")
    assert dia.pedidos.sum() == faixa.pedidos.sum()
    assert dia.notas_baixas.sum() == (faixa.pedidos * faixa.pct_nota_baixa).round().sum()


def test_regiao_fecha_com_os_estados():
    por_estado = ler("entrega_por_estado").groupby("regiao").pedidos.sum()
    por_regiao = ler("entrega_por_regiao").set_index("regiao").pedidos
    assert por_regiao.sort_index().to_dict() == por_estado.sort_index().to_dict()


def test_percentis_em_ordem():
    r = ler("entrega_por_regiao")
    assert ((r.p10 <= r.p25) & (r.p25 <= r.p50) & (r.p50 <= r.p75) & (r.p75 <= r.p90)).all()


# ------------------------------------------------------------ com banco

@precisa_banco
def test_totais_batem_com_o_postgres():
    r = ler("resumo").iloc[0]
    (pedidos,), (receita,), (clientes,) = (
        postgres("SELECT COUNT(*) FROM dw.fato_pedidos")[0],
        postgres("SELECT SUM(valor_item) FROM dw.fato_itens_pedido")[0],
        postgres("SELECT COUNT(*) FROM dw.dim_cliente")[0],
    )
    assert r.pedidos_total == int(pedidos)
    assert r.receita_total == pytest.approx(float(receita), abs=0.01)
    assert r.clientes_total == int(clientes)


@precisa_banco
def test_kpis_mensais_batem_mes_a_mes():
    pg = pd.DataFrame(
        postgres("SELECT ano_mes, pedidos, clientes, receita FROM dw.vw_receita_mensal ORDER BY ano_mes"),
        columns=["ano_mes", "pedidos", "clientes", "receita"],
    ).astype({"pedidos": int, "clientes": int, "receita": float})
    ouro = ler("kpis_mensais").sort_values("ano_mes").reset_index(drop=True)

    assert list(ouro.ano_mes) == list(pg.ano_mes)
    assert list(ouro.pedidos) == list(pg.pedidos)
    assert list(ouro.clientes) == list(pg.clientes)
    assert ouro.receita.round(2).tolist() == pytest.approx(pg.receita.tolist(), abs=0.01)


@precisa_banco
def test_pedidos_entregues_batem_com_a_visao():
    (n,) = postgres("SELECT COUNT(*) FROM dw.vw_pedidos_entregues")[0]
    assert ler("entrega_por_estado").pedidos.sum() == int(n)


# ------------------------------------------------------------ análises dos achados do relatório
# Controles de cada análise SQL nova contra as tabelas que já foram conferidas.
# Se uma base sair diferente (pedido a mais, avaliado a menos), o erro aparece aqui antes de virar gráfico.

@precisa_banco
def test_analise_07_soma_os_avaliados_das_faixas():
    pg = analise_pg("07_nota_por_dia_atraso.sql")
    assert pg.pedidos.sum() == ler("nota_por_faixa").pedidos.sum()  # 95.560


@precisa_banco
def test_analise_08_soma_os_entregues():
    assert analise_pg("08_entrega_por_regiao.sql").pedidos.sum() == ler("entrega_por_estado").pedidos.sum()  # 96.203


@precisa_banco
def test_analise_09_atrasados_batem_com_o_resumo():
    pg = analise_pg("09_nota_por_regiao_atraso.sql")
    assert pg.pedidos.sum() == 95560
    assert pg[pg.atrasado].pedidos.sum() / pg.pedidos.sum() == pytest.approx(ler("resumo").pct_atrasados.iloc[0])


@precisa_banco
def test_analise_10_nao_passa_dos_pedidos_do_estado():
    # Só pedidos de vendedor único entram. Na exploração, 1.272 de 96.203 entregues tinham mais de um,
    # então cada estado perde pouco. Mais de 3% de perda indica regra de vendedor errada.
    pg = analise_pg("10_atraso_vendedor_destino.sql")
    por_estado = ler("entrega_por_estado").set_index("estado").pedidos
    assert set(pg.estado) == {"RJ", "SP", "MG", "ES"}
    for uf, n in pg.groupby("estado").pedidos.sum().items():
        assert 0.97 * por_estado[uf] <= n <= por_estado[uf]


@precisa_banco
def test_analise_11_pessoas_dentro_do_total():
    pg = analise_pg("11_recompra_primeira_compra.sql")
    assert pg.pessoas.sum() <= ler("resumo").clientes_total.iloc[0]
    assert (pg.voltaram < pg.pessoas).all()


def conferir_com_o_postgres(nome):
    """Compara a tabela da ouro com a análise SQL linha a linha, depois de ordenar os dois lados pelo grão.

    Contagens precisam ser iguais. Percentis e somas aceitam só diferença de arredondamento de ponto flutuante.
    """
    arquivo, grao = TABELAS_DO_RELATORIO[nome]
    ouro = ler(nome).sort_values(grao).reset_index(drop=True)
    pg = analise_pg(arquivo).sort_values(grao).reset_index(drop=True)
    assert list(ouro.columns) == list(pg.columns), "colunas diferentes entre Spark e SQL"
    assert len(ouro) == len(pg), f"{nome}: {len(ouro)} linhas na ouro contra {len(pg)} no Postgres"
    for coluna in ouro.columns:
        if pd.api.types.is_float_dtype(ouro[coluna]) or pd.api.types.is_float_dtype(pg[coluna]):
            assert ouro[coluna].tolist() == pytest.approx(pg[coluna].astype(float).tolist(), abs=1e-9), coluna
        else:
            assert ouro[coluna].tolist() == pg[coluna].tolist(), coluna


@precisa_banco
def test_nota_por_dia_atraso_bate_com_o_postgres():
    conferir_com_o_postgres("nota_por_dia_atraso")


@precisa_banco
def test_entrega_por_regiao_bate_com_o_postgres():
    conferir_com_o_postgres("entrega_por_regiao")


@precisa_banco
def test_nota_por_regiao_atraso_bate_com_o_postgres():
    conferir_com_o_postgres("nota_por_regiao_atraso")


@precisa_banco
def test_atraso_vendedor_destino_bate_com_o_postgres():
    conferir_com_o_postgres("atraso_vendedor_destino")


@precisa_banco
def test_recompra_primeira_compra_bate_com_o_postgres():
    conferir_com_o_postgres("recompra_primeira_compra")
