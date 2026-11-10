# Relatório de análise. Atraso na entrega e satisfação do cliente na Olist

Base pública da Olist com cerca de 100 mil pedidos, de 01/2017 a 08/2018. Dados tratados em PostgreSQL e no Databricks, camada ouro em `app/data/`. Os números deste relatório são calculados ao vivo na página Relatório do painel, a partir dos mesmos arquivos.

## Resumo executivo

1. **O atraso é a principal alavanca da nota.** Só 6,7% dos pedidos entregues e avaliados chegaram atrasados, mas eles respondem por 32,6% de todas as notas 1 e 2. Um pedido atrasado tem 62,4% de chance de receber nota 1 ou 2, contra 9,2% no prazo, 6,7 vezes mais.
2. **A relação aparece em três recortes diferentes.** Pedido a pedido (Mann-Whitney, efeito grande de 0,64), mês a mês (correlação de -0,87) e estado a estado (correlação de -0,88). Nenhum recorte sozinho prova causa, mas os três juntos tornam difícil explicar a queda da nota por outro motivo.
3. **A nota despenca nos três primeiros dias de atraso.** A chance de nota 1 ou 2 é 12,4% no dia prometido, 19,7% com 1 dia de atraso, 34,3% com 2 e 50,4% com 3. De 7 a 15 dias de atraso fica em 78,5%.
4. **O RJ é onde agir rende mais, e o problema é o caminho, não o vendedor.** O RJ tem 12,8% dos pedidos e 22,9% dos atrasos. Os mesmos 124 vendedores atrasam em média 12,2% dos pedidos para o RJ e 4,4% para SP. Se o RJ atrasasse na mesma taxa de SP, seriam cerca de 940 atrasos e 500 notas 1 e 2 a menos, 4,1% de todas as notas baixas da base.
5. **O prazo prometido não acompanha o risco de cada região.** O Nordeste tem quase a mesma folga média do Sudeste (11,2 contra 11,5 dias), mas atrasa o dobro (12,8% contra 6,1%), porque a entrega lá é menos previsível. Entre os 80% de pedidos do meio, a entrega no Nordeste varia 27 dias, contra 19 no Sudeste.
6. **O aviso de atraso precisa de teste, e o teste é lento.** Para enxergar uma queda de 5 pontos na nota baixa dos atrasados, o experimento precisa de cerca de 3 mil pedidos atrasados, o que leva perto de 6 meses no volume de 2018.

## Pergunta e dados

**Pergunta.** O que mais derruba a satisfação do cliente da Olist e onde agir primeiro?

| Arquivo da camada ouro | Linhas | O que tem |
|---|---|---|
| `resumo.parquet` | 1 | Totais da base, recompra e parcela das notas baixas que vêm de atraso |
| `kpis_mensais.parquet` | 20 | Pedidos, receita, nota média e taxa de atraso de cada mês |
| `entrega_por_estado.parquet` | 27 | Prazo prometido, entrega real, frete, atraso e nota por estado do cliente |
| `nota_por_faixa.parquet` | 5 | Nota média e percentual de nota 1 ou 2 por faixa de atraso |
| `categorias_abc.parquet` | 74 | Receita e curva ABC por categoria |
| `nota_por_dia_atraso.parquet` | 195 | Pedidos avaliados, notas baixas e soma das notas para cada dia em relação ao prometido |
| `entrega_por_regiao.parquet` | 5 | Percentis p10, p25, p50, p75 e p90 dos dias em relação ao prometido, por região |
| `nota_por_regiao_atraso.parquet` | 10 | Pedidos, notas baixas e soma das notas por região, separando no prazo e atrasado |
| `atraso_vendedor_destino.parquet` | 6.397 | Pedidos e atrasos de cada vendedor para RJ, SP, MG e ES, só pedidos de um vendedor |
| `recompra_primeira_compra.parquet` | 2 | Pessoas e quantas voltaram, pela situação da primeira compra |

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
7. Comparação pareada por vendedor. O mesmo vendedor entrega para dois destinos, então a diferença entre eles não vem de quem vende. Só pedidos de um vendedor e vendedores com 20 ou mais pedidos em cada destino, com teste de Wilcoxon pareado sobre a taxa de atraso de cada vendedor.
8. As cinco tabelas dos achados novos são calculadas no Databricks e em SQL e conferidas linha a linha. Os critérios de confirmação foram combinados antes de ler os números finais e estão em `analise/achados_relatorio.py`, que imprime cada número dos achados novos.

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

