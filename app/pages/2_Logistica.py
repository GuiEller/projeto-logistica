"""Logística. Onde a entrega falha?"""

import altair as alt
import pandas as pd
import streamlit as st

from dados import (AZUL, DESTAQUE, conclusao, desenhar, ler, mapa_atraso, num, painel, pct, ponderada, rodape)

st.title("Onde a entrega falha?")

estados = ler("entrega_por_estado")
estados["atrasos"] = estados.pedidos * estados.taxa_atraso
f1, f2 = st.columns(2)
regioes = f1.multiselect("Regiões", sorted(estados.regiao.unique()), default=sorted(estados.regiao.unique()))
# Estado com poucos pedidos tem taxa instável. 300 é o mesmo corte da análise SQL 06.
minimo = f2.slider("Mínimo de pedidos por estado", 0, 2000, 300, step=50)
filtro = estados[estados.regiao.isin(regioes) & (estados.pedidos >= minimo)].copy()

if filtro.empty:
    st.warning("Nenhum estado com esses filtros.")
    st.stop()

pior = filtro.sort_values("taxa_atraso", ascending=False).iloc[0]
rj = estados[estados.estado == "RJ"].iloc[0]
sp = estados[estados.estado == "SP"].iloc[0]
# O RJ é o destaque porque é onde a recomendação manda agir. AL atrasa mais, mas tem 30 vezes menos pedidos.
filtro["destaque"] = filtro.estado == "RJ"

mapa, ranking = st.columns([4, 3])
with mapa:
    with painel("Atraso por estado", "mapa-logistica",
                "Parcela dos pedidos entregue depois da data prometida. Cinza é estado fora do filtro."):
        desenhar(mapa_atraso(filtro, altura=460))
with ranking:
    parte_rj = (f"Laranja marca o RJ, com {pct(rj.pedidos / estados.pedidos.sum())} dos pedidos "
                f"e {pct(rj.atrasos / estados.atrasos.sum())} dos atrasos.")
    with painel("Ranking do atraso", "ranking", parte_rj):
        base = alt.Chart(filtro).encode(
            y=alt.Y("estado:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False)),
            x=alt.X("taxa_atraso:Q", title=None, axis=alt.Axis(format=".0%", tickCount=4)),
            tooltip=[alt.Tooltip("estado", title="Estado"), alt.Tooltip("regiao", title="Região"),
                     alt.Tooltip("pedidos", title="Pedidos", format=","),
                     alt.Tooltip("taxa_atraso", title="Atraso", format=".1%"),
                     alt.Tooltip("entrega_media", title="Entrega média (dias)", format=".1f"),
                     alt.Tooltip("prazo_medio", title="Prazo prometido (dias)", format=".1f"),
                     alt.Tooltip("nota_media", title="Nota média", format=".2f")],
        )
        barras = base.mark_bar(cornerRadiusEnd=4).encode(
            color=alt.condition("datum.destaque", alt.value(DESTAQUE), alt.value(AZUL)))
        valores = base.mark_text(align="left", dx=4, fontSize=11, color="#5f6672").encode(
            text=alt.Text("taxa_atraso:Q", format=".1%"))
        desenhar((barras + valores).properties(height=max(260, 20 * len(filtro))))

# Agregar por região exige média ponderada pelos pedidos. Média simples das taxas daria o mesmo peso a RR e SP.
MEDIAS = ["prazo_medio", "entrega_media", "frete_medio"]
por_regiao = (filtro.groupby("regiao")
              .apply(lambda g: pd.Series({c: ponderada(g, c) for c in MEDIAS}), include_groups=False)
              .reset_index())
por_regiao["folga"] = por_regiao.prazo_medio - por_regiao.entrega_media


def barras_regiao(coluna, titulo_eixo, formato, dica):
    return (
        alt.Chart(por_regiao).mark_bar(color=AZUL, cornerRadiusEnd=4, size=26).encode(
            y=alt.Y("regiao:N", sort="-x", title=None),
            x=alt.X(f"{coluna}:Q", title=titulo_eixo, axis=alt.Axis(tickCount=4, format=formato)),
            tooltip=[alt.Tooltip("regiao", title="Região"), alt.Tooltip(coluna, title=dica, format=".1f")],
        ).properties(height=220)
    )


c1, c2 = st.columns(2)
with c1:
    with painel("Folga entre prometido e real", "folga", "Dias que o pedido chega, em média, antes da data prometida."):
        desenhar(barras_regiao("folga", "Dias de folga", "d", "Folga (dias)"))
with c2:
    with painel("Frete médio por pedido", "frete", "Valor do frete somado por pedido, em reais."):
        desenhar(barras_regiao("frete_medio", "Frete médio", "$,.0f", "Frete (R$)"))

folga_geral = ponderada(estados, "prazo_medio") - ponderada(estados, "entrega_media")
conclusao(
    f"O RJ tem {pct(rj.pedidos / estados.pedidos.sum())} dos pedidos e {pct(rj.atrasos / estados.atrasos.sum())} dos atrasos. "
    f"Nos filtros atuais, o pior estado é {pior.estado}, com {pct(pior.taxa_atraso)} de atraso contra {pct(sp.taxa_atraso)} em SP. "
    f"Ao mesmo tempo, o pedido médio chega {num(folga_geral, 1)} dias antes do prometido. "
    "O prazo nacional é folgado demais onde a entrega é rápida e apertado onde ela é lenta."
)
rodape()
