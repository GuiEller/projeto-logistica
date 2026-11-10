"""Leitura dos Parquet da camada ouro, formatação no padrão brasileiro e o visual comum a todas as páginas."""

import json
import math
from pathlib import Path
from statistics import NormalDist

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


def tamanho_amostra(p1: float, p2: float, alfa: float = 0.05, poder: float = 0.8) -> int:
    """Pedidos por grupo para um teste A/B de duas proporções (bilateral) enxergar a diferença entre p1 e p2."""
    # Fórmula clássica do teste z de duas proporções. NormalDist é da biblioteca padrão, sem dependência nova.
    # alfa é a chance aceita de ver efeito que não existe. Poder é a chance de ver o efeito quando ele existe.
    z = NormalDist().inv_cdf
    media = (p1 + p2) / 2
    termo = z(1 - alfa / 2) * math.sqrt(2 * media * (1 - media)) + z(poder) * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return math.ceil(termo ** 2 / (p1 - p2) ** 2)


def razao(parte: float, total: float) -> float:
    # Divisão que não quebra num estado sem nenhum pedido no grupo. Sem dado vira nan e aparece como traço.
    return parte / total if total else float("nan")


def faixas_do_estado(uf: str | None) -> pd.DataFrame:
    """Pedidos, notas baixas e nota média por faixa de atraso, de um estado ou do Brasil inteiro."""
    t = ler("faixa_por_estado")
    t = t[t.estado == uf] if uf else t
    # Soma das contagens e só depois a divisão. Média das notas médias dos estados daria peso igual a RR e SP.
    f = t.groupby("faixa_atraso", as_index=False)[["pedidos", "notas_baixas", "soma_notas"]].sum()
    # O prefixo "1. ", "2. " existe só para ordenar. Na tela, sai.
    f["situacao"] = f.faixa_atraso.str.split(". ", n=1).str[1]
    f["atrasado"] = f.faixa_atraso.str[0].astype(int) >= 3
    f["nota_media"] = f.soma_notas / f.pedidos
    f["pct_nota_baixa"] = f.notas_baixas / f.pedidos
    return f.sort_values("faixa_atraso")


def num(x, casas=0):
    if pd.isna(x):
        return "sem dado"
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


# Estados pequenos do litoral não cabem a sigla dentro. Ela vai para o mar, numa coluna, com uma linha até o estado.
SIGLA_NO_MAR = {"RN": (-33.4, -5.3), "PB": (-33.4, -6.8), "PE": (-33.4, -8.3), "AL": (-33.4, -9.8),
                "SE": (-33.4, -11.3), "ES": (-38.2, -20.6), "RJ": (-41.2, -24.4)}
# O DF fica dentro de GO. A sigla de GO sai um pouco do centro para as duas não se encostarem.
SIGLA_DESLOCADA = {"GO": (-50.4, -15.0)}


@st.cache_data
def siglas_estados() -> pd.DataFrame:
    """Onde escrever a sigla de cada estado: no centro do maior polígono, ou no mar para os pequenos do litoral."""
    linhas = []
    for f in estados_geo()["features"]:
        geo = f["geometry"]
        aneis = [geo["coordinates"][0]] if geo["type"] == "Polygon" else [p[0] for p in geo["coordinates"]]
        # Centro de área do maior anel (fórmula do polígono). A média dos vértices puxaria para o litoral recortado.
        melhor = (0, 0, 0)
        for anel in aneis:
            a = cx = cy = 0
            for (x0, y0), (x1, y1) in zip(anel, anel[1:]):
                c = x0 * y1 - x1 * y0
                a, cx, cy = a + c, cx + (x0 + x1) * c, cy + (y0 + y1) * c
            if abs(a) > melhor[0]:
                melhor = (abs(a), cx / (3 * a), cy / (3 * a))
        uf = f["properties"]["sigla"]
        lon, lat = melhor[1], melhor[2]
        lon_t, lat_t = SIGLA_NO_MAR.get(uf) or SIGLA_DESLOCADA.get(uf) or (lon, lat)
        linhas.append({"estado": uf, "lon": lon, "lat": lat, "lon_t": lon_t, "lat_t": lat_t,
                       "no_mar": uf in SIGLA_NO_MAR})
    return pd.DataFrame(linhas)


