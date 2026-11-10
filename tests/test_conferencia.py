"""
Conferência da camada ouro (Parquet exportado do Databricks) contra o PostgreSQL.

Duas fontes que deveriam ser iguais e não foram conferidas são duas fontes de erro.
Os testes que precisam do banco consultam o container olist-db. Sem o container
(por exemplo, no job de pytest do CI, que não sobe banco), eles são pulados.
O job do pipeline SQL sobe o banco e roda esta conferência.
"""

import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

DADOS = Path(__file__).resolve().parents[1] / "app" / "data"


def ler(nome):
    return pd.read_parquet(DADOS / f"{nome}.parquet")


def postgres(sql):
    """Roda uma consulta no container e devolve as linhas como listas de texto."""
    saida = subprocess.run(
        ["docker", "exec", "olist-db", "psql", "-U", "postgres", "-d", "olist", "-At", "-F", "|", "-c", sql],
        capture_output=True, text=True, check=True,
    ).stdout
    return [linha.split("|") for linha in saida.strip().splitlines()]


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
    for nome in ["kpis_mensais", "categorias_abc", "entrega_por_estado", "nota_por_faixa", "resumo"]:
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
