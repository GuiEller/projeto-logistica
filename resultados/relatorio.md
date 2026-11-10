# Relatório de análise. Atraso na entrega e satisfação do cliente na Olist

Base pública da Olist com cerca de 100 mil pedidos, de 01/2017 a 08/2018. Dados tratados em PostgreSQL e no Databricks, camada ouro em `app/data/`. Os números deste relatório são calculados ao vivo na página Relatório do painel, a partir dos mesmos arquivos.

## Resumo executivo

1. **O atraso é a principal alavanca da nota.** Só 6,7% dos pedidos entregues e avaliados chegaram atrasados, mas eles respondem por 32,6% de todas as notas 1 e 2. Um pedido atrasado tem 62,4% de chance de receber nota 1 ou 2, contra 9,2% no prazo, 6,7 vezes mais.
2. **A relação aparece em três recortes diferentes.** Pedido a pedido (Mann-Whitney, efeito grande de 0,64), mês a mês (correlação de -0,87) e estado a estado (correlação de -0,88). Nenhum recorte sozinho prova causa, mas os três juntos tornam difícil explicar a queda da nota por outro motivo.
3. **O RJ é onde agir rende mais.** Tem 12,8% dos pedidos e 22,9% dos atrasos. Se atrasasse na mesma taxa de SP, seriam cerca de 940 atrasos e 500 notas 1 e 2 a menos, 4,1% de todas as notas baixas da base.
4. **O prazo prometido não acompanha o risco de cada região.** O Nordeste tem quase a mesma folga média do Sudeste (11,2 contra 11,5 dias), mas atrasa o dobro (12,8% contra 6,1%).
5. **O aviso de atraso precisa de teste, e o teste é lento.** Para enxergar uma queda de 5 pontos na nota baixa dos atrasados, o experimento precisa de cerca de 3 mil pedidos atrasados, o que leva perto de 6 meses no volume de 2018.

## Pergunta e dados

**Pergunta.** O que mais derruba a satisfação do cliente da Olist e onde agir primeiro?

| Arquivo da camada ouro | Linhas | O que tem |
|---|---|---|
| `resumo.parquet` | 1 | Totais da base, recompra e parcela das notas baixas que vêm de atraso |
| `kpis_mensais.parquet` | 20 | Pedidos, receita, nota média e taxa de atraso de cada mês |
| `entrega_por_estado.parquet` | 27 | Prazo prometido, entrega real, frete, atraso e nota por estado do cliente |
| `nota_por_faixa.parquet` | 5 | Nota média e percentual de nota 1 ou 2 por faixa de atraso |
| `categorias_abc.parquet` | 74 | Receita e curva ABC por categoria |

**Definições.**

- **Atrasado** é o pedido entregue depois da data estimada que a Olist mostrou na compra.
- **Nota baixa** é nota 1 ou 2, numa escala de 1 a 5. Avaliação duplicada fica com a mais recente.
- **Cliente** é a pessoa (`customer_unique_id`), e não o cadastro do pedido.
- **Receita** é a soma do valor dos itens, sem frete, vinda da tabela de itens. Frete, atraso e nota vêm da tabela de pedidos, um pedido por linha.

## Metodologia

1. Pipeline local em PostgreSQL (staging, modelo estrela, testes de integridade) e o mesmo tratamento refeito no Databricks em três camadas (bronze, prata, ouro). A camada ouro foi conferida contra o PostgreSQL em pedidos, receita e clientes antes de alimentar o painel.
2. Teste de hipótese pedido a pedido em `analise/teste_hipotese.py`. Mann-Whitney U para a nota (ordinal, sem distribuição normal) e qui-quadrado para a proporção de notas baixas. Detalhes em [`teste_hipotese.md`](teste_hipotese.md).
3. Correlação por mês (Pearson, 20 meses) e por estado (Spearman, 27 estados), com intervalo de confiança de 95% pela transformação de Fisher. Spearman entre estados porque a relação não precisa ser reta e estados com poucos pedidos não devem puxar o resultado.
4. Mês fora do padrão definido pela regra do boxplot (taxa de atraso acima de Q3 + 1,5 vezes o intervalo interquartil), para a regra decidir e não o olho.
5. Impacto das recomendações estimado como atrasos evitados vezes a diferença de chance de nota baixa entre atrasado e no prazo (53,2 pontos percentuais).
6. Tamanho de amostra do experimento pelo teste z de duas proporções, bilateral, com alfa de 5% e poder de 80%.

