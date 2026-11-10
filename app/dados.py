"""Leitura dos Parquet da camada ouro, formatação no padrão brasileiro e o visual comum a todas as páginas."""

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DADOS = Path(__file__).parent / "data"

# Cor só nos dados. Azul é o dado principal de cada gráfico, laranja é sempre o atraso (o problema do projeto).
AZUL = "#1d5fbf"
DESTAQUE = "#d4581c"
NEUTRO = "#a3a8b0"
NEUTRO_CLARO = "#d9dde3"
TINTA = "#0a0a0a"
CINZA = "#5f6672"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@alt.theme.register("olist", enable=True)
def _tema():
    # O locale faz o Vega escrever 1.234,5 e "jan" em vez de 1,234.5 e "Jan". Sem ele, todo eixo sairia em inglês.
    return {
        "config": {
            "background": "transparent",
            "font": "Geist, system-ui, sans-serif",
            "view": {"stroke": None},
            "axis": {"labelColor": CINZA, "titleColor": CINZA, "labelFontSize": 12, "titleFontSize": 12,
                     "titleFontWeight": 500, "gridColor": "#eceef2", "domainColor": "#d0d4da", "tickColor": "#d0d4da"},
            "axisY": {"domain": False, "ticks": False},
            "legend": {"labelColor": CINZA, "titleColor": CINZA, "labelFontSize": 12, "titleFontSize": 12},
            "locale": {
                "number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["R$ ", ""]},
                "time": {
                    "dateTime": "%d/%m/%Y %H:%M", "date": "%d/%m/%Y", "time": "%H:%M", "periods": ["", ""],
                    "days": ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"],
                    "shortDays": ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"],
                    "months": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                               "setembro", "outubro", "novembro", "dezembro"],
                    "shortMonths": MESES,
                },
            },
        }
    }


@st.cache_data
def ler(nome: str) -> pd.DataFrame:
    # cache_data guarda o resultado na memória. Sem ele, cada clique num filtro releria o arquivo do disco.
    return pd.read_parquet(DADOS / f"{nome}.parquet")


@st.cache_data
def estados_geo() -> dict:
    # Malha dos estados do IBGE, com a sigla da UF em cada polígono para cruzar com a tabela de entrega.
    return json.loads((DADOS / "estados.geojson").read_text(encoding="utf-8"))


def resumo() -> pd.Series:
    return ler("resumo").iloc[0]


def ponderada(df: pd.DataFrame, coluna: str) -> float:
    # Média ponderada pelos pedidos. A média simples daria o mesmo peso a um estado com 40 pedidos e a SP.
    return (df[coluna] * df.pedidos).sum() / df.pedidos.sum()


def comparar_destinos(tabela: pd.DataFrame, destino_a: str, destino_b: str, minimo: int = 20,
                      origem: str | None = None, fora_dos_destinos: bool = False) -> dict:
    """Compara o atraso do MESMO vendedor para dois destinos (tabela atraso_vendedor_destino).

    Pareado porque assim a diferença não vem de quem vende, vem do caminho até o cliente.
    Vendedor só entra com `minimo` pedidos em cada destino. Com 3 pedidos, uma entrega atrasada vira 33%.
    """
    from scipy.stats import wilcoxon  # importado aqui para as páginas que não comparam não pagarem o custo

    t = tabela
    if origem is not None:
        t = t[t.estado_vendedor == origem]
    if fora_dos_destinos:
        # Vendedor do próprio destino entrega na vizinhança e puxaria a taxa daquele destino para baixo.
        t = t[~t.estado_vendedor.isin([destino_a, destino_b])]
    larga = t.pivot_table(index="vendedor_id", columns="estado", values=["pedidos", "atrasos"], aggfunc="sum")
    if larga.empty or destino_a not in larga["pedidos"] or destino_b not in larga["pedidos"]:
        larga = pd.DataFrame(columns=pd.MultiIndex.from_product([["pedidos", "atrasos"], [destino_a, destino_b]]))
    larga = larga[(larga["pedidos"][destino_a] >= minimo) & (larga["pedidos"][destino_b] >= minimo)]
    taxa = larga["atrasos"] / larga["pedidos"]
    pares = pd.DataFrame({"vendedor_id": larga.index, "taxa_a": taxa[destino_a].astype(float).values,
                          "taxa_b": taxa[destino_b].astype(float).values})
    # Com menos de 6 pares o Wilcoxon bilateral não chega a p < 0,05 nem no melhor caso. Sem teste, sem p-valor.
    p = wilcoxon(pares.taxa_a, pares.taxa_b).pvalue if len(pares) >= 6 else float("nan")
    soma = larga.sum()
    return {
        "vendedores": len(pares),
        # Média das taxas dá o mesmo peso a cada vendedor. A taxa somada pesa pelo volume. O relatório mostra as duas.
        "media_a": pares.taxa_a.mean(), "media_b": pares.taxa_b.mean(),
        "taxa_a": soma["atrasos"][destino_a] / soma["pedidos"][destino_a] if len(pares) else float("nan"),
        "taxa_b": soma["atrasos"][destino_b] / soma["pedidos"][destino_b] if len(pares) else float("nan"),
        "p_valor": float(p),
        "pares": pares,
    }


def num(x, casas=0):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, casas=1):
    return num(100 * x, casas) + "%"


