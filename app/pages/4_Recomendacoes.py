"""Recomendações. O que fazer primeiro?"""

import streamlit as st

from dados import comparar_destinos, conclusao, ler, num, pct, ponderada, resumo, rodape

st.title("O que fazer primeiro?")
st.markdown("Quatro ações, em ordem de prioridade, cada uma com o número que a sustenta.")

r = resumo()
estados = ler("entrega_por_estado").assign(atrasos=lambda d: d.pedidos * d.taxa_atraso)
rj = estados[estados.estado == "RJ"].iloc[0]
nordeste = estados[estados.regiao == "Nordeste"]
sp = estados[estados.estado == "SP"].iloc[0]
folga = ponderada(estados, "prazo_medio") - ponderada(estados, "entrega_media")
vendedor = comparar_destinos(ler("atraso_vendedor_destino"), "RJ", "SP")
faixa = ler("entrega_por_regiao").assign(largura=lambda d: d.p90 - d.p10).set_index("regiao").largura
dia = ler("nota_por_dia_atraso").set_index("dias_atraso")
nota_baixa_dia = dia.notas_baixas / dia.pedidos

acoes = [
    ("1. Rever a entrega até o cliente no RJ",
     f"O RJ concentra {pct(rj.pedidos / estados.pedidos.sum())} dos pedidos e {pct(rj.atrasos / estados.atrasos.sum())} "
     f"dos atrasos. O mesmo vendedor atrasa {pct(vendedor['media_a'])} dos pedidos para o RJ e {pct(vendedor['media_b'])} "
     f"para SP ({vendedor['vendedores']} vendedores comparados), então o problema está no caminho até o cliente "
     "(transportadora e rota), não em quem vende. Cobrar o vendedor não resolveria."),
    ("2. Prometer prazo por região, e não um prazo nacional",
     f"O pedido médio chega {num(folga, 1)} dias antes do prometido, mas o Nordeste atrasa {pct(ponderada(nordeste, 'taxa_atraso'))} "
     f"das entregas contra {pct(sp.taxa_atraso)} em SP. A entrega no Nordeste também é menos previsível, com "
     f"{num(faixa['Nordeste'])} dias entre os pedidos mais adiantados e os mais atrasados (p10 a p90) contra "
     f"{num(faixa['Sudeste'])} no Sudeste. Prazo calibrado por região encurta a promessa onde sobra folga e alonga onde ela falta."),
    ("3. Avisar o cliente antes do primeiro dia de atraso",
     f"Os atrasados são {pct(r.pct_atrasados)} dos pedidos e {pct(r.parcela_notas_baixas_atraso)} das notas 1 e 2. "
     f"A nota baixa vai de {pct(nota_baixa_dia[0])} no dia prometido para {pct(nota_baixa_dia[2])} com 2 dias de atraso, "
     "então o aviso com nova data precisa sair antes do vencimento. Testar com experimento A/B antes de levar para todos."),
    # O número de clientes vem da segmentação RFM da análise SQL 04 (segmento "Alto valor perdidos").
    ("4. Programa de segunda compra para clientes de alto valor",
     f"Só {pct(r.pct_recompra)} dos clientes voltaram a comprar. Cerca de 14 mil clientes de ticket alto compraram uma vez, "
     "há mais de um ano, e somam 28,9% da receita. Trazer uma parte deles de volta custa menos do que conquistar cliente novo."),
]
for i, (titulo, texto) in enumerate(acoes):
    with st.container(border=True, key=f"painel-acao-{i}"):
        st.markdown(f"#### {titulo}")
        st.markdown(texto)

conclusao(
    "As três primeiras ações atacam a mesma causa, a entrega. O projeto mostrou que ela é a principal alavanca da nota. "
    "A quarta ataca o outro ponto fraco do negócio, a recompra quase inexistente."
)
rodape()
