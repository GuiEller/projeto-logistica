"""Ponto de entrada do painel. Define o menu, a marca e o visual comum. Cada página mora no próprio arquivo."""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Olist Logística", page_icon=":material/local_shipping:", layout="wide")
st.logo(str(Path(__file__).parent / "marca.svg"), size="large")

# CSS mínimo. Limita a largura para a leitura não se espalhar em tela grande, pinta os blocos de branco
# sobre o fundo cinza-azulado e alinha os números em colunas (tabular-nums).
st.html("""
<style>
.block-container { max-width: 1200px; padding-top: 2.5rem; }
[class*="st-key-painel"], [data-testid="stMetric"] { background: #ffffff; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; font-weight: 700; }
[data-testid="stMetricLabel"] p { color: #5f6672; font-size: 0.875rem; }
h1 { letter-spacing: -0.02em; }
</style>
""")

# Menu no topo, com ícones. Com poucas páginas, a barra lateral só ocupava espaço da tela.
st.navigation([
    st.Page("visao_geral.py", title="Visão geral", icon=":material/insights:", default=True),
    st.Page("pages/1_Vendas.py", title="Vendas", icon=":material/payments:"),
    st.Page("pages/2_Logistica.py", title="Logística", icon=":material/local_shipping:"),
    st.Page("pages/3_Cliente.py", title="Cliente", icon=":material/star_half:"),
    st.Page("pages/4_Recomendacoes.py", title="Recomendações", icon=":material/task_alt:"),
    st.Page("pages/5_Relatorio.py", title="Relatório", icon=":material/fact_check:"),
], position="top").run()
