"""Relatório. Quanto dá para confiar nos achados e quanto cada ação rende?"""

import math

import altair as alt
import pandas as pd
import streamlit as st

from dados import (AZUL, CINZA, DESTAQUE, TINTA, conclusao, desenhar, ler, mes_br, num, painel, pct,
                   ponderada, resumo, rodape, tamanho_amostra)

st.title("Quanto dá para confiar nos achados?")
st.markdown("A visão geral mostrou que o atraso derruba a nota pedido a pedido. Esta página confere a mesma relação "
            "de outros dois ângulos, estima quanto cada recomendação rende e desenha o teste da recomendação 3. "
            "O texto completo está em `resultados/relatorio.md` no repositório.")


def correlacao(x: pd.Series, y: pd.Series, metodo="pearson"):
    """Correlação com intervalo de 95% pela transformação de Fisher."""
    # Com 20 meses ou 27 estados, o r sozinho engana. O intervalo mostra o quanto ele poderia variar.
    r = x.corr(y, method=metodo)
    erro = 1.96 / math.sqrt(len(x) - 3)
    return r, math.tanh(math.atanh(r) - erro), math.tanh(math.atanh(r) + erro)


r = resumo()
kpis = ler("kpis_mensais").sort_values("ano_mes").assign(mes=lambda d: d.ano_mes.map(mes_br))
estados = ler("entrega_por_estado").assign(atrasos=lambda d: d.pedidos * d.taxa_atraso)
faixas = ler("nota_por_faixa")
atrasado = faixas.faixa_atraso.str[0].astype(int) >= 3

# Mês fora do padrão pela regra do boxplot (acima de Q3 + 1,5 x IQR). A regra decide, não o olho.
q1, q3 = kpis.taxa_atraso.quantile([0.25, 0.75])
kpis["crise"] = kpis.taxa_atraso > q3 + 1.5 * (q3 - q1)
crise = kpis[kpis.crise]
r_mes, r_mes_min, r_mes_max = correlacao(kpis.taxa_atraso, kpis.nota_media)
r_sem_crise, _, _ = correlacao(kpis[~kpis.crise].taxa_atraso, kpis[~kpis.crise].nota_media)
# Spearman entre estados, porque a relação não precisa ser reta e RR, com 40 pedidos, não deve puxar o resultado.
r_uf, r_uf_min, r_uf_max = correlacao(estados.taxa_atraso, estados.nota_media, "spearman")

# Diferença na chance de nota 1 ou 2 entre atrasado e no prazo. É o quanto cada atraso evitado vale em nota baixa.
nota_baixa_atraso = ponderada(faixas[atrasado], "pct_nota_baixa")
diferenca = nota_baixa_atraso - ponderada(faixas[~atrasado], "pct_nota_baixa")
notas_baixas = (faixas.pedidos * faixas.pct_nota_baixa).sum()
media_nacional = estados.atrasos.sum() / estados.pedidos.sum()
rj = estados[estados.estado == "RJ"].iloc[0]
sp = estados[estados.estado == "SP"].iloc[0]
nordeste = estados[estados.regiao == "Nordeste"]
cenarios = pd.DataFrame([
    ("RJ atrasa como SP", rj.pedidos * (rj.taxa_atraso - sp.taxa_atraso)),
    ("RJ na média nacional", rj.pedidos * (rj.taxa_atraso - media_nacional)),
    # clip(lower=0) porque estado do Nordeste que já atrasa menos que a média não tem atraso a evitar.
    ("Nordeste na média nacional", (nordeste.pedidos * (nordeste.taxa_atraso - media_nacional).clip(lower=0)).sum()),
], columns=["cenario", "atrasos_evitados"])
cenarios["notas_baixas_evitadas"] = cenarios.atrasos_evitados * diferenca
cenarios["parcela"] = cenarios.notas_baixas_evitadas / notas_baixas

# Atrasados por mês em 2018, a população que receberia o aviso no teste.
atrasados_mes = (kpis.pedidos * kpis.taxa_atraso)[kpis.ano_mes >= "2018"].mean()

kpi = dict(border=True, height="stretch")
c1, c2, c3, c4 = st.columns(4)
# Rótulo curto no cartão e a frase inteira no help, porque o cartão corta texto longo com reticências.
c1.metric("Atraso x nota, por mês", num(r_mes, 2), help="Correlação de Pearson entre os 20 meses", **kpi)
c2.metric("Atraso x nota, por estado", num(r_uf, 2), help="Correlação de Spearman entre os 27 estados", **kpi)
c3.metric("Notas 1 e 2 a menos no RJ", num(cenarios.notas_baixas_evitadas.iloc[0]),
          help="Se o RJ atrasasse na mesma taxa de SP", **kpi)
