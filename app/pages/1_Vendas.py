"""Vendas. Como a receita evoluiu e de onde ela vem?"""

import altair as alt
import pandas as pd
import streamlit as st

from dados import (AZUL, NEUTRO, NEUTRO_CLARO, categoria_br, conclusao, desenhar, eixo_reais_mi, estado_escolhido,
                   ler, mes_br, num, painel, pct, ponderada, reais, resumo, rodape)

st.title("De onde vem a receita?")
if estado_escolhido():
    st.caption(f"Esta página é do Brasil inteiro, mesmo com {estado_escolhido()} escolhido. "
               "A receita não está separada por estado na camada ouro.")

kpis = ler("kpis_mensais").sort_values("ano_mes")
meses = kpis.ano_mes.tolist()
inicio, fim = st.select_slider("Período", options=meses, value=(meses[0], meses[-1]), format_func=mes_br)
periodo = kpis[(kpis.ano_mes >= inicio) & (kpis.ano_mes <= fim)].assign(mes=lambda d: pd.to_datetime(d.ano_mes))

# Mês clicado no gráfico. Fora do período escolhido no controle acima, ele é ignorado.
mes = st.session_state.get("filtro_mes")
mes = mes if mes in set(periodo.ano_mes) else None
cartoes = periodo[periodo.ano_mes == mes] if mes else periodo
quando = f"em {mes_br(mes)}" if mes else "no período"

# Sem variação contra o mês anterior. Em agosto de 2018 ela mostrava -3,3% em vermelho, ruído de um mês só.
kpi = dict(border=True, height="stretch")
c1, c2, c3, c4 = st.columns(4)
# Em milhões, porque R$ 13.449.530 não cabe no cartão e ninguém lê os últimos dígitos.
c1.metric(f"Receita {quando}", f"{reais(cartoes.receita.sum() / 1e6, 2 if mes else 1)} mi", **kpi)
c2.metric(f"Pedidos {quando}", num(cartoes.pedidos.sum()), **kpi)
c3.metric("Ticket médio", reais(cartoes.receita.sum() / cartoes.pedidos.sum(), 2), **kpi)
# Nota média ponderada pelos pedidos de cada mês, para um mês pequeno não pesar igual a um grande.
c4.metric("Nota média", num(ponderada(cartoes, "nota_media"), 2), **kpi)

with painel("Receita mensal", "receita", f"Soma do valor dos itens vendidos, de {mes_br(inicio)} a {mes_br(fim)}. "
            "Clique num mês para ver os números dele nos cartões."):
    linha = alt.Chart(periodo).encode(
        x=alt.X("mes:T", title=None, axis=alt.Axis(format="%b/%y", labelAngle=0, tickCount="month", labelOverlap=True)),
        y=alt.Y("receita:Q", axis=eixo_reais_mi()),
        tooltip=[alt.Tooltip("mes:T", title="Mês", format="%B de %Y"),
                 alt.Tooltip("receita:Q", title="Receita", format="$,.0f"),
                 alt.Tooltip("pedidos:Q", title="Pedidos", format=","),
                 alt.Tooltip("nota_media:Q", title="Nota média", format=".2f")],
    )
    pontos = linha.mark_point(color=AZUL, filled=True, cursor="pointer").encode(
        # O mês escolhido fica maior e os outros continuam na linha. A tendência não pode sumir.
        size=alt.condition(f"datum.ano_mes == '{mes}'" if mes else "false", alt.value(220), alt.value(60)),
    ).add_params(alt.selection_point(name="mes", fields=["ano_mes"], on="click"))
    chave = f"receita-{mes}-{inicio}-{fim}"

    def ao_clicar_no_mes():
        marcados = st.session_state[chave].selection.get("mes", [])
        st.session_state["filtro_mes"] = marcados[0]["ano_mes"] if marcados else None

    st.altair_chart((linha.mark_line(color=AZUL, strokeWidth=2.5) + pontos).properties(height=300), width="stretch",
                    theme=None, key=chave, on_select=ao_clicar_no_mes, selection_mode="mes")
    if mes:
        st.button("Ver o período inteiro", on_click=lambda: st.session_state.update(filtro_mes=None))

abc = ler("categorias_abc").sort_values("ranking").assign(nome=lambda d: d.categoria.map(categoria_br))
classe_a = abc[abc.classe_abc == "A"]
# O rótulo da legenda já diz o que cada classe significa, sem precisar de nota de rodapé.
rotulos = {"A": "A, até 80% da receita", "B": "B, de 80% a 95%", "C": "C, o restante"}
abc["classe"] = abc.classe_abc.map(rotulos)

with painel("Curva ABC das categorias", "abc",
            f"{len(classe_a)} de {len(abc)} categorias somam {pct(classe_a.participacao.sum())} da receita"
            + (" de 01/2017 a 08/2018. As categorias não estão separadas por mês na camada ouro." if mes else ".")):
    mostrar = st.slider("Categorias no gráfico", 10, len(abc), 25)
    desenhar(
        alt.Chart(abc.head(mostrar))
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            y=alt.Y("nome:N", sort=None, title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)),
            x=alt.X("receita:Q", axis=eixo_reais_mi("Receita")),
            # Só a classe A ganha cor. O olho vai direto para o que concentra a receita.
            color=alt.Color("classe:N", scale=alt.Scale(domain=list(rotulos.values()), range=[AZUL, NEUTRO, NEUTRO_CLARO]),
                            legend=alt.Legend(title=None, orient="top", symbolType="square", symbolSize=140,
                                              labelFontSize=13)),
            tooltip=[alt.Tooltip("nome", title="Categoria"), alt.Tooltip("receita", title="Receita", format="$,.0f"),
                     alt.Tooltip("participacao", title="Participação", format=".1%"),
                     alt.Tooltip("acumulado", title="Acumulado", format=".1%"), alt.Tooltip("classe_abc", title="Classe")],
        )
        .properties(height=max(300, 24 * mostrar))
    )
    with st.expander("Tabela completa"):
        st.dataframe(
            abc[["ranking", "nome", "receita", "itens", "participacao", "acumulado", "classe_abc"]],
            hide_index=True, width="stretch",
            column_config={
                "ranking": "Posição", "nome": "Categoria", "itens": "Itens", "classe_abc": "Classe",
                "receita": st.column_config.NumberColumn("Receita", format="R$ %.0f"),
                "participacao": st.column_config.NumberColumn("Participação", format="percent"),
                "acumulado": st.column_config.NumberColumn("Acumulado", format="percent"),
            },
        )

conclusao(
    f"{len(classe_a)} de {len(abc)} categorias somam {pct(classe_a.participacao.sum())} da receita, "
    f"com {classe_a.nome.iloc[0].lower()} na frente com {reais(classe_a.receita.iloc[0] / 1e6, 2)} milhões. "
    f"O ponto fraco é a recompra. Só {pct(resumo().pct_recompra)} dos clientes voltaram, então quase toda venda "
    "depende de trazer cliente novo."
)
rodape()
