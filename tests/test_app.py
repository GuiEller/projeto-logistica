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


def test_relatorio_mantem_os_numeros_do_ab(monkeypatch):
    # Protege os números enquanto os gráficos da página mudam. Queda padrão de 5 pontos.
    monkeypatch.syspath_prepend(str(APP))
    at = AppTest.from_file(str(APP / "pages/5_Relatorio.py"), default_timeout=30).run()
    assert not at.exception
    cartoes = {m.label: m.value for m in at.metric}
    assert cartoes["Meses de coleta"] == "5,8"
    assert cartoes["Pedidos atrasados por grupo"] == "1.507"


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


def test_logistica_cita_os_vendedores_da_comparacao(monkeypatch):
    # O número do texto precisa sair da mesma função que o relatório usa, não de uma conta à parte.
    monkeypatch.syspath_prepend(str(APP))
    from dados import comparar_destinos, ler
    n = comparar_destinos(ler("atraso_vendedor_destino"), "RJ", "SP")["vendedores"]
    at = AppTest.from_file(str(APP / "pages/2_Logistica.py"), default_timeout=30).run()
    assert not at.exception
    assert any(f"{n} vendedores" in c.value for c in at.caption)


# ------------------------------------------------------------ filtros por clique
# Cada página abre com estado, mês, faixa e dia escolhidos, inclusive valores que não existem mais
# (um filtro guardado de outra sessão). Clique nenhum pode quebrar uma página.
FILTROS = [
    {"filtro_uf": "AL"},
    {"filtro_uf": "RR"},  # 40 pedidos, testa grupo vazio e amostra pequena
    {"filtro_uf": "SP", "filtro_faixa": "3. 1 a 3 dias de atraso", "filtro_mes": "2018-03", "filtro_dia": 2},
    {"filtro_faixa": "faixa velha", "filtro_mes": "1999-01", "filtro_dia": 999},
]


@pytest.mark.parametrize("filtros", FILTROS, ids=["AL", "RR", "SP-com-tudo", "valores-velhos"])
@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_abre_com_filtros(pagina, filtros, monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    at = AppTest.from_file(str(APP / pagina), default_timeout=30)
    for chave, valor in filtros.items():
        at.session_state[chave] = valor
    at.run()
    assert not at.exception, at.exception


def test_visao_geral_sem_filtro_bate_com_o_resumo(monkeypatch):
    # Os cartões agora somam a tabela por estado. Sem filtro, precisam dar os números do Brasil já conferidos.
    monkeypatch.syspath_prepend(str(APP))
    from dados import pct, resumo
    r = resumo()
    valores = [m.value for m in AppTest.from_file(str(APP / "visao_geral.py"), default_timeout=30).run().metric]
    assert valores[0] == pct(r.pct_atrasados)
    assert valores[1] == pct(r.parcela_notas_baixas_atraso)
    assert valores[3] == pct(r.pct_recompra)