Dia a dia, o estrago se concentra nos três primeiros dias.

| Dias em relação ao prometido | Pedidos avaliados | Nota 1 ou 2 |
|---|---|---|
| 1 dia adiantado | 1.449 | 11,0% |
| no dia prometido | 1.280 | 12,4% |
| 1 dia de atraso | 819 | 19,7% |
| 2 dias de atraso | 536 | 34,3% |
| 3 dias de atraso | 496 | 50,4% |
| 7 a 15 dias de atraso, somados | | 78,5% |

Pelo critério combinado antes da análise, a nota baixa do dia 2 precisava ser pelo menos o dobro da do dia 0. Foi 2,8 vezes. Achado confirmado.

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
- O Nordeste tem folga parecida com a do Sudeste e atrasa o dobro, porque a entrega lá varia mais de um pedido para outro. A tabela abaixo mostra os dias em relação ao prometido (negativo é adiantado) entre os 80% de pedidos do meio.

  | Região | p10 | Mediana | p90 | Largura da faixa |
  |---|---|---|---|---|
  | Norte | -29 | -17 | -1 | 28 dias |
  | Nordeste | -24 | -13 | 3 | 27 dias |
  | Centro-Oeste | -22 | -13 | -2 | 20 dias |
  | Sul | -23 | -14 | -3 | 20 dias |
  | Sudeste | -21 | -12 | -2 | 19 dias |

  O Nordeste é a única região em que o p90 passa do dia prometido. Com a mesma folga média, uma faixa mais larga joga mais pedidos para depois da data.
- Frete e prazo sobem juntos (Spearman de 0,82 entre estados). O cliente longe dos centros paga mais e espera mais.

### 5. O atraso do RJ vem do caminho, não do vendedor

O RJ pode atrasar mais porque é atendido por vendedores piores ou porque o caminho até lá é pior. Para separar as duas coisas, a comparação usa o mesmo vendedor entregando para destinos diferentes.

| Comparação | Vendedores | Média das taxas dos vendedores | Taxa somada (atrasos sobre pedidos) | Wilcoxon p |
|---|---|---|---|---|
| RJ contra SP, todos os vendedores | 124 | 12,2% contra 4,4% | 12,8% contra 4,4% | 5,5e-15 |
| RJ contra MG, só vendedores de SP | 61 | 14,1% contra 5,8% | 15,0% contra 5,4% | 2,4e-08 |
| RJ contra SP, vendedores de fora dos dois estados | 32 | 9,5% contra 3,8% | 8,7% contra 4,1% | 0,0002 |

A média das taxas dá o mesmo peso a cada vendedor. A taxa somada pesa pelo volume. As duas contam a mesma história.

- O controle com MG tira a distância da conta. Belo Horizonte fica mais longe de São Paulo do que o Rio, e mesmo assim o mesmo vendedor paulista atrasa mais que o dobro para o RJ.
- O controle com vendedores de fora tira a vantagem de quem entrega no próprio estado.
- Pelo critério combinado antes da análise, as três comparações precisavam de p abaixo de 0,05 e diferença de pelo menos 3 pontos. As três passaram. Achado confirmado.
- O ES mostra o mesmo padrão. Vendedores de SP atrasam 12,9% para o ES e 5,3% para MG (24 vendedores com 10 ou mais pedidos em cada, p = 0,00009). O problema parece ser da rota para o Sudeste fora de SP e MG, não só do RJ.

### 6. A receita cresceu em 2017 e estabilizou em 2018

A receita mensal foi de R$ 120 mil em jan/17 para R$ 742 mil em dez/17, cerca de 6 vezes, com pico de R$ 1,0 mi na Black Friday. Em 2018 ficou estável, perto de R$ 918 mil por mês. O ticket médio oscilou pouco, entre R$ 125 e R$ 153, então o crescimento veio de mais pedidos e não de pedidos maiores. 18 de 74 categorias somam 81,3% da receita, com beleza e saúde na frente (R$ 1,25 mi).