## Conferência dos números

**Avaliação geral. Pronto para compartilhar, com as ressalvas abaixo.** Todos os números do painel batem com o SDD e entre si. A única diferença encontrada é de base, não de cálculo.

| Número | Valor conferido | Resultado |
|---|---|---|
| Pedidos atrasados | 6,7% dos entregues e avaliados, 6,8% dos entregues | Confere. Bases diferentes, ver ressalva 1 |
| Notas 1 e 2 que vêm de atraso | 32,6% (soma das faixas e `resumo` dão o mesmo valor) | Confere |
| Nota média no prazo e com atraso | 4,29 e 2,27 | Confere com o teste de hipótese |
| Chance de nota baixa, atrasado contra no prazo | 62,4% contra 9,2%, razão de 6,75 | Confere |
| RJ, parcela dos pedidos e dos atrasos | 12,8% e 22,9% | Confere |
| Atraso no Nordeste e em SP | 12,8% e 4,5% | Confere |
| Folga média entre prometido e real | 11,8 dias | Confere |
| Categorias classe A | 18 de 74, com 81,3% da receita. Participações somam 100% | Confere |
| Receita | R$ 13,59 mi na base inteira, R$ 13,45 mi na janela de 01/2017 a 08/2018 | Confere. A soma das categorias bate com a janela |
| Médias por região | Ponderadas pelos pedidos, nunca média das médias | Confere no código do painel |

**Ressalvas para quem lê.**

1. **O total de pedidos muda de um gráfico para outro, e isso é proposital.** São quatro bases, cada uma certa para a sua pergunta.

   | Base | Pedidos | Onde aparece |
   |---|---|---|
   | Todos os pedidos da base | 99.441 | Receita total, clientes e recompra |
   | Pedidos de 01/2017 a 08/2018 | 97.905 | Receita mensal e ticket médio |
   | Entregues com estado do cliente | 96.203 | Mapa e ranking de atraso (6,8%) |
   | Entregues e avaliados | 95.560 | Faixas de atraso e teste de hipótese (6,7%) |

2. **Associação não é causa.** Os testes mostram que atraso e nota baixa andam juntos de forma forte e consistente. A prova de causa viria do experimento da seção de A/B.
3. **Os 14 mil clientes de alto valor da recomendação 4** vêm da segmentação RFM da análise SQL 04 e não foram reconferidos nesta rodada, porque dependem do banco local.

## Achados

### 1. O atraso derruba a nota pedido a pedido

| Situação da entrega | Pedidos | Nota média | Nota 1 ou 2 |
|---|---|---|---|
| 10 ou mais dias adiantado | 61.270 | 4,32 | 8,9% |
| até 10 dias adiantado ou no dia | 27.912 | 4,22 | 10,1% |
| 1 a 3 dias de atraso | 1.851 | 3,29 | 32,1% |
| 4 a 7 dias de atraso | 1.748 | 2,10 | 67,7% |
| mais de 7 dias de atraso | 2.779 | 1,70 | 79,3% |

A nota cai a cada faixa, e o salto maior acontece logo no primeiro dia de atraso (de 10,1% para 32,1% de nota baixa). Mann-Whitney com p-valor abaixo de 0,0001 e correlação rank-biserial de 0,64, efeito grande.

### 2. Nos meses em que o atraso subiu, a nota caiu

Correlação de Pearson de -0,87 entre a taxa de atraso e a nota média dos 20 meses (IC 95% de -0,95 a -0,70). Três meses saem do padrão pela regra do boxplot.

