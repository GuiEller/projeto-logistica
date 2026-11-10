"""Ponto de entrada do painel. Define o menu, a marca e o visual comum. Cada página mora no próprio arquivo."""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Olist Logística", page_icon=":material/local_shipping:", layout="wide")
st.logo(str(Path(__file__).parent / "marca.svg"), size="large")

# Todo o visual (moldura, folha, tipografia, faixa de indicadores) mora em estilo.css, num arquivo só.
# As páginas não repetem estilo. O Streamlit reinjeta o CSS a cada execução, então ele vale em todas elas.
st.html(f"<style>{(Path(__file__).parent / 'estilo.css').read_text(encoding='utf-8')}</style>")

# Menu no topo, com ícones. Com poucas páginas, a barra lateral só ocupava espaço da tela.
st.navigation([
    st.Page("visao_geral.py", title="Visão geral", icon=":material/insights:", default=True),
    st.Page("pages/1_Vendas.py", title="Vendas", icon=":material/payments:"),
    st.Page("pages/2_Logistica.py", title="Logística", icon=":material/local_shipping:"),
    st.Page("pages/3_Cliente.py", title="Cliente", icon=":material/star_half:"),
    st.Page("pages/4_Recomendacoes.py", title="Recomendações", icon=":material/task_alt:"),
    st.Page("pages/5_Relatorio.py", title="Relatório", icon=":material/fact_check:"),
], position="top").run()