### 7. Quase ninguém volta a comprar

Só 3,0% dos clientes compraram mais de uma vez. Quase toda venda depende de trazer cliente novo, o que torna a reputação (a nota) ainda mais importante para o negócio.

Achado secundário. Quem teve a primeira compra atrasada volta um pouco menos, 2,5% (161 de 6.345) contra 3,1% (2.651 de 86.684) de quem recebeu no prazo. São 0,52 ponto de diferença, cerca de 17% a menos, com qui-quadrado p = 0,021. O efeito é pequeno e tem uma ressalva. Quem comprou no fim da janela teve menos tempo para voltar, e se os atrasos se concentraram em algum período, a comparação fica torta. Serve como indício, não como número para meta.

## Robustez

O Nordeste tem nota menor que o Sudeste. Isso poderia vir da região, e não do atraso. Separando no prazo e atrasado dentro de cada região, a diferença entre regiões quase some.

| Região | Nota no prazo | Nota 1 ou 2 no prazo | Nota atrasado | Nota 1 ou 2 atrasado |
|---|---|---|---|---|
| Norte | 4,20 | 10,6% | 2,14 | 66,2% |
| Nordeste | 4,22 | 9,9% | 2,18 | 64,9% |
| Centro-Oeste | 4,26 | 9,6% | 2,19 | 64,1% |
| Sudeste | 4,30 | 9,2% | 2,29 | 62,0% |
| Sul | 4,30 | 8,8% | 2,37 | 59,7% |

No prazo, as cinco regiões ficam entre 4,20 e 4,30. Atrasado, entre 2,14 e 2,37. O que derruba a nota é o atraso, não o lugar.

## Recomendações e impacto estimado

| Prioridade | Ação | Número que sustenta | Impacto estimado |
|---|---|---|---|
| 1 | Rever a entrega até o cliente no RJ (transportadora, rota, última milha) | 12,8% dos pedidos e 22,9% dos atrasos. O mesmo vendedor atrasa 12,2% para o RJ e 4,4% para SP | Cerca de 500 notas 1 e 2 a menos (4,1% do total) se o RJ atrasasse como SP. Cerca de 350 se chegasse à média nacional |
| 2 | Prometer prazo por região | Nordeste com a folga do Sudeste, o dobro de atraso e faixa de entrega de 27 dias contra 19 | Cerca de 290 notas 1 e 2 a menos se os estados do Nordeste chegassem à média nacional |
| 3 | Avisar o cliente antes do primeiro dia de atraso, com teste A/B | Nota baixa vai de 12,4% no dia prometido para 34,3% com 2 dias de atraso | A medir no experimento abaixo |
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
- **Sem dado de transportadora nem de rota.** A comparação por vendedor mostra que o atraso do RJ não vem de quem vende, mas não diz se vem de uma transportadora, de uma rota ou de uma região da cidade. Esse é o primeiro corte para a operação investigar com dado interno.
- **Estado do cliente é o endereço mais recente da pessoa.** Em 18 de 65.114 pedidos de vendedor único para RJ, SP, MG e ES ele difere do endereço daquele pedido, o que não muda a comparação por vendedor.
- **Associação, não causa,** como dito na conferência.

## Próximos passos

1. Abrir o atraso do RJ por transportadora e por cidade, com dado interno da operação, já que o vendedor foi descartado como causa.
2. Calibrar o prazo prometido por região a partir do p90 da tabela do achado 4, para que 9 em cada 10 pedidos cheguem até a data.
3. Investigar os meses de crise (nov/17, fev/18 e mar/18), em especial se o atraso nesses meses foi mais longo do que nos outros.
4. Rodar o experimento do aviso de atraso com a queda mínima escolhida pelo negócio.

## Como reproduzir

```bash
pytest                           # testes, incluindo a página Relatório e a fórmula do tamanho de amostra
streamlit run app/Home.py        # página Relatório com todos os números deste documento
python analise/teste_hipotese.py # teste de hipótese pedido a pedido (precisa do CSV exportado do banco)
py -3.12 analise/achados_relatorio.py  # números dos achados novos, da robustez e os critérios de confirmação
```