def mapa_atraso(estados: pd.DataFrame, altura: int = 420, uf: str | None = None, campo: str = "taxa_atraso",
                titulo: str = "Pedidos entregues depois do prazo"):
    """Mapa do Brasil pintado por `campo`, com a sigla de cada estado e clique para escolher um estado.

    Estado fora do filtro fica cinza claro. Com `uf`, os outros estados ficam apagados e o escolhido ganha contorno.
    """
    campos = list(dict.fromkeys(["estado", "pedidos", campo]))
    # Uma cor só, do claro ao escuro. Laranja porque atraso é sempre laranja no painel.
    escala = alt.Scale(range=["#fbe5d8", "#ec8f5c", DESTAQUE, "#7a2e0b"])
    # Duas camadas de polígonos. O Vega apaga o polígono que não tem valor no campo da cor, então o Brasil inteiro
    # vai primeiro em cinza, e os estados com dado vêm por cima. Sem o fundo, o mapa filtrado ficava com buracos.
    fundo = alt.Chart(alt.Data(values=estados_geo()["features"])).mark_geoshape(
        fill=NEUTRO_CLARO, stroke="#ffffff", strokeWidth=1)
    destacado = f"datum.estado == '{uf}'"
    visivel = destacado if uf else "true"
    clique = alt.selection_point(name="uf", fields=["estado"], on="click")
    dados = (
        alt.Chart(alt.Data(values=estados_geo()["features"]))
        .mark_geoshape(cursor="pointer")
        .transform_lookup(lookup="properties.sigla", from_=alt.LookupData(estados[campos], "estado", campos))
        .transform_filter(f"isValid(datum['{campo}'])")
        .encode(
            color=alt.Color(f"{campo}:Q", scale=escala,
                            legend=alt.Legend(title=titulo, format=".0%", orient="bottom", gradientLength=220,
                                              titleLimit=320)),
            # Com um estado escolhido, os outros perdem força em vez de sumir. O mapa continua dando o contexto.
            opacity=alt.condition(visivel, alt.value(1), alt.value(0.3)),
            stroke=alt.condition(destacado, alt.value(TINTA), alt.value("#ffffff")),
            strokeWidth=alt.condition(destacado, alt.value(2), alt.value(1)),
            tooltip=[alt.Tooltip("estado:N", title="Estado"), alt.Tooltip(f"{campo}:Q", title=titulo, format=".1%"),
                     alt.Tooltip("pedidos:Q", title="Pedidos", format=",")],
        )
        .add_params(clique)
    )
    # Sigla branca sobre os laranjas escuros e preta sobre os claros. No mar, sempre preta.
    rotulos = siglas_estados().merge(estados[["estado", campo]], on="estado", how="left")
    corte = rotulos[campo].quantile(0.6)
    rotulos["clara"] = ~rotulos.no_mar & (rotulos[campo] >= corte)
    rotulos["visivel"] = (rotulos.estado == uf) if uf else True
    # A linha termina no ponto do mar e a sigla fica um pouco à direita dela, para a linha não riscar a letra.
    rotulos["lon_sigla"] = rotulos.lon_t + rotulos.no_mar * 1.3
    linhas = alt.Chart(rotulos).transform_filter("datum.no_mar").mark_rule(color=CINZA, strokeWidth=0.8).encode(
        longitude="lon:Q", latitude="lat:Q", longitude2="lon_t:Q", latitude2="lat_t:Q")
    siglas = alt.Chart(rotulos).mark_text(fontSize=10, fontWeight=600, cursor="pointer").encode(
        longitude="lon_sigla:Q", latitude="lat_t:Q", text="estado:N",
        color=alt.condition("datum.clara", alt.value("#ffffff"), alt.value(TINTA)),
        opacity=alt.condition("datum.visivel", alt.value(1), alt.value(0.35)),
        tooltip=[alt.Tooltip("estado:N", title="Estado")],
    # Uma seleção própria na sigla, porque clicar em cima das letras também precisa escolher o estado.
    # O Vega não aceita a mesma seleção em duas camadas ("Duplicate signal name"), então são duas.
    ).add_params(alt.selection_point(name="uf_sigla", fields=["estado"], on="click"))
    return alt.layer(fundo, dados, linhas, siglas).project("mercator").properties(height=altura)


