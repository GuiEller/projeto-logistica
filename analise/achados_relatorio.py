"""
Números oficiais dos achados novos do relatório, lidos da camada ouro já conferida.

Todo número que o relatório e o painel citam sobre esses achados sai daqui. Assim o texto
nunca leva um número da exploração que não passou pela conferência com o Postgres.

Os critérios foram combinados ANTES de olhar os números finais. Se um deles der
"não confirmado", o achado não entra nas recomendações sem uma conversa antes.
  Achado 1  O mesmo vendedor atrasa mais para o RJ. As três comparações com p < 0,05
            no Wilcoxon pareado e diferença de pelo menos 3 pontos na média das taxas.
  Achado 2  A nota baixa sobe rápido nos primeiros dias. Nota baixa no dia 2 de atraso
            pelo menos o dobro da do dia 0.

Entrada  app/data/*.parquet
Uso      py -3.12 analise/achados_relatorio.py
"""

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import chi2_contingency

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "app"))
from dados import comparar_destinos, num, pct  # noqa: E402  (as mesmas funções que o painel usa)

DADOS = RAIZ / "app" / "data"
ler = lambda nome: pd.read_parquet(DADOS / f"{nome}.parquet")


def vendedores():
    print("== Achado 1. Mesmo vendedor, destinos diferentes (pedidos de vendedor único, 20+ pedidos por destino)")
    t = ler("atraso_vendedor_destino")
    comparacoes = [
        ("RJ contra SP, todos os vendedores", ("RJ", "SP"), {}),
        ("RJ contra MG, só vendedores de SP", ("RJ", "MG"), {"origem": "SP"}),
        ("RJ contra SP, vendedores de fora dos dois", ("RJ", "SP"), {"fora_dos_destinos": True}),
    ]
    confirmado = True
    for rotulo, (a, b), extra in comparacoes:
        r = comparar_destinos(t, a, b, **extra)
        diferenca = r["media_a"] - r["media_b"]
        confirmado &= r["p_valor"] < 0.05 and diferenca >= 0.03
        print(f"  {rotulo}: {r['vendedores']} vendedores. Média das taxas {a} {pct(r['media_a'])}, {b} {pct(r['media_b'])}."
              f" Taxa somada {a} {pct(r['taxa_a'])}, {b} {pct(r['taxa_b'])}. Wilcoxon p = {r['p_valor']:.2g}")
    # ES fica fora do critério. Serve para ver se o padrão é do RJ ou de destinos fora de SP em geral.
    r = comparar_destinos(t, "ES", "MG", minimo=10, origem="SP")
    print(f"  ES contra MG, só vendedores de SP (10+ pedidos): {r['vendedores']} vendedores. Média das taxas"
          f" ES {pct(r['media_a'])}, MG {pct(r['media_b'])}. Wilcoxon p = {r['p_valor']:.2g}")
    return confirmado


def curva_por_dia():
    print("\n== Achado 2. Nota baixa dia a dia (dias de atraso, negativo é adiantado)")
    d = ler("nota_por_dia_atraso").set_index("dias_atraso")
    taxa = d.notas_baixas / d.pedidos
    for dia in range(-3, 8):
        print(f"  dia {dia:>3}: {pct(taxa[dia])} de nota baixa em {num(d.pedidos[dia])} pedidos")
    return taxa[2] >= 2 * taxa[0]


def faixa_por_regiao():
    print("\n== Faixa de entrega por região (dias em relação ao prometido, p10 a p90)")
    r = ler("entrega_por_regiao").assign(faixa=lambda d: d.p90 - d.p10).sort_values("faixa", ascending=False)
    for _, x in r.iterrows():
        print(f"  {x.regiao}: de {x.p10:.0f} a {x.p90:.0f} dias, faixa de {x.faixa:.0f} dias, mediana {x.p50:.0f},"
              f" {num(x.pedidos)} pedidos")


def nota_por_regiao():
    print("\n== Nota por região e situação (robustez)")
    n = ler("nota_por_regiao_atraso").assign(nota=lambda d: d.soma_notas / d.pedidos, baixa=lambda d: d.notas_baixas / d.pedidos)
    for atrasado, g in n.groupby("atrasado"):
        situacao = "atrasado" if atrasado else "no prazo"
        print(f"  {situacao}: nota de {num(g.nota.min(), 2)} a {num(g.nota.max(), 2)} entre regiões,"
              f" nota baixa de {pct(g.baixa.min())} a {pct(g.baixa.max())}")
        for _, x in g.iterrows():
            print(f"    {x.regiao}: nota {num(x.nota, 2)}, nota baixa {pct(x.baixa)}, {num(x.pedidos)} pedidos")


def recompra():
    print("\n== Recompra pela primeira compra (achado secundário)")
    r = ler("recompra_primeira_compra").set_index("primeira_atrasada")
    taxa = r.voltaram / r.pessoas
    tabela = [[r.voltaram[s], r.pessoas[s] - r.voltaram[s]] for s in (False, True)]
    p = chi2_contingency(tabela)[1]
    print(f"  Primeira no prazo: {pct(taxa[False])} voltaram ({num(r.voltaram[False])} de {num(r.pessoas[False])})")
    print(f"  Primeira atrasada: {pct(taxa[True])} voltaram ({num(r.voltaram[True])} de {num(r.pessoas[True])})")
    print(f"  Diferença de {num(100 * (taxa[False] - taxa[True]), 2)} pontos, qui-quadrado p = {p:.2g}")


if __name__ == "__main__":
    achado_1 = vendedores()
    achado_2 = curva_por_dia()
    faixa_por_regiao()
    nota_por_regiao()
    recompra()
    print()
    print(f"Critério achado 1: {'confirmado' if achado_1 else 'não confirmado'}")
    print(f"Critério achado 2: {'confirmado' if achado_2 else 'não confirmado'}")
