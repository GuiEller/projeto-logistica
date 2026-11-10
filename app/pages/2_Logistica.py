"""Logística. Onde a entrega falha?"""

import altair as alt
import pandas as pd
import streamlit as st

from dados import (AZUL, DESTAQUE, NEUTRO_CLARO, barra_de_filtro, comparar_destinos, conclusao, desenhar,
                   desenhar_clicavel, escolher_estado, ler, mapa_atraso, num, painel, pct, ponderada, rodape)

st.title("Onde a entrega falha?")

estados = ler("entrega_por_estado")
estados["atrasos"] = estados.pedidos * estados.taxa_atraso
uf = barra_de_filtro(estados.set_index("estado").pedidos, "pedidos entregues")
TODAS = sorted(estados.regiao.unique())
# A lista de regiões mora no session_state porque o clique numa barra de região também escreve nela.
st.session_state.setdefault("regioes", TODAS)
f1, f2 = st.columns(2)
regioes = f1.multiselect("Regiões", TODAS, key="regioes")
# Estado com poucos pedidos tem taxa instável. 300 é o mesmo corte da análise SQL 06.
minimo = f2.slider("Mínimo de pedidos por estado", 0, 2000, 300, step=50)
# O estado escolhido no clique fica na tela mesmo fora dos filtros. Escolher e ver sumir seria pior que o aviso.
filtro = estados[(estados.regiao.isin(regioes) & (estados.pedidos >= minimo)) | (estados.estado == uf)].copy()

if filtro.empty:
    st.warning("Nenhum estado com esses filtros.")
    st.stop()

pior = filtro.sort_values("taxa_atraso", ascending=False).iloc[0]
rj = estados[estados.estado == "RJ"].iloc[0]
# O RJ é o destaque porque é onde a recomendação manda agir. AL atrasa mais, mas tem 30 vezes menos pedidos.
filtro["destaque"] = filtro.estado == "RJ"

mapa, ranking = st.columns([4, 3])
with mapa:
    # O volume explica o atraso: o mesmo percentual pesa muito mais onde há mais pedidos.
    modo = st.segmented_control("Pintar o mapa por", ["Atraso", "Volume de pedidos"], default="Atraso",
                                label_visibility="collapsed", key="modo_mapa") or "Atraso"
    volume = modo != "Atraso"
    with painel("Pedidos por estado" if volume else "Atraso por estado", "mapa-logistica",
                ("Pedidos entregues de cada estado. A escala é de raiz quadrada, para o SP não apagar os outros. "
                 if volume else "Parcela dos pedidos entregue depois da data prometida. ")
                + "Cinza é estado fora do filtro."):
        desenhar_clicavel(mapa_atraso(filtro, altura=460, uf=uf, **(
            dict(campo="pedidos", titulo="Pedidos entregues") if volume else {})), "mapa-logistica")
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
        barras = base.mark_bar(cornerRadiusEnd=4, size=14, cursor="pointer").encode(
            color=alt.condition("datum.destaque", alt.value(DESTAQUE), alt.value(AZUL)),
            opacity=alt.condition(f"datum.estado == '{uf}'" if uf else "true", alt.value(1), alt.value(0.3)),
        ).add_params(alt.selection_point(name="uf", fields=["estado"], on="click"))
        valores = base.mark_text(align="left", dx=4, fontSize=11, color="#5f6672").encode(
            text=alt.Text("taxa_atraso:Q", format=".1%"))
        desenhar_clicavel((barras + valores).properties(height=max(260, 20 * len(filtro))), "ranking")

# O mesmo vendedor entregando para RJ e para SP. Não depende dos filtros da página, porque compara vendedores, não estados.
vendedor = ler("atraso_vendedor_destino")
rj_sp = comparar_destinos(vendedor, "RJ", "SP")
rj_mg = comparar_destinos(vendedor, "RJ", "MG", origem="SP")
de_fora = comparar_destinos(vendedor, "RJ", "SP", fora_dos_destinos=True)
pares = rj_sp["pares"].assign(diferenca=lambda d: d.taxa_a - d.taxa_b).sort_values("diferenca")
pares["ordem"] = range(1, len(pares) + 1)
pontos = pares.melt(id_vars=["vendedor_id", "ordem"], value_vars=["taxa_b", "taxa_a"], var_name="destino", value_name="taxa")
pontos["destino"] = pontos.destino.map({"taxa_a": "Para o RJ", "taxa_b": "Para SP"})

