"""Cliente. O atraso derruba a nota?"""

import altair as alt
import pandas as pd
import streamlit as st

from dados import (AZUL, DESTAQUE, alternar, barra_de_filtro, conclusao, desenhar, faixas_do_estado, ler, num, painel, pct,
                   razao, rodape)

st.title("O atraso derruba a nota?")

uf = barra_de_filtro(ler("faixa_por_estado").groupby("estado").pedidos.sum(), "pedidos entregues e avaliados")
faixas = faixas_do_estado(uf)
no_prazo, atrasados = faixas[~faixas.atrasado], faixas[faixas.atrasado]
baixa_prazo = razao(no_prazo.notas_baixas.sum(), no_prazo.pedidos.sum())
baixa_atraso = razao(atrasados.notas_baixas.sum(), atrasados.pedidos.sum())

kpi = dict(border=True, height="stretch")
c1, c2, c3 = st.columns(3)
c1.metric("Nota média no prazo", num(razao(no_prazo.soma_notas.sum(), no_prazo.pedidos.sum()), 2), **kpi)
c2.metric("Nota média com atraso", num(razao(atrasados.soma_notas.sum(), atrasados.pedidos.sum()), 2), **kpi)
c3.metric("Chance de nota 1 ou 2 quando atrasa", f"{num(razao(baixa_atraso, baixa_prazo), 1)} vezes maior", **kpi)

# Dia clicado na curva lá embaixo. Ele acende a faixa a que pertence, com a mesma regra da vw_pedidos_entregues.
dia = st.session_state.get("filtro_dia")
dia = dia if isinstance(dia, int) and -10 <= dia <= 15 else None
faixa_do_dia = None if dia is None else next(f for limite, f in [(-10, "1"), (0, "2"), (3, "3"), (7, "4"), (99, "5")]
                                             if dia <= limite)
onde = f" em {uf}" if uf else ""
with painel("Nota por faixa de atraso", "nota-faixa", "Azul chegou no prazo, laranja chegou atrasado." + (f" Pedidos de {uf}." if uf else "")
            + (f" Acesa a faixa do dia {dia} escolhido na curva." if dia is not None else "")):
    escolha = st.radio("Medida", ["Nota média", "Percentual de nota 1 ou 2"], horizontal=True)
    # O eixo usa número redondo e o rótulo da barra usa o valor exato.
    coluna, formato = ("nota_media", ".0f") if escolha == "Nota média" else ("pct_nota_baixa", ".0%")
    base = alt.Chart(faixas).encode(
        y=alt.Y("situacao:N", sort=None, title=None, axis=alt.Axis(labelLimit=220, labelFontSize=13)),
        x=alt.X(f"{coluna}:Q", title=escolha, axis=alt.Axis(format=formato, tickCount=5)),
        tooltip=[alt.Tooltip("situacao", title="Situação"), alt.Tooltip("pedidos", title="Pedidos", format=","),
                 alt.Tooltip("nota_media", title="Nota média", format=".2f"),
                 alt.Tooltip("pct_nota_baixa", title="Nota 1 ou 2", format=".1%")],
    )
    barras = base.mark_bar(cornerRadiusEnd=4, size=34).encode(
        color=alt.condition("datum.atrasado", alt.value(DESTAQUE), alt.value(AZUL)),
        opacity=alt.condition(f"substring(datum.faixa_atraso, 0, 1) == '{faixa_do_dia}'" if faixa_do_dia else "true",
                              alt.value(1), alt.value(0.3)))
    valores = base.mark_text(align="left", dx=6, fontSize=14, fontWeight=700, color="#0a0a0a").encode(
        text=alt.Text(f"{coluna}:Q", format=".2f" if coluna == "nota_media" else ".1%"))
    desenhar((barras + valores).properties(height=300))
    if dia is not None:
        st.button("Ver todas as faixas", on_click=lambda: st.session_state.update(filtro_dia=None))

# Curva dia a dia. As faixas acima juntam 1 a 3 dias de atraso, e é justamente aí que a nota despenca.
dias = ler("nota_por_dia_atraso").query("-10 <= dias_atraso <= 15").assign(
    taxa=lambda d: d.notas_baixas / d.pedidos, atrasado=lambda d: d.dias_atraso >= 1)