| Mês | Pedidos | Atraso | Nota média |
|---|---|---|---|
| nov/17 (Black Friday) | 7.421 | 12,4% | 3,95 |
| fev/18 | 6.624 | 14,1% | 3,86 |
| mar/18 | 7.168 | 19,0% | 3,76 |
| outros 17 meses, ponderado pelos pedidos | | 4,5% | 4,19 |

**Cuidado com este número.** Sem esses três meses, a correlação cai para -0,44 e deixa de ser significativa a 5% (p = 0,08). A relação mensal existe, mas é puxada pelos picos. Por isso a prova principal continua sendo o teste pedido a pedido.

Um detalhe que vale investigar. Se a nota do mês dependesse só da mistura entre pedidos no prazo e atrasados, março de 2018 teria nota 3,91. A nota real foi 3,76. Nos meses de crise a nota caiu mais do que a mistura explica, o que sugere atrasos mais longos nesses meses ou um efeito que respinga até nos pedidos entregues no prazo.

### 3. Estados que atrasam mais têm nota menor

Correlação de Spearman de -0,88 entre taxa de atraso e nota média dos 27 estados (IC 95% de -0,94 a -0,75). Com só os 21 estados que têm 300 pedidos ou mais, a correlação fica em -0,92. Correlação entre estados não fala de cada pedido (falácia ecológica), mas aqui ela confirma no mapa o que o teste já mostrou pedido a pedido.

### 4. O atraso se concentra no RJ e no Nordeste

| Região | Pedidos | Atraso | Folga média (dias) | Frete médio | Nota média |
|---|---|---|---|---|---|
| Sudeste | 66.024 | 6,1% | 11,5 | R$ 19,89 | 4,18 |
| Sul | 13.766 | 5,9% | 13,0 | R$ 24,37 | 4,19 |
| Nordeste | 9.016 | 12,8% | 11,2 | R$ 36,05 | 3,97 |
| Centro-Oeste | 5.605 | 6,5% | 12,3 | R$ 26,62 | 4,13 |
| Norte | 1.792 | 8,6% | 15,5 | R$ 41,34 | 4,03 |

- O RJ tem 12,8% dos pedidos e 22,9% dos atrasos, com 12,2% de atraso contra 4,5% em SP. Nenhum outro estado junta tanto volume com tanta falha.
- AL (21,5%) e MA (17,5%) atrasam mais que o RJ, mas têm 31 e 17 vezes menos pedidos.
- O Nordeste tem folga parecida com a do Sudeste e atrasa o dobro. Mesma folga média com atraso diferente indica que a entrega no Nordeste varia mais de um pedido para outro. É uma hipótese, a confirmar com o desvio padrão do tempo de entrega por pedido.
- Frete e prazo sobem juntos (Spearman de 0,82 entre estados). O cliente longe dos centros paga mais e espera mais.

### 5. A receita cresceu em 2017 e estabilizou em 2018

A receita mensal foi de R$ 120 mil em jan/17 para R$ 742 mil em dez/17, cerca de 6 vezes, com pico de R$ 1,0 mi na Black Friday. Em 2018 ficou estável, perto de R$ 918 mil por mês. O ticket médio oscilou pouco, entre R$ 125 e R$ 153, então o crescimento veio de mais pedidos e não de pedidos maiores. 18 de 74 categorias somam 81,3% da receita, com beleza e saúde na frente (R$ 1,25 mi).

### 6. Quase ninguém volta a comprar

Só 3,0% dos clientes compraram mais de uma vez. Quase toda venda depende de trazer cliente novo, o que torna a reputação (a nota) ainda mais importante para o negócio.

## Recomendações e impacto estimado

