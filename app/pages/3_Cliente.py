"""Cliente. O atraso derruba a nota?"""

import altair as alt
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
