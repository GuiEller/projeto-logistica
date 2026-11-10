"""Visão geral. A descoberta principal do projeto, em uma tela."""

import altair as alt
import streamlit as st

from dados import AZUL, DESTAQUE, conclusao, desenhar, ler, mapa_atraso, num, painel, pct, ponderada, resumo, rodape

st.title("O atraso na entrega é o que mais derruba a nota")
st.markdown("Cerca de 100 mil pedidos reais da Olist, de janeiro de 2017 a agosto de 2018, "
            "tratados em PostgreSQL e no Databricks.")

r = resumo()
faixas = ler("nota_por_faixa").sort_values("faixa_atraso")
# O prefixo "1. ", "2. " existe só para ordenar. Na tela, sai.
faixas["situacao"] = faixas.faixa_atraso.str.split(". ", n=1).str[1]
faixas["atrasado"] = faixas.faixa_atraso.str[0].astype(int) >= 3
nota_prazo = ponderada(faixas[~faixas.atrasado], "nota_media")
nota_atraso = ponderada(faixas[faixas.atrasado], "nota_media")

c1, c2, c3, c4 = st.columns(4)
# height="stretch" deixa os quatro cartões da mesma altura, mesmo quando só um tem a linha de variação.
kpi = dict(border=True, height="stretch")
c1.metric("Pedidos que chegaram atrasados", pct(r.pct_atrasados), **kpi)
c2.metric("Notas 1 e 2 que vêm de atraso", pct(r.parcela_notas_baixas_atraso), **kpi)
c3.metric("Nota média com atraso", num(nota_atraso, 2),
          f"-{num(nota_prazo - nota_atraso, 2)} contra {num(nota_prazo, 2)} no prazo", **kpi)
c4.metric("Clientes que voltaram a comprar", pct(r.pct_recompra), **kpi)

esq, dir = st.columns([5, 4])
with esq:
    with painel("A nota cai a cada faixa de atraso", "faixas",
                "Nota média dos pedidos entregues, da entrega antecipada ao atraso de mais de 7 dias."):
        # Barras deitadas porque os nomes das faixas são longos. Em pé, os rótulos se atropelavam.
        base = alt.Chart(faixas).encode(
            y=alt.Y("situacao:N", sort=None, title=None, axis=alt.Axis(labelLimit=200, labelFontSize=13)),
            x=alt.X("nota_media:Q", title="Nota média", scale=alt.Scale(domain=[0, 5]),
                    axis=alt.Axis(format=".0f", tickCount=5)),
            tooltip=[alt.Tooltip("situacao", title="Situação"), alt.Tooltip("pedidos", title="Pedidos", format=","),
                     alt.Tooltip("nota_media", title="Nota média", format=".2f"),
                     alt.Tooltip("pct_nota_baixa", title="Nota 1 ou 2", format=".1%")],
        )
        barras = base.mark_bar(cornerRadiusEnd=4, size=34).encode(
            color=alt.condition("datum.atrasado", alt.value(DESTAQUE), alt.value(AZUL)))
        valores = base.mark_text(align="left", dx=6, fontSize=14, fontWeight=700, color="#0a0a0a").encode(
            text=alt.Text("nota_media:Q", format=".2f"))
        desenhar((barras + valores).properties(height=300))
        st.caption("Azul chegou no prazo, laranja chegou atrasado.")
with dir:
    with painel("Onde o atraso acontece", "mapa",
                "Parcela dos pedidos de cada estado entregue depois da data prometida."):
        desenhar(mapa_atraso(ler("entrega_por_estado"), altura=380))

estados = ler("entrega_por_estado")
nordeste = ponderada(estados[estados.regiao == "Nordeste"], "taxa_atraso")
conclusao(
    f"Só {pct(r.pct_atrasados)} dos pedidos atrasam, mas eles respondem por {pct(r.parcela_notas_baixas_atraso)} "
    f"de todas as notas 1 e 2. A nota média cai de {num(nota_prazo, 2)} para {num(nota_atraso, 2)} quando o pedido "
    f"atrasa. O Nordeste atrasa {pct(nordeste)} das entregas, quase o dobro da média, e o RJ junta muito volume "
    "com atraso alto. As páginas seguintes mostram onde agir primeiro."
)
rodape()
