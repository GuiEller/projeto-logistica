"""Leitura dos Parquet da camada ouro e formatação no padrão brasileiro, usadas por todas as páginas."""

from pathlib import Path

import pandas as pd
import streamlit as st

DADOS = Path(__file__).parent / "data"
AZUL = "#2a78d6"      # cor única das séries
DESTAQUE = "#eb6834"  # o que a conclusão da página aponta
NEUTRO = "#b8b6ae"


@st.cache_data
def ler(nome: str) -> pd.DataFrame:
    # cache_data guarda o resultado na memória. Sem ele, cada clique num filtro releria o arquivo do disco.
    return pd.read_parquet(DADOS / f"{nome}.parquet")


def resumo() -> pd.Series:
    return ler("resumo").iloc[0]


def num(x, casas=0):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, casas=1):
    return num(100 * x, casas) + "%"


def reais(x, casas=0):
    return "R$ " + num(x, casas)


def conclusao(texto: str):
    # Toda página termina com a conclusão escrita. Gráfico sem conclusão obriga o leitor a fazer a análise.
    st.divider()
    st.markdown(f"**Conclusão.** {texto}")


def rodape():
    st.caption("Base pública da Olist, pedidos de 01/2017 a 08/2018. Camada ouro processada no Databricks.")
