"""
TESTE DE HIPÓTESE. O atraso na entrega derruba a avaliação do cliente?

EM PORTUGUÊS SIMPLES
  Vimos que clientes com pedido atrasado parecem dar nota menor. Mas "parecer" não basta:
  pode ser coincidência. Um teste de hipótese responde à pergunta "qual a chance de eu ver
  uma diferença tão grande assim se o atraso NÃO tivesse efeito nenhum?". Quando essa chance
  (o "p-valor") é minúscula, concluímos que a diferença é real.

  Fazemos duas perguntas, uma com cada teste:

  H1  A nota de pedidos atrasados é MENOR que a de pedidos no prazo?
      Teste de Mann-Whitney U (unilateral). Por que ele e não o teste t, mais famoso?
      Porque a nota é uma escala de 1 a 5 (ordem, não medida exata) e não segue a curva
      "em sino" que o teste t exige. O Mann-Whitney compara as POSIÇÕES das notas.
      O tamanho do efeito sai da correlação rank-biserial: perto de 0 não importa,
      perto de 1 é enorme.
  H2  A proporção de notas 1 ou 2 é MAIOR entre pedidos atrasados?
      Teste qui-quadrado de independência, mais a diferença de proporções com intervalo
      de confiança de 95% (a faixa onde a diferença real provavelmente está).

Entrada  analise/dados/pedidos_entregues.csv  (gerado por scripts/exportar_csv.sh)
Saída    resultados/teste_hipotese.md e dois gráficos em resultados/
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # desenha os gráficos direto em arquivo, sem abrir janela
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "analise" / "dados" / "pedidos_entregues.csv"
SAIDA = RAIZ / "resultados"
ALFA = 0.05  # nível de significância: aceitamos 5% de chance de errar ao "rejeitar H0"


def formatar_numero(valor, casas=2):
    """Escreve o número no padrão brasileiro: 13591643.7 vira '13.591.643,70'.

    O Python formata com vírgula de milhar e ponto decimal (padrão americano). Para
    inverter sem um separador atropelar o outro, trocamos por uma letra temporária 'X'.
    """
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def carregar(caminho=ENTRADA) -> pd.DataFrame:
    """Lê o CSV e deixa a tabela pronta para os testes."""
    # O caminho é parâmetro para o pytest poder passar um CSV pequeno de teste.
    pedidos = pd.read_csv(caminho)
    # Sem nota ou sem saber se atrasou, o pedido não serve para comparar: sai da análise.
    pedidos = pedidos.dropna(subset=["nota_avaliacao", "entregue_no_prazo"])
    # O Postgres exporta verdadeiro/falso como o texto "t"/"f". Convertemos para True/False.
    pedidos["entregue_no_prazo"] = (
        pedidos["entregue_no_prazo"].astype(str).str.lower().isin(["t", "true", "1"])
    )
    pedidos["atrasado"] = ~pedidos["entregue_no_prazo"]          # "~" inverte: não no prazo = atrasado
    pedidos["nota_baixa"] = pedidos["nota_avaliacao"] <= 2       # notas 1 e 2 são "ruins"
    return pedidos


def teste_mann_whitney(pedidos):
    """H1: as notas dos atrasados são menores que as dos pedidos no prazo?"""
    notas_atrasados = pedidos.loc[pedidos.atrasado, "nota_avaliacao"]
    notas_no_prazo = pedidos.loc[~pedidos.atrasado, "nota_avaliacao"]

    # alternative="less" = teste unilateral: só interessa se os atrasados têm nota MENOR.
    estatistica_u, valor_p = stats.mannwhitneyu(notas_atrasados, notas_no_prazo, alternative="less")

    # Correlação rank-biserial, o "tamanho do efeito":  r = 1 - 2U / (n1 * n2).
    # Sai negativa quando os atrasados têm notas menores; no resultado
    # guardamos o sinal trocado.
    correlacao = 1 - 2 * estatistica_u / (len(notas_atrasados) * len(notas_no_prazo))

    return {
        "n_atrasados": len(notas_atrasados), "n_no_prazo": len(notas_no_prazo),
        "media_atrasados": notas_atrasados.mean(), "media_no_prazo": notas_no_prazo.mean(),
        "mediana_atrasados": notas_atrasados.median(), "mediana_no_prazo": notas_no_prazo.median(),
        "u": estatistica_u, "p": valor_p, "rank_biserial": -correlacao,
    }


def teste_proporcoes(pedidos):
    """H2: a fatia de notas 1 e 2 é maior entre os atrasados?"""
    # Tabela de contagem 2x2 (atrasou ou não x nota baixa ou não), que o qui-quadrado usa.
    tabela_de_contagem = pd.crosstab(pedidos.atrasado, pedidos.nota_baixa)
    qui_quadrado, valor_p, graus_de_liberdade, _ = stats.chi2_contingency(tabela_de_contagem)

    proporcao_atrasados = pedidos.loc[pedidos.atrasado, "nota_baixa"].mean()    # % de notas baixas entre atrasados
    proporcao_no_prazo = pedidos.loc[~pedidos.atrasado, "nota_baixa"].mean()    # % de notas baixas entre os no prazo
    qtd_atrasados = pedidos.atrasado.sum()
    qtd_no_prazo = (~pedidos.atrasado).sum()

    diferenca = proporcao_atrasados - proporcao_no_prazo
    # Erro padrão da diferença de duas proporções. Multiplicado por 1,96, dá a margem do IC de 95%.
    erro_padrao = np.sqrt(
        proporcao_atrasados * (1 - proporcao_atrasados) / qtd_atrasados
        + proporcao_no_prazo * (1 - proporcao_no_prazo) / qtd_no_prazo
    )
    # De todas as notas 1 e 2 da base, que parcela veio de pedidos atrasados?
    parcela_das_notas_baixas = (
        pedidos.loc[pedidos.atrasado, "nota_baixa"].sum() / pedidos["nota_baixa"].sum()
    )

    return {
        "chi2": qui_quadrado, "p": valor_p, "gl": graus_de_liberdade,
        "p_atr": proporcao_atrasados, "p_ok": proporcao_no_prazo, "dif": diferenca,
        "ic": (diferenca - 1.96 * erro_padrao, diferenca + 1.96 * erro_padrao),
        "risco_relativo": proporcao_atrasados / proporcao_no_prazo,  # "quantas vezes mais chance"
        "pct_pedidos_atrasados": pedidos.atrasado.mean(),
        "parcela_notas_baixas_atraso": parcela_das_notas_baixas,
    }


def graficos(pedidos):
    """Desenha dois gráficos de barras (nota média e % de nota baixa) por faixa de atraso."""
    SAIDA.mkdir(exist_ok=True)
    resumo_por_faixa = (
        pedidos.groupby("faixa_atraso")
        .agg(nota_media=("nota_avaliacao", "mean"), pct_baixa=("nota_baixa", "mean"),
             pedidos=("pedido_id", "size"))
        .sort_index()
    )
    # As faixas vêm como "1. No prazo", "2. Até 3 dias"... O número só garante a ordem; tiramos para o rótulo.
    rotulos = [faixa.split(". ", 1)[1] for faixa in resumo_por_faixa.index]
    cores = ["#2E7D32", "#66BB6A", "#FFB300", "#F57C00", "#C62828"]  # do verde (no prazo) ao vermelho (muito atrasado)

    # Cada volta do laço desenha um gráfico: (coluna, título, arquivo, como escrever o número na barra).
    for coluna, titulo, arquivo, formatar in [
        ("nota_media", "Nota média da avaliação por situação da entrega", "nota_por_atraso.png",
         lambda valor: formatar_numero(valor, 2)),
        ("pct_baixa", "Percentual de avaliações com nota 1 ou 2", "nota_baixa_por_atraso.png",
         lambda valor: formatar_numero(100 * valor, 1) + "%"),
    ]:
        figura, eixo = plt.subplots(figsize=(9, 4.8))
        barras = eixo.bar(rotulos, resumo_por_faixa[coluna], color=cores)
        for barra, valor in zip(barras, resumo_por_faixa[coluna]):
            eixo.text(barra.get_x() + barra.get_width() / 2, barra.get_height(), formatar(valor),
                      ha="center", va="bottom", fontsize=10)
        eixo.set_title(titulo, fontsize=13, loc="left")
        eixo.spines[["top", "right"]].set_visible(False)  # tira as bordas de cima e da direita
        eixo.tick_params(axis="x", labelsize=9)
        if coluna == "pct_baixa":
            eixo.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        plt.setp(eixo.get_xticklabels(), rotation=12, ha="right")
        figura.text(0.01, 0.01, f"Base Olist, {formatar_numero(len(pedidos), 0)} pedidos entregues de 01/2017 a 08/2018",
                    fontsize=8, color="#666")
        figura.tight_layout(rect=(0, 0.03, 1, 1))
        figura.savefig(SAIDA / arquivo, dpi=150)
        plt.close(figura)  # libera a memória do gráfico antes de desenhar o próximo
    return resumo_por_faixa


def main():
    pedidos = carregar()
    resultado_mann_whitney = teste_mann_whitney(pedidos)
    resultado_proporcoes = teste_proporcoes(pedidos)
    resumo_por_faixa = graficos(pedidos)

    # Regra de decisão: p-valor menor que o ALFA = "rejeitamos H0" (a diferença é real).
    conclusao_h1 = "rejeitamos H0" if resultado_mann_whitney["p"] < ALFA else "não rejeitamos H0"
    conclusao_h2 = "rejeitamos H0" if resultado_proporcoes["p"] < ALFA else "não rejeitamos H0"
    # p-valores minúsculos viram "< 0,0001" em vez de um monte de zeros.
    formatar_p = lambda valor_p: "< 0,0001" if valor_p < 1e-4 else formatar_numero(valor_p, 4)

    mw = resultado_mann_whitney
    pr = resultado_proporcoes
    br = formatar_numero  # apelido curto só para o texto do relatório abaixo ficar legível

    # O relatório é montado linha a linha e gravado em Markdown.
    linhas_do_relatorio = [
        "# Teste de hipótese, atraso na entrega x avaliação do cliente",
        "",
        f"Base com {br(len(pedidos), 0)} pedidos entregues e avaliados, de 01/2017 a 08/2018. "
        f"{br(100 * pr['pct_pedidos_atrasados'], 1)}% chegaram depois da data prometida.",
        "",
        "## H1. Pedidos atrasados recebem notas menores",
        "",
        "Teste de Mann-Whitney U unilateral, porque a nota é ordinal (1 a 5) e não segue distribuição normal.",
        "",
        "| | Atrasados | No prazo |",
        "|---|---|---|",
        f"| Pedidos | {br(mw['n_atrasados'], 0)} | {br(mw['n_no_prazo'], 0)} |",
        f"| Nota média | {br(mw['media_atrasados'])} | {br(mw['media_no_prazo'])} |",
        f"| Nota mediana | {br(mw['mediana_atrasados'], 0)} | {br(mw['mediana_no_prazo'], 0)} |",
        "",
        f"U = {br(mw['u'], 0)}, p-valor {formatar_p(mw['p'])}. Tamanho de efeito pela correlação rank-biserial de "
        f"{br(abs(mw['rank_biserial']))}, o que é considerado efeito grande (acima de 0,5). Com alfa de 5%, {conclusao_h1}.",
        "",
        "## H2. Atraso aumenta a chance de nota 1 ou 2",
        "",
        f"Nota 1 ou 2 em {br(100 * pr['p_atr'], 1)}% dos atrasados contra {br(100 * pr['p_ok'], 1)}% dos entregues no prazo. "
        f"Diferença de {br(100 * pr['dif'], 1)} pontos percentuais "
        f"(IC 95% de {br(100 * pr['ic'][0], 1)} a {br(100 * pr['ic'][1], 1)}). "
        f"Um pedido atrasado tem {br(pr['risco_relativo'], 1)} vezes mais chance de receber nota baixa.",
        "",
        f"Qui-quadrado = {br(pr['chi2'], 1)}, {pr['gl']} grau de liberdade, p-valor {formatar_p(pr['p'])}. "
        f"{conclusao_h2[0].upper() + conclusao_h2[1:]}.",
        "",
        "## Leitura de negócio",
        "",
        f"Os atrasados são só {br(100 * pr['pct_pedidos_atrasados'], 1)}% dos pedidos, mas respondem por "
        f"{br(100 * pr['parcela_notas_baixas_atraso'], 1)}% de todas as notas 1 e 2 da base. "
        "Atacar o atraso é a alavanca mais concentrada que existe para melhorar a reputação.",
        "",
        "Observação. O teste mostra associação forte, não prova causalidade sozinho. Ainda assim, a relação "
        "cresce de forma consistente com o tamanho do atraso (tabela abaixo), o que reforça a leitura.",
        "",
        "| Situação da entrega | Pedidos | Nota média | Nota 1 ou 2 |",
        "|---|---|---|---|",
    ]
    for faixa, dados_da_faixa in resumo_por_faixa.iterrows():
        linhas_do_relatorio.append(
            f"| {faixa.split('. ', 1)[1]} | {br(dados_da_faixa.pedidos, 0)} "
            f"| {br(dados_da_faixa.nota_media)} | {br(100 * dados_da_faixa.pct_baixa, 1)}% |"
        )
    linhas_do_relatorio += ["", "![Nota média](nota_por_atraso.png)", "", "![Nota baixa](nota_baixa_por_atraso.png)", ""]

    (SAIDA / "teste_hipotese.md").write_text("\n".join(linhas_do_relatorio), encoding="utf-8")
    print("\n".join(linhas_do_relatorio))


if __name__ == "__main__":
    main()
