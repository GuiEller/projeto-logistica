"""Visão geral. A descoberta principal do projeto, em uma tela."""

import altair as alt
import streamlit as st

from dados import (AZUL, DESTAQUE, barra_de_filtro, conclusao, desenhar_clicavel, faixas_do_estado, ler, mapa_atraso,
                   num, painel, pct, razao, rodape)

st.title("O atraso na entrega é o que mais derruba a nota")
st.markdown("Cerca de 100 mil pedidos reais da Olist, de janeiro de 2017 a agosto de 2018, "
            "tratados em PostgreSQL e no Databricks.")

# Cartões, faixas e mapa saem da mesma tabela por estado. Com ou sem filtro, cada número aparece com um valor só.
por_estado = ler("faixa_por_estado")
uf = barra_de_filtro(por_estado.groupby("estado").pedidos.sum(), "pedidos entregues e avaliados")
faixas = faixas_do_estado(uf)
atrasados, no_prazo = faixas[faixas.atrasado], faixas[~faixas.atrasado]
pct_atrasados = razao(atrasados.pedidos.sum(), faixas.pedidos.sum())
parcela_notas_baixas = razao(atrasados.notas_baixas.sum(), faixas.notas_baixas.sum())
nota_prazo = razao(no_prazo.soma_notas.sum(), no_prazo.pedidos.sum())
nota_atraso = razao(atrasados.soma_notas.sum(), atrasados.pedidos.sum())
recompra = ler("recompra_por_estado")
recompra = recompra[recompra.estado == uf] if uf else recompra
pct_recompra = razao(recompra.voltaram.sum(), recompra.clientes.sum())

onde = f" em {uf}" if uf else ""
# O estado escolhido fica na barra de filtro. No rótulo do cartão ele cortaria o texto.
c1, c2, c3, c4 = st.columns(4)
# height="stretch" deixa os quatro cartões da mesma altura, mesmo quando só um tem a linha de variação.
kpi = dict(border=True, height="stretch")
c1.metric("Pedidos que chegaram atrasados", pct(pct_atrasados), **kpi)
c2.metric("Notas 1 e 2 que vêm de atraso", pct(parcela_notas_baixas), **kpi)
c3.metric("Nota média com atraso", num(nota_atraso, 2),
          f"-{num(nota_prazo - nota_atraso, 2)} contra {num(nota_prazo, 2)} no prazo", **kpi)
c4.metric("Clientes que voltaram a comprar", pct(pct_recompra), **kpi)

# Faixa escolhida com clique nas barras. Ela pinta o mapa pela parte dos pedidos de cada estado naquela faixa.
faixa = st.session_state.get("filtro_faixa")
if faixa not in set(faixas.faixa_atraso):
    faixa = None

