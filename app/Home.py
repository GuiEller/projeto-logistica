"""Ponto de entrada do painel. Só define o menu, cada página mora no próprio arquivo."""

import streamlit as st

# st.navigation dá título com acento a cada página. Sem ele, o menu mostraria o nome do arquivo.
st.navigation([
    st.Page("visao_geral.py", title="Visão geral", default=True),
    st.Page("pages/1_Vendas.py", title="Vendas"),
    st.Page("pages/2_Logistica.py", title="Logística"),
    st.Page("pages/3_Cliente.py", title="Cliente"),
    st.Page("pages/4_Recomendacoes.py", title="Recomendações"),
]).run()
