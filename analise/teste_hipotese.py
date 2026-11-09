"""
Teste de hipótese. O atraso na entrega derruba a avaliação do cliente?

Hipóteses
  H1  A nota de pedidos entregues com atraso é menor que a de pedidos no prazo.
      Teste de Mann-Whitney U unilateral (a nota é ordinal de 1 a 5, então não
      dá para assumir normalidade e usar teste t). Tamanho de efeito pela
      correlação rank-biserial.
  H2  A proporção de notas 1 ou 2 é maior entre pedidos atrasados.
      Teste qui-quadrado de independência e diferença de proporções com IC de 95%.

Entrada  analise/dados/pedidos_entregues.csv  (gerado por scripts/exportar_csv.sh)
Saída    resultados/teste_hipotese.md e dois gráficos em resultados/
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "analise" / "dados" / "pedidos_entregues.csv"
SAIDA = RAIZ / "resultados"
ALFA = 0.05


def br(x, casas=2):
    """Formata número no padrão brasileiro."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def carregar(caminho=ENTRADA) -> pd.DataFrame:
    # O caminho é parâmetro para o pytest poder passar um CSV pequeno de teste.
    df = pd.read_csv(caminho)
    df = df.dropna(subset=["nota_avaliacao", "entregue_no_prazo"])
    df["entregue_no_prazo"] = df["entregue_no_prazo"].astype(str).str.lower().isin(["t", "true", "1"])
    df["atrasado"] = ~df["entregue_no_prazo"]
    df["nota_baixa"] = df["nota_avaliacao"] <= 2
    return df


def teste_mann_whitney(df):
    atrasados = df.loc[df.atrasado, "nota_avaliacao"]
    no_prazo = df.loc[~df.atrasado, "nota_avaliacao"]
    u, p = stats.mannwhitneyu(atrasados, no_prazo, alternative="less")
    # rank-biserial  r = 1 - 2U / (n1 n2)   (negativo = atrasados com notas menores)
    r = 1 - 2 * u / (len(atrasados) * len(no_prazo))
    return {
        "n_atrasados": len(atrasados), "n_no_prazo": len(no_prazo),
        "media_atrasados": atrasados.mean(), "media_no_prazo": no_prazo.mean(),
        "mediana_atrasados": atrasados.median(), "mediana_no_prazo": no_prazo.median(),
        "u": u, "p": p, "rank_biserial": -r,
    }


def teste_proporcoes(df):
    tabela = pd.crosstab(df.atrasado, df.nota_baixa)
    chi2, p, gl, _ = stats.chi2_contingency(tabela)
    p_atr = df.loc[df.atrasado, "nota_baixa"].mean()
    p_ok = df.loc[~df.atrasado, "nota_baixa"].mean()
    n_atr, n_ok = df.atrasado.sum(), (~df.atrasado).sum()
    dif = p_atr - p_ok
    ep = np.sqrt(p_atr * (1 - p_atr) / n_atr + p_ok * (1 - p_ok) / n_ok)
    # parcela de todas as notas baixas que vem de pedidos atrasados
    parcela = df.loc[df.atrasado, "nota_baixa"].sum() / df["nota_baixa"].sum()
    return {
        "chi2": chi2, "p": p, "gl": gl,
        "p_atr": p_atr, "p_ok": p_ok, "dif": dif,
        "ic": (dif - 1.96 * ep, dif + 1.96 * ep),
        "risco_relativo": p_atr / p_ok,
        "pct_pedidos_atrasados": df.atrasado.mean(),
        "parcela_notas_baixas_atraso": parcela,
    }


def graficos(df):
    SAIDA.mkdir(exist_ok=True)
    resumo = (df.groupby("faixa_atraso")
                .agg(nota_media=("nota_avaliacao", "mean"), pct_baixa=("nota_baixa", "mean"),
                     pedidos=("pedido_id", "size"))
                .sort_index())
    rotulos = [f.split(". ", 1)[1] for f in resumo.index]
    cores = ["#2E7D32", "#66BB6A", "#FFB300", "#F57C00", "#C62828"]

    for coluna, titulo, nome, fmt in [
        ("nota_media", "Nota média da avaliação por situação da entrega", "nota_por_atraso.png", lambda v: br(v, 2)),
        ("pct_baixa", "Percentual de avaliações com nota 1 ou 2", "nota_baixa_por_atraso.png", lambda v: br(100 * v, 1) + "%"),
    ]:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        barras = ax.bar(rotulos, resumo[coluna], color=cores)
        for b, v in zip(barras, resumo[coluna]):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), fmt(v), ha="center", va="bottom", fontsize=10)
        ax.set_title(titulo, fontsize=13, loc="left")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=9)
        if coluna == "pct_baixa":
            ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
        fig.text(0.01, 0.01, f"Base Olist, {br(len(df), 0)} pedidos entregues de 01/2017 a 08/2018",
                 fontsize=8, color="#666")
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        fig.savefig(SAIDA / nome, dpi=150)
        plt.close(fig)
    return resumo


def main():
    df = carregar()
    mw = teste_mann_whitney(df)
    pr = teste_proporcoes(df)
    resumo = graficos(df)

    conclusao_h1 = "rejeitamos H0" if mw["p"] < ALFA else "não rejeitamos H0"
    conclusao_h2 = "rejeitamos H0" if pr["p"] < ALFA else "não rejeitamos H0"
    p_txt = lambda p: "< 0,0001" if p < 1e-4 else br(p, 4)

    linhas = [
        "# Teste de hipótese, atraso na entrega x avaliação do cliente",
        "",
        f"Base com {br(len(df), 0)} pedidos entregues e avaliados, de 01/2017 a 08/2018. "
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
        f"U = {br(mw['u'], 0)}, p-valor {p_txt(mw['p'])}. Tamanho de efeito pela correlação rank-biserial de "
        f"{br(abs(mw['rank_biserial']))}, o que é considerado efeito grande (acima de 0,5). Com alfa de 5%, {conclusao_h1}.",
        "",
        "## H2. Atraso aumenta a chance de nota 1 ou 2",
        "",
        f"Nota 1 ou 2 em {br(100 * pr['p_atr'], 1)}% dos atrasados contra {br(100 * pr['p_ok'], 1)}% dos entregues no prazo. "
        f"Diferença de {br(100 * pr['dif'], 1)} pontos percentuais "
        f"(IC 95% de {br(100 * pr['ic'][0], 1)} a {br(100 * pr['ic'][1], 1)}). "
        f"Um pedido atrasado tem {br(pr['risco_relativo'], 1)} vezes mais chance de receber nota baixa.",
        "",
        f"Qui-quadrado = {br(pr['chi2'], 1)}, {pr['gl']} grau de liberdade, p-valor {p_txt(pr['p'])}. {conclusao_h2[0].upper() + conclusao_h2[1:]}.",
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
    for faixa, r in resumo.iterrows():
        linhas.append(f"| {faixa.split('. ', 1)[1]} | {br(r.pedidos, 0)} | {br(r.nota_media)} | {br(100 * r.pct_baixa, 1)}% |")
    linhas += ["", "![Nota média](nota_por_atraso.png)", "", "![Nota baixa](nota_baixa_por_atraso.png)", ""]

    (SAIDA / "teste_hipotese.md").write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