# ------------------------------------------------------------------ filtro por estado
# O estado escolhido vive em st.session_state["filtro_uf"] e vale em todas as páginas que filtram.
# O clique no gráfico e a caixa de seleção escrevem no mesmo lugar, então os dois sempre mostram o mesmo estado.
BRASIL = "Brasil inteiro"


def estado_escolhido() -> str | None:
    return st.session_state.get("filtro_uf")


def alternar(atual, clicado):
    """Clicar de novo no que já está escolhido desfaz a escolha. Clique em outro item troca. Sem clique, limpa."""
    return None if clicado == atual else clicado


def escolher_estado(uf: str | None):
    st.session_state["filtro_uf"] = uf
    st.session_state["seletor_uf"] = uf or BRASIL


def desenhar_clicavel(grafico, chave: str, parametros: tuple = ("uf", "uf_sigla"), campo: str = "estado"):
    """Desenha um gráfico em que o clique escolhe o estado do filtro. Lê a primeira seleção marcada."""
    # A chave muda com o estado escolhido. Assim a seleção interna do gráfico zera quando o filtro muda pela caixa,
    # e o segundo clique no mesmo estado chega ao callback como um clique novo, que o alternar transforma em limpar.
    chave = f"{chave}-{estado_escolhido()}"

    def ao_clicar():
        selecao = st.session_state[chave].selection
        marcados = [m for p in parametros for m in selecao.get(p, [])]
        escolher_estado(alternar(estado_escolhido(), marcados[0][campo] if marcados else None))

    # O Altair sobe as seleções das camadas para o topo do gráfico. Só as que existem entram no selection_mode.
    presentes = [p["name"] for p in grafico.to_dict().get("params", [])]
    st.altair_chart(grafico, width="stretch", theme=None, key=chave, on_select=ao_clicar,
                    selection_mode=[p for p in parametros if p in presentes])


def barra_de_filtro(pedidos_por_estado: pd.Series, base: str) -> str | None:
    """Caixa de seleção do estado, para quem usa teclado, e a frase que diz o que está filtrado."""
    st.session_state.setdefault("seletor_uf", estado_escolhido() or BRASIL)

    def trocar():
        valor = st.session_state["seletor_uf"]
        st.session_state["filtro_uf"] = None if valor == BRASIL else valor

    caixa, botao, frase = st.columns([2, 2, 8], vertical_alignment="bottom")
    caixa.selectbox("Estado", [BRASIL] + sorted(pedidos_por_estado.index), key="seletor_uf", on_change=trocar)
    uf = estado_escolhido()
    if uf:
        botao.button("Ver Brasil inteiro", on_click=escolher_estado, args=(None,), width="stretch")
        n = int(pedidos_por_estado.get(uf, 0))
        aviso = " Amostra pequena, leia com cuidado." if n < 300 else ""
        frase.caption(f"Filtrando {uf}, com {num(n)} {base}.{aviso} Clique de novo no estado para voltar ao Brasil inteiro.")
    else:
        frase.caption("Clique num estado do mapa ou escolha na lista para filtrar a página.")
    return uf


def conclusao(texto: str):
    # Toda página termina com a conclusão escrita. Gráfico sem conclusão obriga o leitor a fazer a análise.
    with st.container(border=True, key="painel-conclusao"):
        st.markdown(f"**Conclusão.** {texto}")


def rodape():
    st.caption("Base pública da Olist, pedidos de 01/2017 a 08/2018. Camada ouro processada no Databricks. "
               "Malha dos estados do IBGE.")
