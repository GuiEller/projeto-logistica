"""Cliente. O atraso derruba a nota?"""

import altair as alt
import pandas as pd
import streamlit as st

from dados import AZUL, DESTAQUE, conclusao, desenhar, ler, num, painel, pct, ponderada, resumo, rodape

st.title("O atraso derruba a nota?")

faixas = ler("nota_por_faixa").sort_values("faixa_atraso")
# O prefixo "1. ", "2. " existe só para ordenar. Na tela, sai.
faixas["situacao"] = faixas.faixa_atraso.str.split(". ", n=1).str[1]
faixas["atrasado"] = faixas.faixa_atraso.str[0].astype(int) >= 3
r = resumo()

no_prazo = faixas[~faixas.atrasado]
atrasados = faixas[faixas.atrasado]
vezes = ponderada(atrasados, "pct_nota_baixa") / ponderada(no_prazo, "pct_nota_baixa")

kpi = dict(border=True, height="stretch")
c1, c2, c3 = st.columns(3)
c1.metric("Nota média no prazo", num(ponderada(no_prazo, "nota_media"), 2), **kpi)
c2.metric("Nota média com atraso", num(ponderada(atrasados, "nota_media"), 2), **kpi)
c3.metric("Chance de nota 1 ou 2 quando atrasa", f"{num(vezes, 1)} vezes maior", **kpi)

with painel("Nota por faixa de atraso", "nota-faixa", "Azul chegou no prazo, laranja chegou atrasado."):
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
        color=alt.condition("datum.atrasado", alt.value(DESTAQUE), alt.value(AZUL)))
    valores = base.mark_text(align="left", dx=6, fontSize=14, fontWeight=700, color="#0a0a0a").encode(
        text=alt.Text(f"{coluna}:Q", format=".2f" if coluna == "nota_media" else ".1%"))
    desenhar((barras + valores).properties(height=300))

# Curva dia a dia. As faixas acima juntam 1 a 3 dias de atraso, e é justamente aí que a nota despenca.
dias = ler("nota_por_dia_atraso").query("-10 <= dias_atraso <= 15").assign(
    taxa=lambda d: d.notas_baixas / d.pedidos, atrasado=lambda d: d.dias_atraso >= 1)
taxa_dia = dias.set_index("dias_atraso").taxa
with painel("A nota despenca já nos primeiros dias de atraso", "nota-dia",
            f"Parcela de notas 1 e 2 por dia em relação à data prometida. No dia prometido é {pct(taxa_dia[0])}. "
            f"Com 1 dia de atraso sobe para {pct(taxa_dia[1])}, com 2 dias para {pct(taxa_dia[2])} e com 3 dias "
            f"para {pct(taxa_dia[3])}."):
    eixo_x = alt.X("dias_atraso:Q", title="Dias em relação à data prometida (negativo é adiantado)",
                   scale=alt.Scale(domain=[-10, 15]), axis=alt.Axis(tickCount=13, format="d"))
    eixo_y = alt.Y("taxa:Q", title="Notas 1 e 2", axis=alt.Axis(format=".0%", tickCount=5))
    dica = [alt.Tooltip("dias_atraso", title="Dias"), alt.Tooltip("pedidos", title="Pedidos avaliados", format=","),
            alt.Tooltip("taxa", title="Notas 1 e 2", format=".1%")]
    linha = lambda dados, cor: alt.Chart(dados).mark_line(color=cor, strokeWidth=2.5, point=alt.OverlayMarkDef(
        color=cor, size=36)).encode(x=eixo_x, y=eixo_y, tooltip=dica)
    # O trecho atrasado começa no dia 0 para a linha não ter buraco entre as duas cores.
    prometido = alt.Chart(pd.DataFrame({"x": [0]}))
    desenhar((linha(dias[~dias.atrasado], AZUL) + linha(dias[dias.dias_atraso >= 0], DESTAQUE)
              + prometido.mark_rule(color="#a3a8b0", strokeDash=[4, 3]).encode(x="x:Q")
              + prometido.mark_text(text="dia prometido", align="left", dx=4, color="#5f6672", fontSize=11)
              .encode(x="x:Q", y=alt.value(12))).properties(height=300))
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
    f"Os pedidos atrasados são só {pct(r.pct_atrasados)} do total, mas respondem por {pct(r.parcela_notas_baixas_atraso)} "
    "de todas as notas 1 e 2. Atacar o atraso é a alavanca mais concentrada que existe para melhorar a reputação."
)
rodape()
