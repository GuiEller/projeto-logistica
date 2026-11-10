"""Vendas. De onde vem a receita?"""

import altair as alt
import streamlit as st

from dados import AZUL, NEUTRO, conclusao, ler, num, pct, reais, resumo, rodape

st.set_page_config(page_title="Vendas | Olist Logística", layout="wide")
st.title("De onde vem a receita?")

abc = ler("categorias_abc").sort_values("ranking")
classe_a = abc[abc.classe_abc == "A"]

c1, c2, c3 = st.columns(3)
c1.metric("Categorias com venda", num(len(abc)))
c2.metric("Categorias na classe A", num(len(classe_a)), f"{pct(classe_a.participacao.sum())} da receita", delta_color="off")
c3.metric("Clientes que voltaram a comprar", pct(resumo().pct_recompra))

st.subheader("Curva ABC das categorias")
st.caption("Classe A soma até 80% da receita acumulada, B vai de 80% a 95% e C é o restante.")
mostrar = st.slider("Categorias no gráfico", 10, len(abc), 25)
grafico = (
    alt.Chart(abc.head(mostrar))
    .mark_bar(cornerRadiusEnd=4)
    .encode(
        y=alt.Y("categoria_en:N", sort=None, title=None, axis=alt.Axis(labelOverlap=False)),
        x=alt.X("receita:Q", title="Receita (R$)", axis=alt.Axis(format="~s")),
        # Cor por classe, mas só a A ganha cor. O olho vai direto para o que concentra a receita.
        color=alt.Color("classe_abc:N", scale=alt.Scale(domain=["A", "B", "C"], range=[AZUL, NEUTRO, "#dcdad3"]),
                        legend=alt.Legend(title="Classe", orient="top")),
        tooltip=[alt.Tooltip("categoria_en", title="Categoria"), alt.Tooltip("receita", title="Receita", format=",.0f"),
                 alt.Tooltip("participacao", title="Participação", format=".1%"),
                 alt.Tooltip("acumulado", title="Acumulado", format=".1%"), alt.Tooltip("classe_abc", title="Classe")],
    )
    .properties(height=max(300, 24 * mostrar))
)
st.altair_chart(grafico, width="stretch")

with st.expander("Tabela completa"):
    st.dataframe(abc[["ranking", "categoria_en", "receita", "itens", "participacao", "acumulado", "classe_abc"]],
                 hide_index=True, width="stretch")

conclusao(
    f"{len(classe_a)} de {len(abc)} categorias somam {pct(classe_a.participacao.sum())} da receita, "
    f"com {classe_a.categoria_en.iloc[0].replace('_', ' ')} na frente com {reais(classe_a.receita.iloc[0] / 1e6, 2)} milhões. "
    f"O ponto fraco é a recompra. Só {pct(resumo().pct_recompra)} dos clientes voltaram, então quase toda venda depende de trazer cliente novo."
)
rodape()