| Prioridade | Ação | Número que sustenta | Impacto estimado |
|---|---|---|---|
| 1 | Atacar o atraso no RJ | 12,8% dos pedidos e 22,9% dos atrasos | Cerca de 500 notas 1 e 2 a menos (4,1% do total) se o RJ atrasasse como SP. Cerca de 350 se chegasse à média nacional |
| 2 | Prometer prazo por região | Nordeste com a folga do Sudeste e o dobro de atraso | Cerca de 290 notas 1 e 2 a menos se os estados do Nordeste chegassem à média nacional |
| 3 | Avisar o cliente antes de atrasar, com teste A/B | 62,4% dos atrasados dão nota 1 ou 2 | A medir no experimento abaixo |
| 4 | Programa de segunda compra para clientes de alto valor | Recompra de 3,0%. Cerca de 14 mil clientes de alto valor compraram uma vez | Não estimado nesta rodada |

O impacto supõe que o pedido que deixa de atrasar passa a ser avaliado como um pedido no prazo. Como os testes mostram associação, o número real tende a ser menor. Ele serve para ordenar as ações, não como meta.

## Desenho do experimento da recomendação 3

**Hipótese.** Avisar o cliente com a nova data antes do prazo estourar reduz a chance de nota 1 ou 2 entre os pedidos que atrasam.

- **Quem entra.** Pedidos com atraso previsto (a transportadora sinaliza que não vai cumprir a data). Sorteio por cliente, para a mesma pessoa não cair nos dois grupos.
- **Grupos.** Controle sem aviso e tratamento com aviso, 50% para cada.
- **Métrica principal.** Percentual de nota 1 ou 2. Hoje é 62,4% entre os atrasados.
- **Métricas secundárias.** Nota média, reclamações no atendimento e recompra em 6 meses.
- **Métrica de proteção.** Nota dos pedidos que recebem aviso e acabam chegando no prazo, para o aviso não piorar quem não atrasaria.
- **Parâmetros.** Alfa de 5%, poder de 80%, teste bilateral.

| Queda mínima que o teste enxerga | Pedidos atrasados por grupo | Total | Meses de coleta no volume de 2018 |
|---|---|---|---|
| 3 pontos (62,4% para 59,4%) | 4.152 | 8.304 | 16,0 |
| 5 pontos | 1.507 | 3.014 | 5,8 |
| 8 pontos | 595 | 1.190 | 2,3 |
| 10 pontos | 383 | 766 | 1,5 |

Em 2018 atrasaram cerca de 518 pedidos por mês, e só eles entram no teste. A decisão de negócio é escolher a menor queda que justificaria o custo do aviso e aceitar o prazo correspondente. Durante o teste, conferir se os grupos ficaram do tamanho esperado (diferença grande indica erro no sorteio) e não encerrar antes da hora só porque o p-valor ficou abaixo de 5% num dia. Olhar o resultado todo dia e parar no primeiro p-valor bom aumenta muito a chance de falso positivo.

## Limitações

- **Período fechado.** Os dados vão até 08/2018. O relatório descreve aquele período, não o presente da Olist.
- **Só pedidos avaliados entram na análise de nota.** Quem não avaliou pode ter outra experiência, e ninguém sabe se melhor ou pior.
- **Sem dado de transportadora nem de rota.** Não dá para saber se o atraso do RJ vem de uma transportadora, de um vendedor ou da região de entrega. Esse é o primeiro corte para a operação investigar.
- **Associação, não causa,** como dito na conferência.

## Próximos passos

1. Abrir o atraso do RJ por vendedor e por cidade, para achar se ele se concentra em poucos pontos.
2. Medir o desvio padrão do tempo de entrega por região, para confirmar a hipótese do achado 4 e calibrar o prazo por região.
3. Investigar os meses de crise (nov/17, fev/18 e mar/18), em especial se o atraso nesses meses foi mais longo do que nos outros.
4. Rodar o experimento do aviso de atraso com a queda mínima escolhida pelo negócio.

## Como reproduzir

```bash
pytest                           # testes, incluindo a página Relatório e a fórmula do tamanho de amostra
streamlit run app/Home.py        # página Relatório com todos os números deste documento
python analise/teste_hipotese.py # teste de hipótese pedido a pedido (precisa do CSV exportado do banco)
```