with painel("O mesmo vendedor atrasa mais para o RJ", "vendedores",
            f"{rj_sp['vendedores']} vendedores com 20 ou mais pedidos para cada destino. Em média, eles atrasam "
            f"{pct(rj_sp['media_a'])} dos pedidos para o RJ e {pct(rj_sp['media_b'])} para SP. "
            "Como o vendedor é o mesmo, a diferença vem do caminho até o cliente."):
    # Cada vendedor é uma coluna, com uma linha cinza ligando os dois destinos. Ordem pela diferença, sem nome no eixo,
    # porque o id do vendedor é um código sem sentido para quem lê.
    eixo_x = alt.X("ordem:O", title="Vendedores, do que menos piora no RJ ao que mais piora", axis=None)
    dica = [alt.Tooltip("vendedor_id", title="Vendedor"), alt.Tooltip("destino", title="Destino"),
            alt.Tooltip("taxa", title="Atraso", format=".1%")]
    ligacao = alt.Chart(pares).mark_rule(color=NEUTRO_CLARO, strokeWidth=1.5).encode(
        x=eixo_x, y=alt.Y("taxa_b:Q"), y2="taxa_a:Q")
    marcas = alt.Chart(pontos).mark_circle(size=34, opacity=0.9).encode(
        x=eixo_x,
        y=alt.Y("taxa:Q", title="Pedidos atrasados", axis=alt.Axis(format=".0%", tickCount=5)),
        color=alt.Color("destino:N", title=None, scale=alt.Scale(domain=["Para SP", "Para o RJ"], range=[AZUL, DESTAQUE]),
                        legend=alt.Legend(orient="top-left", direction="horizontal")),
        tooltip=dica)
    desenhar((ligacao + marcas).properties(height=300))
    if uf and uf not in ("RJ", "SP"):
        st.caption(f"A comparação pelo mesmo vendedor é o achado do RJ e não muda com o estado escolhido ({uf}).")
    st.caption(f"Dois controles dão o mesmo resultado. Só vendedores de SP, o RJ atrasa {pct(rj_mg['media_a'])} contra "
               f"{pct(rj_mg['media_b'])} em MG, que fica mais longe de SP do que o RJ ({rj_mg['vendedores']} vendedores). "
               f"Só vendedores de fora de RJ e SP, {pct(de_fora['media_a'])} contra {pct(de_fora['media_b'])} "
               f"({de_fora['vendedores']} vendedores). Teste de Wilcoxon pareado, p de no máximo "
               f"{num(max(rj_sp['p_valor'], rj_mg['p_valor'], de_fora['p_valor']), 4)} nos três. "
               "Pedidos com mais de um vendedor ficam fora.")

# Agregar por região exige média ponderada pelos pedidos. Média simples das taxas daria o mesmo peso a RR e SP.
por_regiao = (filtro.groupby("regiao")
              .apply(lambda g: pd.Series({"frete_medio": ponderada(g, "frete_medio")}), include_groups=False)
              .reset_index())
faixa = ler("entrega_por_regiao").query("regiao in @regioes")
# Com estado escolhido, a região dele fica cheia e as outras apagadas. Faixa e frete só existem por região.
regiao_do_estado = estados.set_index("estado").regiao.get(uf)
cheia = alt.condition(f"datum.regiao == '{regiao_do_estado}'" if uf else "true", alt.value(1), alt.value(0.3))
clique_regiao = alt.selection_point(name="regiao", fields=["regiao"], on="click")


def desenhar_regioes(grafico, chave: str):
    """Clique numa região filtra mapa e ranking por ela. Estado de outra região deixa de estar escolhido."""
    chave = f"{chave}-{'-'.join(regioes)}-{uf}"

    def ao_clicar():
        marcadas = st.session_state[chave].selection.get("regiao", [])
        if marcadas and regioes == [marcadas[0]["regiao"]]:
            st.session_state["regioes"] = TODAS  # segundo clique na região única volta a todas
        elif marcadas:
            st.session_state["regioes"] = [marcadas[0]["regiao"]]
            if uf and regiao_do_estado != marcadas[0]["regiao"]:
                escolher_estado(None)

    st.altair_chart(grafico, width="stretch", theme=None, key=chave, on_select=ao_clicar, selection_mode="regiao")