esq, dir = st.columns([5, 4])
with esq:
    with painel("A nota cai a cada faixa de atraso", "faixas",
                f"Nota média dos pedidos entregues{onde}, da entrega antecipada ao atraso de mais de 7 dias. "
                "Clique numa faixa para ver no mapa onde ela acontece."):
        # Barras deitadas porque os nomes das faixas são longos. Em pé, os rótulos se atropelavam.
        clique = alt.selection_point(name="faixa", fields=["faixa_atraso"], on="click")
        base = alt.Chart(faixas).encode(
            y=alt.Y("situacao:N", sort=None, title=None, axis=alt.Axis(labelLimit=200, labelFontSize=13)),
            x=alt.X("nota_media:Q", title="Nota média", scale=alt.Scale(domain=[0, 5]),
                    axis=alt.Axis(format=".0f", tickCount=5)),
            tooltip=[alt.Tooltip("situacao", title="Situação"), alt.Tooltip("pedidos", title="Pedidos", format=","),
                     alt.Tooltip("nota_media", title="Nota média", format=".2f"),
                     alt.Tooltip("pct_nota_baixa", title="Nota 1 ou 2", format=".1%")],
        )
        barras = base.mark_bar(cornerRadiusEnd=4, size=34, cursor="pointer").encode(
            color=alt.condition("datum.atrasado", alt.value(DESTAQUE), alt.value(AZUL)),
            # A faixa escolhida fica cheia e as outras apagadas, o mesmo sinal do mapa.
            opacity=alt.condition(f"datum.faixa_atraso == '{faixa}'" if faixa else "true",
                                  alt.value(1), alt.value(0.3)),
        ).add_params(clique)
        valores = base.mark_text(align="left", dx=6, fontSize=14, fontWeight=700, color="#0a0a0a").encode(
            text=alt.Text("nota_media:Q", format=".2f"))
        chave = f"faixas-{uf}-{faixa}"

        def ao_clicar_na_faixa():
            marcadas = st.session_state[chave].selection.get("faixa", [])
            st.session_state["filtro_faixa"] = marcadas[0]["faixa_atraso"] if marcadas else None

        st.altair_chart((barras + valores).properties(height=300), width="stretch", theme=None, key=chave,
                        on_select=ao_clicar_na_faixa, selection_mode="faixa")
        if faixa:
            st.button("Ver todas as faixas", on_click=lambda: st.session_state.update(filtro_faixa=None))
        else:
            st.caption("Azul chegou no prazo, laranja chegou atrasado.")

with dir:
    # Taxa de cada estado sobre os pedidos entregues e avaliados, a mesma base dos cartões acima.
    total = por_estado.groupby("estado").pedidos.sum()
    if faixa:
        situacao = faixas.set_index("faixa_atraso").situacao[faixa]
        parte = por_estado[por_estado.faixa_atraso == faixa].groupby("estado").pedidos.sum()
        titulo, descricao = f"Pedidos na faixa {situacao}", f"Parcela dos pedidos de cada estado na faixa {situacao}."
    else:
        parte = por_estado[por_estado.faixa_atraso.str[0].astype(int) >= 3].groupby("estado").pedidos.sum()
        titulo, descricao = ("Pedidos entregues depois do prazo",
                             "Parcela dos pedidos de cada estado entregue depois da data prometida. "
                             "Clique num estado para filtrar a página.")
    mapa = total.rename("pedidos").to_frame().assign(taxa=(parte / total).fillna(0)).reset_index()
    with painel("Onde o atraso acontece", "mapa", descricao):
        desenhar_clicavel(mapa_atraso(mapa, altura=380, uf=uf, campo="taxa", titulo=titulo), "mapa-visao")

if uf:
    brasil = faixas_do_estado(None)
    atraso_brasil = razao(brasil[brasil.atrasado].pedidos.sum(), brasil.pedidos.sum())
    conclusao(
        f"Em {uf}, {pct(pct_atrasados)} dos pedidos atrasam, contra {pct(atraso_brasil)} no Brasil inteiro, e eles "
        f"respondem por {pct(parcela_notas_baixas)} das notas 1 e 2. A nota média cai de {num(nota_prazo, 2)} no prazo "
        f"para {num(nota_atraso, 2)} com atraso."
    )
else:
    estados = ler("entrega_por_estado")
    nordeste = (estados.pedidos * estados.taxa_atraso)[estados.regiao == "Nordeste"].sum() / \
        estados.pedidos[estados.regiao == "Nordeste"].sum()
    conclusao(
        f"Só {pct(pct_atrasados)} dos pedidos atrasam, mas eles respondem por {pct(parcela_notas_baixas)} "
        f"de todas as notas 1 e 2. A nota média cai de {num(nota_prazo, 2)} para {num(nota_atraso, 2)} quando o pedido "
        f"atrasa. O Nordeste atrasa {pct(nordeste)} das entregas, quase o dobro da média, e o RJ junta muito volume "
        "com atraso alto. No RJ o problema é o caminho até o cliente, porque o mesmo vendedor atrasa bem menos para SP. "
        "As páginas seguintes mostram onde agir primeiro."
    )
rodape()
