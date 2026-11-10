"""Logística. Onde a entrega falha?"""

import altair as alt
import streamlit as st

from dados import AZUL, DESTAQUE, conclusao, ler, num, pct, rodape

st.set_page_config(page_title="Logística | Olist Logística", layout="wide")
st.title("Onde a entrega falha?")

estados = ler("entrega_por_estado")
f1, f2 = st.columns(2)
regioes = f1.multiselect("Regiões", sorted(estados.regiao.unique()), default=sorted(estados.regiao.unique()))
# Estado com poucos pedidos tem taxa instável. 300 é o mesmo corte da análise SQL 06.
minimo = f2.slider("Mínimo de pedidos por estado", 0, 2000, 300, step=50)
filtro = estados[estados.regiao.isin(regioes) & (estados.pedidos >= minimo)].copy()

if filtro.empty:
    st.warning("Nenhum estado com esses filtros.")
    st.stop()

pior = filtro.sort_values("taxa_atraso", ascending=False).iloc[0]
filtro["destaque"] = filtro.estado == pior.estado

st.subheader("Taxa de atraso por estado")
grafico = (
    alt.Chart(filtro)
    .mark_bar(cornerRadiusEnd=4)
    .encode(
        y=alt.Y("estado:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False)),
        x=alt.X("taxa_atraso:Q", title="Pedidos entregues depois do prazo", axis=alt.Axis(format="%", tickCount=6)),
        color=alt.condition("datum.destaque", alt.value(DESTAQUE), alt.value(AZUL)),
        tooltip=[alt.Tooltip("estado", title="Estado"), alt.Tooltip("regiao", title="Região"),
                 alt.Tooltip("pedidos", title="Pedidos", format=","), alt.Tooltip("taxa_atraso", title="Atraso", format=".1%"),
                 alt.Tooltip("entrega_media", title="Entrega média (dias)", format=".1f"),
                 alt.Tooltip("prazo_medio", title="Prazo prometido (dias)", format=".1f"),
                 alt.Tooltip("nota_media", title="Nota média", format=".2f")],
    )
    .properties(height=max(260, 26 * len(filtro)))
)
st.altair_chart(grafico, width="stretch")

# Agregar por região exige média ponderada pelos pedidos. Média simples das taxas daria o mesmo peso a RR e SP.
pond = lambda g, c: (g[c] * g.pedidos).sum() / g.pedidos.sum()
MEDIAS = ["prazo_medio", "entrega_media", "frete_medio"]
por_regiao = filtro[MEDIAS].mul(filtro.pedidos, axis=0).assign(regiao=filtro.regiao, pedidos=filtro.pedidos)
por_regiao = por_regiao.groupby("regiao").sum()
por_regiao[MEDIAS] = por_regiao[MEDIAS].div(por_regiao.pedidos, axis=0)
por_regiao = por_regiao.assign(folga=por_regiao.prazo_medio - por_regiao.entrega_media).reset_index()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Folga entre prometido e real")
    st.caption("Dias que o pedido chega, em média, antes da data prometida.")
    st.altair_chart(
        alt.Chart(por_regiao).mark_bar(color=AZUL, cornerRadiusEnd=4).encode(
            y=alt.Y("regiao:N", sort="-x", title=None), x=alt.X("folga:Q", title="Dias de folga"),
            tooltip=[alt.Tooltip("regiao", title="Região"), alt.Tooltip("folga", title="Folga (dias)", format=".1f")],
        ).properties(height=220),
        width="stretch",
    )
with c2:
    st.subheader("Frete médio por pedido")
    st.caption("Valor do frete somado por pedido, em reais.")
    st.altair_chart(
        alt.Chart(por_regiao).mark_bar(color=AZUL, cornerRadiusEnd=4).encode(
            y=alt.Y("regiao:N", sort="-x", title=None), x=alt.X("frete_medio:Q", title="Frete médio (R$)"),
            tooltip=[alt.Tooltip("regiao", title="Região"), alt.Tooltip("frete_medio", title="Frete (R$)", format=".2f")],
        ).properties(height=220),
        width="stretch",
    )

# Participação do RJ nos pedidos e nos atrasos, sempre sobre a base inteira, independente do filtro.
estados["atrasos"] = estados.pedidos * estados.taxa_atraso
rj = estados[estados.estado == "RJ"].iloc[0]
sp = estados[estados.estado == "SP"].iloc[0]
folga_geral = pond(estados, "prazo_medio") - pond(estados, "entrega_media")
conclusao(
    f"O RJ tem {pct(rj.pedidos / estados.pedidos.sum())} dos pedidos e {pct(rj.atrasos / estados.atrasos.sum())} dos atrasos. "
    f"Nos filtros atuais, o pior estado é {pior.estado}, com {pct(pior.taxa_atraso)} de atraso contra {pct(sp.taxa_atraso)} em SP. "
    f"Ao mesmo tempo, o pedido médio chega {num(folga_geral, 1)} dias antes do prometido. "
    "O prazo nacional é folgado demais onde a entrega é rápida e apertado onde ela é lenta."
)
rodape()
