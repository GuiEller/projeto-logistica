"""
Testes da lógica do teste de hipótese, com dados pequenos e conhecidos.

A ideia é que cada teste quebre se uma regra mudar sem querer. Por exemplo, se
alguém trocar o "alternative" do Mann-Whitney, o sinal do efeito inverte e o
teste de direção falha na hora.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analise"))
import teste_hipotese as th  # noqa: E402


@pytest.fixture
def base():
    # 10 pedidos no prazo com nota alta e 4 atrasados com nota baixa.
    # O Postgres exporta booleano como "t" e "f", por isso o CSV de teste usa o mesmo formato.
    linhas = [("t", 5)] * 6 + [("t", 4)] * 3 + [("t", 1)] + [("f", 1)] * 3 + [("f", 4)]
    return pd.DataFrame(linhas, columns=["entregue_no_prazo", "nota_avaliacao"])


def test_formato_brasileiro():
    assert th.br(13591643.7) == "13.591.643,70"
    assert th.br(0.5, 1) == "0,5"


def test_carregar_converte_booleano_do_postgres_e_descarta_nulos(tmp_path, base):
    # Uma linha sem nota não pode entrar no teste. Sem avaliação não há o que comparar.
    com_nulo = pd.concat([base, pd.DataFrame([{"entregue_no_prazo": "t", "nota_avaliacao": None}])])
    arquivo = tmp_path / "pedidos.csv"
    com_nulo.to_csv(arquivo, index=False)

    df = th.carregar(arquivo)

    assert len(df) == len(base)
    assert df["atrasado"].sum() == 4
    assert df["nota_baixa"].sum() == 4  # três atrasados e um no prazo com nota 1


def test_mann_whitney_aponta_atrasados_com_nota_menor(tmp_path, base):
    arquivo = tmp_path / "pedidos.csv"
    base.to_csv(arquivo, index=False)
    r = th.teste_mann_whitney(th.carregar(arquivo))

    assert r["n_atrasados"] == 4 and r["n_no_prazo"] == 10
    assert r["media_atrasados"] < r["media_no_prazo"]
    # Pela convenção do script, efeito negativo quer dizer atrasados com notas menores
    # (o relatório mostra o valor absoluto). Se o sinal inverter, a leitura inverte junto.
    assert r["rank_biserial"] == pytest.approx(-0.8)
    assert r["p"] < 0.05


def test_proporcoes_e_parcela_das_notas_baixas(tmp_path, base):
    arquivo = tmp_path / "pedidos.csv"
    base.to_csv(arquivo, index=False)
    r = th.teste_proporcoes(th.carregar(arquivo))

    assert r["p_atr"] == pytest.approx(3 / 4)
    assert r["p_ok"] == pytest.approx(1 / 10)
    assert r["risco_relativo"] == pytest.approx(7.5)
    # De 4 notas baixas, 3 vieram de atrasados. É o número que vira manchete no README.
    assert r["parcela_notas_baixas_atraso"] == pytest.approx(3 / 4)
    assert r["ic"][0] < r["dif"] < r["ic"][1]