c4.metric("Meses de teste A/B", num(2 * tamanho_amostra(nota_baixa_atraso, nota_baixa_atraso - 0.05) / atrasados_mes, 1),
          help="Para enxergar uma queda de 5 pontos na nota 1 ou 2 dos atrasados", **kpi)

meses_crise = ", ".join(crise.mes)
with painel("Nos meses em que o atraso subiu, a nota caiu", "serie",
            f"Correlação de Pearson de {num(r_mes, 2)} (IC 95% de {num(r_mes_min, 2)} a {num(r_mes_max, 2)}), "
            f"com 20 meses. Em tom escuro, os meses fora do padrão ({meses_crise})."):
    # Dois gráficos empilhados com o mesmo eixo de meses, no lugar de um gráfico de dois eixos.
    # Dois eixos no mesmo gráfico deixam a escala decidir se as linhas parecem andar juntas.
    eixo_x = alt.X("mes:O", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelOverlap=True))
    # minExtent igual nos dois eixos Y para as colunas dos meses ficarem alinhadas entre os gráficos.
    dica = [alt.Tooltip("mes", title="Mês"), alt.Tooltip("pedidos", title="Pedidos", format=","),
            alt.Tooltip("taxa_atraso", title="Atraso", format=".1%"), alt.Tooltip("nota_media", title="Nota média", format=".2f")]
    desenhar(alt.Chart(kpis).mark_bar(cornerRadiusEnd=3).encode(
        x=eixo_x,
        y=alt.Y("taxa_atraso:Q", title="Atraso", axis=alt.Axis(format=".0%", tickCount=4, minExtent=44)),
        color=alt.condition("datum.crise", alt.value("#7a2e0b"), alt.value(DESTAQUE)),
        tooltip=dica,
    ).properties(height=170))
    # Linha não precisa começar no zero. A nota varia entre 3,7 e 4,3 e é essa variação que interessa.
    linha = alt.Chart(kpis).encode(
        x=eixo_x,
        y=alt.Y("nota_media:Q", title="Nota média", scale=alt.Scale(domain=[3.6, 4.4]),
                axis=alt.Axis(format=".1f", tickCount=4, minExtent=44)),
        tooltip=dica,
    )
    desenhar((linha.mark_line(color=AZUL, strokeWidth=2.5)
              + linha.mark_point(filled=True, size=60).encode(
                  color=alt.condition("datum.crise", alt.value(TINTA), alt.value(AZUL)))).properties(height=170))
    st.caption(f"Sem os meses fora do padrão, a correlação cai para {num(r_sem_crise, 2)} e deixa de ser significativa "
               "a 5%. A relação mensal existe, mas é puxada pelos picos de atraso. Por isso a prova principal continua "
               "sendo o teste pedido a pedido da página Cliente.")

esq, dir = st.columns(2)
with esq:
    with painel("Estados que atrasam mais têm nota menor", "dispersao",
                f"Correlação de Spearman de {num(r_uf, 2)} (IC 95% de {num(r_uf_min, 2)} a {num(r_uf_max, 2)}), "
                "com 27 estados. O tamanho do ponto é o número de pedidos."):
        base = alt.Chart(estados.assign(destaque=estados.estado == "RJ")).encode(
            x=alt.X("taxa_atraso:Q", title="Pedidos atrasados", axis=alt.Axis(format=".0%", tickCount=5)),
            # Domínio fixo com folga em cima, para a sigla de SP não sair do gráfico e o eixo andar de 0,1 em 0,1.
            y=alt.Y("nota_media:Q", title="Nota média", scale=alt.Scale(domain=[3.8, 4.4]),
                    axis=alt.Axis(format=".1f", values=[3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4])),
            tooltip=[alt.Tooltip("estado", title="Estado"), alt.Tooltip("pedidos", title="Pedidos", format=","),
                     alt.Tooltip("taxa_atraso", title="Atraso", format=".1%"),
                     alt.Tooltip("nota_media", title="Nota média", format=".2f")],
        )
        pontos = base.mark_circle(opacity=0.75).encode(
            size=alt.Size("pedidos:Q", legend=None, scale=alt.Scale(range=[30, 900])),
            color=alt.condition("datum.destaque", alt.value(DESTAQUE), alt.value(AZUL)))
        # Sigla em todo ponto, porque a cor sozinha não diz qual estado é qual.
        siglas = base.mark_text(dy=-11, fontSize=11, color=CINZA).encode(text="estado:N")
        desenhar((pontos + siglas).properties(height=340))
        st.caption("Laranja marca o RJ. Correlação entre estados não fala de cada pedido, mas confirma no mapa o que "
                   "o teste de hipótese mostrou pedido a pedido.")