def reais(x, casas=0):
    return "R$ " + num(x, casas)


def mes_br(ano_mes: str) -> str:
    # "2017-01" vira "jan/17", como se fala no dia a dia.
    ano, mes = ano_mes.split("-")
    return f"{MESES[int(mes) - 1]}/{ano[2:]}"


# A Olist grava a categoria sem acento e com sublinhado. Estas são as que aparecem no gráfico padrão.
CATEGORIAS = {
    "beleza_saude": "Beleza e saúde", "relogios_presentes": "Relógios e presentes", "cama_mesa_banho": "Cama, mesa e banho",
    "esporte_lazer": "Esporte e lazer", "informatica_acessorios": "Informática", "moveis_decoracao": "Móveis e decoração",
    "utilidades_domesticas": "Utilidades domésticas", "cool_stuff": "Presentes criativos", "automotivo": "Automotivo",
    "ferramentas_jardim": "Ferramentas e jardim", "brinquedos": "Brinquedos", "bebes": "Bebês", "perfumaria": "Perfumaria",
    "telefonia": "Telefonia", "moveis_escritorio": "Móveis de escritório", "papelaria": "Papelaria", "pcs": "Computadores",
    "pet_shop": "Pet shop", "eletroportateis": "Eletroportáteis", "instrumentos_musicais": "Instrumentos musicais",
    "sem_categoria": "Sem categoria", "eletronicos": "Eletrônicos", "fashion_bolsas_e_acessorios": "Bolsas e acessórios",
    "consoles_games": "Consoles e games", "construcao_ferramentas_construcao": "Construção",
    "malas_acessorios": "Malas", "eletrodomesticos_2": "Eletrodomésticos (linha 2)", "casa_construcao": "Casa e construção",
    "eletrodomesticos": "Eletrodomésticos", "agro_industria_e_comercio": "Agro, indústria e comércio",
}


def categoria_br(nome: str) -> str:
    return CATEGORIAS.get(nome, nome.replace("_", " ").capitalize())


def eixo_reais_mi(titulo=None):
    # Eixo em milhões no padrão brasileiro. O formato "~s" do Vega escreveria 0.2M.
    return alt.Axis(title=titulo, labelExpr="'R$ ' + replace(format(datum.value / 1e6, '.1f'), '.', ',') + ' mi'",
                    tickCount=5)


def desenhar(grafico):
    # theme=None faz o Streamlit usar o tema "olist" acima, com o locale brasileiro.
    st.altair_chart(grafico, width="stretch", theme=None)


def painel(titulo: str, chave: str, descricao: str | None = None):
    # Bloco branco com título e uma frase do que o gráfico mostra. A chave vira a classe CSS que pinta o fundo.
    bloco = st.container(border=True, key=f"painel-{chave}")
    bloco.markdown(f"#### {titulo}")
    if descricao:
        bloco.caption(descricao)
    return bloco


def mapa_atraso(estados: pd.DataFrame, altura: int = 420):
    """Mapa do Brasil com a taxa de atraso de cada estado. Estado fora do filtro fica cinza claro."""
    # O lookup cruza a sigla de cada polígono do IBGE com a linha do estado na tabela de entrega.
    campos = ["estado", "regiao", "pedidos", "taxa_atraso", "nota_media"]
    # Uma cor só, do claro ao escuro. Laranja porque atraso é sempre laranja no painel.
    escala = alt.Scale(range=["#fbe5d8", "#ec8f5c", DESTAQUE, "#7a2e0b"])
    poligonos = alt.Chart(alt.Data(values=estados_geo()["features"]))
    # Duas camadas. O Vega apaga o polígono que não tem valor no campo da cor, então o Brasil inteiro vai
    # primeiro em cinza, e os estados com dado vêm por cima. Sem o fundo, o mapa filtrado ficava com buracos.
    fundo = poligonos.mark_geoshape(fill=NEUTRO_CLARO, stroke="#ffffff", strokeWidth=1)
    dados = (
        poligonos.mark_geoshape(stroke="#ffffff", strokeWidth=1)
        .transform_lookup(lookup="properties.sigla", from_=alt.LookupData(estados[campos], "estado", campos))
        .transform_filter("isValid(datum.taxa_atraso)")
        .encode(
            color=alt.Color("taxa_atraso:Q", scale=escala,
                            legend=alt.Legend(title="Pedidos entregues depois do prazo", format=".0%",
                                              orient="bottom", gradientLength=220, titleLimit=300)),
            tooltip=[alt.Tooltip("properties.sigla:N", title="Estado"),
                     alt.Tooltip("taxa_atraso:Q", title="Atraso", format=".1%"),
                     alt.Tooltip("pedidos:Q", title="Pedidos", format=","),
                     alt.Tooltip("nota_media:Q", title="Nota média", format=".2f")],
        )
    )
    return (fundo + dados).project("mercator").properties(height=altura)


def conclusao(texto: str):
    # Toda página termina com a conclusão escrita. Gráfico sem conclusão obriga o leitor a fazer a análise.
    with st.container(border=True, key="painel-conclusao"):
        st.markdown(f"**Conclusão.** {texto}")


def rodape():
    st.caption("Base pública da Olist, pedidos de 01/2017 a 08/2018. Camada ouro processada no Databricks. "
               "Malha dos estados do IBGE.")