taxa_dia = dias.set_index("dias_atraso").taxa
with painel("A nota despenca já nos primeiros dias de atraso", "nota-dia",
            f"Parcela de notas 1 e 2 por dia em relação à data prometida, no Brasil inteiro. No dia prometido é "
            f"{pct(taxa_dia[0])}. Com 1 dia de atraso sobe para {pct(taxa_dia[1])}, com 2 dias para {pct(taxa_dia[2])} "
            f"e com 3 dias para {pct(taxa_dia[3])}. Clique num dia para acender a faixa dele acima, e de novo para desfazer."):
    eixo_x = alt.X("dias_atraso:Q", title="Dias em relação à data prometida (negativo é adiantado)",
                   scale=alt.Scale(domain=[-10, 15]), axis=alt.Axis(tickCount=13, format="d"))
    eixo_y = alt.Y("taxa:Q", title="Notas 1 e 2", axis=alt.Axis(format=".0%", tickCount=5))
    dica = [alt.Tooltip("dias_atraso", title="Dias"), alt.Tooltip("pedidos", title="Pedidos avaliados", format=","),
            alt.Tooltip("taxa", title="Notas 1 e 2", format=".1%")]
    linha = lambda dados, cor: alt.Chart(dados).mark_line(color=cor, strokeWidth=2.5).encode(x=eixo_x, y=eixo_y)
    # Pontos numa camada só, com a seleção. O dia escolhido fica maior.
    pontos = alt.Chart(dias).mark_circle(cursor="pointer").encode(
        x=eixo_x, y=eixo_y, tooltip=dica,
        color=alt.condition("datum.atrasado", alt.value(DESTAQUE), alt.value(AZUL)),
        size=alt.condition(f"datum.dias_atraso == {dia}" if dia is not None else "false", alt.value(160), alt.value(36)),
    ).add_params(alt.selection_point(name="dia", fields=["dias_atraso"], on="click"))
    # O trecho atrasado começa no dia 0 para a linha não ter buraco entre as duas cores.
    prometido = alt.Chart(pd.DataFrame({"x": [0]}))
    chave = f"curva-{dia}"

    def ao_clicar_no_dia():
        marcados = st.session_state[chave].selection.get("dia", [])
        st.session_state["filtro_dia"] = alternar(dia, int(marcados[0]["dias_atraso"]) if marcados else None)

    st.altair_chart((linha(dias[~dias.atrasado], AZUL) + linha(dias[dias.dias_atraso >= 0], DESTAQUE) + pontos
                     + prometido.mark_rule(color="#a3a8b0", strokeDash=[4, 3]).encode(x="x:Q")
                     + prometido.mark_text(text="dia prometido", align="left", dx=4, color="#5f6672", fontSize=11)
                     .encode(x="x:Q", y=alt.value(12))).properties(height=300),
                    width="stretch", theme=None, key=chave, on_select=ao_clicar_no_dia, selection_mode="dia")
    # Patamar somando pedidos e notas baixas, não média das taxas, porque cada dia tem um número de pedidos diferente.
    semana = dias[dias.dias_atraso.between(7, 15)]
    st.caption(f"De 7 a 15 dias de atraso, {pct(semana.notas_baixas.sum() / semana.pedidos.sum())} das avaliações são "
               "nota 1 ou 2. O estrago acontece nos três primeiros dias, então o aviso ao cliente precisa sair antes disso.")

with painel("Teste de hipótese", "hipotese"):
    st.markdown(
        "A diferença de nota pode ser acaso? Para responder, o projeto rodou dois testes sobre os pedidos entregues "
        "e avaliados.\n\n"
        "- **Mann-Whitney U unilateral**, porque a nota vai de 1 a 5 e não segue distribuição normal, então o teste t "
        "não serve. p-valor abaixo de 0,0001 e efeito grande (rank-biserial de 0,64).\n"
        "- **Qui-quadrado** para a proporção de notas 1 e 2, também com p-valor abaixo de 0,0001.\n\n"
        "Com alfa de 5%, a hipótese nula é rejeitada nos dois. O teste mostra associação, não prova causa sozinho, "
        "mas a nota cai de forma consistente a cada faixa de atraso, o que reforça a leitura. "
        "O relatório completo está em `resultados/teste_hipotese.md` no repositório."
    )

conclusao(
    f"Os pedidos atrasados são só {pct(razao(atrasados.pedidos.sum(), faixas.pedidos.sum()))} do total{onde}, mas "
    f"respondem por {pct(razao(atrasados.notas_baixas.sum(), faixas.notas_baixas.sum()))} de todas as notas 1 e 2. "
    "Atacar o atraso é a alavanca mais concentrada que existe para melhorar a reputação."
)
rodape()
