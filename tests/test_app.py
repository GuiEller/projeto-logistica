"""
Roda cada página do painel sem navegador, com o AppTest do próprio Streamlit.
Pega o erro mais comum de painel, uma página que quebra quando alguém abre,
antes de ir para o ar.
"""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
PAGINAS = ["visao_geral.py"] + sorted(f"pages/{p.name}" for p in (APP / "pages").glob("*.py"))


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_abre_sem_erro(pagina, monkeypatch):
    # As páginas importam "dados" como o Streamlit faz em produção, a partir da pasta app/.
    monkeypatch.syspath_prepend(str(APP))
    at = AppTest.from_file(str(APP / pagina), default_timeout=30).run()
    assert not at.exception, at.exception
    # Toda página termina com a conclusão escrita.
    assert any("Conclusão" in m.value for m in at.markdown)


def test_filtro_de_estado_vazio_nao_quebra(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    at = AppTest.from_file(str(APP / "pages/2_Logistica.py"), default_timeout=30).run()
    at.multiselect[0].set_value([]).run()
    assert not at.exception
    assert at.warning[0].value == "Nenhum estado com esses filtros."


def test_tamanho_amostra_bate_com_a_tabela(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    from dados import tamanho_amostra
    # 50% contra 40%, alfa de 5% e poder de 80% dá 388 por grupo nas tabelas de livro (fórmula de Fleiss sem correção).
    assert tamanho_amostra(0.5, 0.4) == 388
    # Efeito menor pede amostra maior. Se a fórmula inverter o sinal, este teste pega.
    assert tamanho_amostra(0.624, 0.574) > tamanho_amostra(0.624, 0.524)


def test_menu_abre_na_visao_geral(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=30).run()
    assert not at.exception
    # A primeira página abre com a descoberta principal, não com o nome do projeto.
    assert at.title[0].value == "O atraso na entrega é o que mais derruba a nota"


def test_comparar_destinos_filtra_e_pareia(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    from dados import comparar_destinos
    t = pd.DataFrame({
        "vendedor_id": ["a", "a", "b", "b", "c", "c"],
        "estado_vendedor": ["SP", "SP", "SP", "SP", "RJ", "RJ"],
        "estado": ["RJ", "SP"] * 3,
        "pedidos": [20, 20, 30, 30, 5, 40],
        "atrasos": [4, 1, 6, 0, 1, 2],
    })
    r = comparar_destinos(t, "RJ", "SP")
    assert r["vendedores"] == 2                      # c tem só 5 pedidos para o RJ
    assert r["media_a"] == pytest.approx((0.2 + 0.2) / 2)
    assert r["taxa_b"] == pytest.approx(1 / 50)
    assert list(r["pares"].columns) == ["vendedor_id", "taxa_a", "taxa_b"]
    assert comparar_destinos(t, "RJ", "SP", fora_dos_destinos=True)["vendedores"] == 0
    assert comparar_destinos(t, "RJ", "SP", origem="RJ")["vendedores"] == 0
