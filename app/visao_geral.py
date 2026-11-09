"""Visão geral. Como o negócio está indo?"""

import altair as alt
import streamlit as st

from dados import AZUL, conclusao, ler, num, pct, reais, resumo, rodape

st.set_page_config(page_title="Olist Logística", layout="wide")

st.title("Olist Logística")
st.markdown(
    "O que mais pesa na satisfação do cliente de um marketplace, e por onde começar a agir? "
    "Cerca de 100 mil pedidos reais da Olist, tratados em PostgreSQL e no Databricks."
)

kpis = ler("kpis_mensais").sort_values("ano_mes")
meses = kpis.ano_mes.tolist()
inicio, fim = st.select_slider("Período", options=meses, value=(meses[0], meses[-1]))
periodo = kpis[(kpis.ano_mes >= inicio) & (kpis.ano_mes <= fim)]

# Variação contra o mês anterior ao último do período. Mostra direção, não só o tamanho.
ultimo = periodo.iloc[-1]
anterior = periodo.iloc[-2] if len(periodo) > 1 else ultimo
variacao = lambda c: pct(ultimo[c] / anterior[c] - 1) if anterior[c] else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Receita no período", reais(periodo.receita.sum()), variacao("receita"))
c2.metric("Pedidos", num(periodo.pedidos.sum()), variacao("pedidos"))
c3.metric("Ticket médio", reais(periodo.receita.sum() / periodo.pedidos.sum(), 2), variacao("ticket_medio"))
# Nota média ponderada pelos pedidos de cada mês, para um mês pequeno não pesar igual a um grande.
nota = (periodo.nota_media * periodo.pedidos).sum() / periodo.pedidos.sum()
dif_nota = round(ultimo.nota_media - anterior.nota_media, 2)
c4.metric("Nota média", num(nota, 2), num(dif_nota, 2) if dif_nota else None)
st.caption(f"Variação de {fim} contra o mês anterior.")

st.subheader("Receita mensal")
grafico = (
    alt.Chart(periodo)
    .mark_line(color=AZUL, strokeWidth=2, point=alt.OverlayMarkDef(size=60, color=AZUL))
    .encode(
        x=alt.X("ano_mes:O", title=None),
        y=alt.Y("receita:Q", title="Receita (R$)", axis=alt.Axis(format="~s")),
        tooltip=[alt.Tooltip("ano_mes", title="Mês"), alt.Tooltip("receita", title="Receita", format=",.0f"),
                 alt.Tooltip("pedidos", title="Pedidos"), alt.Tooltip("nota_media", title="Nota média", format=".2f")],
    )
    .properties(height=320)
)
st.altair_chart(grafico, width="stretch")

r = resumo()
inicio_2017 = kpis.loc[kpis.ano_mes == "2017-01", "receita"].iloc[0]
media_2018 = kpis.loc[kpis.ano_mes.str.startswith("2018"), "receita"].mean()
conclusao(
    f"A receita cresceu {num(media_2018 / inicio_2017, 1)} vezes entre janeiro de 2017 e a média de 2018, "
    f"quando estabilizou perto de {reais(media_2018 / 1000)} mil por mês. O crescimento veio de cliente novo. "
    f"Só {pct(r.pct_recompra)} dos clientes compraram mais de uma vez, e o que mais derruba a nota é a entrega atrasada "
    "(páginas Logística e Cliente)."
)
rodape()