def barras_regiao(coluna, titulo_eixo, formato, dica):
    return (
        alt.Chart(por_regiao).mark_bar(color=AZUL, cornerRadiusEnd=4, size=26, cursor="pointer").encode(
            y=alt.Y("regiao:N", sort="-x", title=None), opacity=cheia,
            x=alt.X(f"{coluna}:Q", title=titulo_eixo, axis=alt.Axis(tickCount=4, format=formato)),
            tooltip=[alt.Tooltip("regiao", title="Região"), alt.Tooltip(coluna, title=dica, format=".1f")],
        ).add_params(clique_regiao).properties(height=220)
    )


c1, c2 = st.columns(2)
with c1:
    with painel("A entrega é menos previsível no Norte e no Nordeste", "faixa",
                "Dias entre a entrega e a data prometida. A barra vai do pedido mais adiantado ao mais atrasado entre os "
                "80% do meio (p10 a p90), e o traço é a mediana. Negativo é adiantado."):
        # Faixa em vez de média. A média esconde que a mesma região tem pedido 24 dias adiantado e pedido atrasado.
        eixo_y = alt.Y("regiao:N", title=None, sort=alt.EncodingSortField("p90", order="descending"))
        dica = [alt.Tooltip("regiao", title="Região"), alt.Tooltip("pedidos", title="Pedidos", format=","),
                alt.Tooltip("p10", title="p10 (dias)"), alt.Tooltip("p50", title="Mediana (dias)"),
                alt.Tooltip("p90", title="p90 (dias)")]
        barra = alt.Chart(faixa).mark_bar(color="#a9c1e8", cornerRadius=4, size=22, cursor="pointer").encode(
            y=eixo_y, x=alt.X("p10:Q", title="Dias em relação ao prometido", axis=alt.Axis(tickCount=6)), x2="p90:Q",
            opacity=cheia, tooltip=dica).add_params(clique_regiao)
        mediana = alt.Chart(faixa).mark_tick(color=AZUL, thickness=3, size=22).encode(y=eixo_y, x="p50:Q", tooltip=dica)
        prometido = alt.Chart(pd.DataFrame({"x": [0]}))
        desenhar_regioes((barra + mediana + prometido.mark_rule(color=DESTAQUE, strokeDash=[4, 3]).encode(x="x:Q")
                          + prometido.mark_text(text="dia prometido", align="left", dx=4, dy=-6, color=DESTAQUE,
                                                fontSize=11).encode(x="x:Q", y=alt.value(0))).properties(height=220),
                         "faixa-regiao")
with c2:
    with painel("Frete médio por pedido", "frete", "Valor do frete somado por pedido, em reais."):
        desenhar_regioes(barras_regiao("frete_medio", "Frete médio", "$,.0f", "Frete (R$)"), "frete")
if len(regioes) < len(TODAS):
    st.button("Todas as regiões", on_click=lambda: st.session_state.update(regioes=TODAS))

folga_geral = ponderada(estados, "prazo_medio") - ponderada(estados, "entrega_media")
largura = ler("entrega_por_regiao").assign(l=lambda d: d.p90 - d.p10).set_index("regiao").l
escolhido = estados.set_index("estado").loc[uf] if uf else None
conclusao(
    (f"{uf} atrasa {pct(escolhido.taxa_atraso)} dos pedidos entregues, contra "
     f"{pct(estados.atrasos.sum() / estados.pedidos.sum())} no Brasil, e responde por "
     f"{pct(escolhido.atrasos / estados.atrasos.sum())} dos atrasos do país. " if uf else "") +
    f"O RJ tem {pct(rj.pedidos / estados.pedidos.sum())} dos pedidos e {pct(rj.atrasos / estados.atrasos.sum())} dos atrasos, "
    f"e o mesmo vendedor atrasa {pct(rj_sp['media_a'])} para o RJ contra {pct(rj_sp['media_b'])} para SP. O problema do RJ "
    f"está na rota, não no vendedor. Nos filtros atuais, o pior estado é {pior.estado}, com {pct(pior.taxa_atraso)} de atraso. "
    f"O pedido médio chega {num(folga_geral, 1)} dias antes do prometido, mas a entrega no Nordeste varia {num(largura['Nordeste'])} "
    f"dias contra {num(largura['Sudeste'])} no Sudeste. O prazo nacional único é folgado onde a entrega é rápida e apertado "
    "onde ela é imprevisível."
)
rodape()