with dir:
    with painel("Quanto cada ação rende em notas 1 e 2", "impacto",
                # Diferença entre duas proporções se fala em pontos percentuais. "53,2% a menos" seria outra conta.
                f"Cada atraso evitado tira {num(100 * diferenca, 1)} pontos percentuais da chance de nota 1 ou 2, a diferença entre "
                f"atrasado ({pct(nota_baixa_atraso)}) e no prazo. Base de {num(notas_baixas)} notas 1 e 2."):
        # st.table em vez de st.dataframe porque a tabela quebra o cabeçalho e cabe na coluna sem rolagem lateral.
        st.table(pd.DataFrame({
            "Cenário": cenarios.cenario,
            "Atrasos a menos": cenarios.atrasos_evitados.map(num),
            "Notas 1 e 2 a menos": cenarios.notas_baixas_evitadas.map(num),
            "Do total de notas 1 e 2": cenarios.parcela.map(pct),
        }).set_index("Cenário"))
        st.caption("Estimativa que supõe que o pedido que deixa de atrasar passa a ser avaliado como um pedido no prazo. "
                   "O teste mostra associação, então o número real tende a ser menor.")

with painel("Quanto tempo leva o teste A/B do aviso de atraso", "ab",
            f"Hoje {pct(nota_baixa_atraso)} dos atrasados dão nota 1 ou 2. O teste divide os atrasados em dois grupos, "
            "um recebe aviso com a nova data e o outro não, com alfa de 5% e poder de 80%."):
    queda = st.slider("Queda mínima na nota 1 ou 2 que o teste precisa enxergar (pontos percentuais)", 3, 15, 5)
    n = tamanho_amostra(nota_baixa_atraso, nota_baixa_atraso - queda / 100)
    a1, a2, a3 = st.columns(3)
    a1.metric("Pedidos atrasados por grupo", num(n), **kpi)
    a2.metric("Total no teste", num(2 * n), **kpi)
    a3.metric("Meses de coleta", num(2 * n / atrasados_mes, 1), **kpi)
    st.caption(f"Em 2018 atrasaram cerca de {num(atrasados_mes)} pedidos por mês, e só eles entram no teste. "
               "Efeito pequeno pede amostra grande, então ou o teste mira uma queda maior ou roda por mais tempo.")

with painel("De onde sai cada número", "bases",
            "Cada página usa a base certa para a pergunta dela, por isso o total de pedidos muda de um gráfico para outro."):
    st.dataframe(pd.DataFrame([
        ("Todos os pedidos da base", r.pedidos_total, "Receita total, clientes e recompra"),
        ("Pedidos de 01/2017 a 08/2018", kpis.pedidos.sum(), "Receita mensal, ticket médio e esta série de meses"),
        ("Pedidos entregues com estado do cliente", estados.pedidos.sum(),
         f"Mapa e ranking de atraso ({pct(media_nacional)} de atraso)"),
        ("Pedidos entregues e avaliados", faixas.pedidos.sum(),
         f"Faixas de atraso e teste de hipótese ({pct(r.pct_atrasados)} de atraso)"),
    ], columns=["Base", "Pedidos", "Onde aparece"]).astype({"Pedidos": int}), hide_index=True, width="stretch",
        column_config={"Pedidos": st.column_config.NumberColumn(format="localized")})

conclusao(
    f"O atraso derruba a nota em três recortes diferentes, pedido a pedido, mês a mês ({num(r_mes, 2)}) e estado a estado "
    f"({num(r_uf, 2)}). O RJ é onde agir rende mais, com cerca de {num(cenarios.notas_baixas_evitadas.iloc[0])} notas 1 e 2 "
    f"a menos se atrasasse como SP. O aviso de atraso precisa de teste antes, e com {num(atrasados_mes)} atrasados por mês "
    f"ele leva {num(2 * tamanho_amostra(nota_baixa_atraso, nota_baixa_atraso - 0.05) / atrasados_mes, 1)} meses para "
    "enxergar uma queda de 5 pontos."
)
rodape()
