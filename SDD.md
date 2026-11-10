# SDD | Olist Logística

Documento de desenho do projeto (Software Design Document). Explica o que vamos construir, com quais ferramentas, em que ordem e, principalmente, **por que** cada coisa existe.

| | |
|---|---|
| Autor | Guilherme Eler |
| Início | 27/10/2026 |
| Duração prevista | 11 dias úteis, prazo flexível |
| Status | Dividido em duas fases, cada uma com um post no LinkedIn. Fase 1 (PostgreSQL e SQL) concluída em 03/11/2026. Fase 2 (Databricks e painel) em seguida |

---

## 1. Por que este projeto existe

Este projeto tem dois objetivos, e os dois têm o mesmo peso.

1. **Aprender de ponta a ponta.** Passar por todas as etapas de um trabalho real de dados, que são extrair, guardar, tratar, modelar, testar, analisar e comunicar. Em cada etapa, entender o porquê das escolhas, e não só o como.
2. **Ter um portfólio que prova o que as vagas pedem.** Numa varredura de 63 vagas de dados de nível de entrada na Gupy (outubro de 2026), os itens mais pedidos foram SQL (75%), Power BI (68%), Python (65%), dashboards (63%), Excel (52%), KPIs (33%), nuvem (29%), automação (22%), ETL (21%) e modelagem de dados (19%). Databricks e Spark apareceram em 10 vagas. Os setores que mais contratam são vendas e varejo, finanças e logística.

Até agora o portfólio do Guilherme é todo de futebol. Este é o primeiro projeto de negócio tradicional.

## 2. A pergunta de negócio

> **O que mais pesa na satisfação do cliente de um marketplace, e por onde começar a agir?**

Todo o projeto existe para responder essa pergunta. Cada tabela, cada gráfico e cada teste precisa ajudar a respondê-la. Se alguma coisa não ajuda, não entra.

**Por que começar pela pergunta.** Projeto de portfólio que começa pela ferramenta ("vou fazer algo com Spark") vira tutorial. Projeto que começa pela pergunta vira análise, e análise é o que o analista de dados entrega na empresa.

## 3. O que está dentro e o que está fora

**Dentro**
- Vendas, entrega (prazo, atraso, frete) e avaliação do cliente.
- Pipeline local em PostgreSQL e pipeline na nuvem em Databricks, chegando ao mesmo resultado.
- Teste de hipótese formal sobre atraso e nota.
- Painel em Streamlit publicado com link aberto.

**Fora, de propósito**
- Modelo de machine learning. Fica para o próximo projeto (risco de crédito).
- Dados de geolocalização (o CSV de 1 milhão de linhas). Não ajudam a responder a pergunta e pesam no processamento.
- Power BI e Supabase. O porquê está na seção 5.

## 4. Os dados

Base pública da Olist, um marketplace brasileiro real, com dados anonimizados de 2016 a 2018. Licença MIT, disponível no [GitHub da Olist](https://github.com/olist/work-at-olist-data).

| Arquivo | Linhas | Grão (o que é uma linha) | Usamos? |
|---|---|---|---|
| `olist_orders_dataset.csv` | 99.441 | um pedido | sim |
| `olist_order_items_dataset.csv` | 112.650 | um item dentro de um pedido | sim |
| `olist_order_payments_dataset.csv` | 103.886 | um pagamento de um pedido | sim |
| `olist_order_reviews_dataset.csv` | 99.224 | uma avaliação | sim |
| `olist_customers_dataset.csv` | 99.441 | um cadastro de cliente por pedido | sim |
| `olist_products_dataset.csv` | 32.951 | um produto | sim |
| `olist_sellers_dataset.csv` | 3.095 | um vendedor | sim |
| `product_category_name_translation.csv` | 71 | uma categoria traduzida | sim |
| `olist_geolocation_dataset.csv` | 1.000.163 | um CEP com coordenadas | não |

**Grão** é a palavra mais importante desta tabela. É a resposta para "o que uma linha representa". Quase todo erro de número em análise de dados vem de misturar grãos, por exemplo somar o frete de um pedido uma vez para cada item dele.

**Armadilhas conhecidas da base**, que o projeto trata e que você precisa saber explicar.
- `customer_id` muda a cada pedido. A mesma pessoa tem vários. A pessoa real é `customer_unique_id`.
- `review_id` se repete e alguns pedidos têm mais de uma avaliação.
- Colunas com nome escrito errado na origem (`product_name_lenght`). Foram mantidas na staging para a carga bater com o CSV.
- Meses do começo (2016) e do fim (set. e out. de 2018) têm poucos pedidos e distorcem tendência.

## 5. A stack e o porquê de cada ferramenta

| Ferramenta | Papel no projeto | Por que ela | O que foi descartado e por quê |
|---|---|---|---|
| **Docker** | Sobe o PostgreSQL com um comando | Qualquer pessoa roda o projeto igual, em qualquer computador, sem instalar banco na mão. Acaba com o "na minha máquina funciona" | Instalar o PostgreSQL direto no computador. Funciona, mas ninguém mais consegue reproduzir |
| **PostgreSQL 16** | Banco local, staging e modelo estrela | É o banco relacional mais pedido em vaga e o SQL dele é o padrão de mercado. Prova SQL, o item número um das vagas | SQLite, que é mais simples mas não mostra o que empresa usa |
| **SQL** | Transformação, modelagem e análises | É a língua do analista de dados. A maior parte do tratamento acontece aqui | Fazer tudo em pandas. Esconderia o SQL, que é o que mais pesa na contratação |
| **Python (pandas, SciPy)** | Teste de hipótese e exportações | Estatística que o SQL não faz bem. SciPy tem os testes prontos e confiáveis | R, que é ótimo para estatística mas aparece pouco nas vagas |
| **Databricks Free Edition** | Pipeline na nuvem em camadas | Plataforma usada por bancos, varejo e indústria. Prova nuvem, Spark e ETL de uma vez. Gratuita para estudo | BigQuery, que também é nuvem mas não traz Spark nem arquitetura medalhão |
| **PySpark** | Tratamento na camada prata | É o pandas do mundo distribuído, feito para volumes que não cabem em uma máquina. Aprender aqui com dados pequenos é o jeito mais barato | Só SQL no Databricks. Daria certo, mas perde o PySpark, que as vagas citam |
| **Delta Lake** | Formato das tabelas no Databricks | Tabela com histórico de versões e transações, como um banco, mas em arquivos baratos | Parquet puro dentro do Databricks, que não tem histórico nem transação |
| **Parquet** | Ponte entre a camada ouro e o painel | Arquivo colunar, pequeno e rápido de ler. O painel fica sem servidor e nunca cai | Ler o Databricks ao vivo, que tem cota diária e pode apagar conta parada |
| **Streamlit** | Painel publicado | Painel em Python, com link aberto que o recrutador abre no celular | Power BI. Aparece em 68% das vagas, mas o painel publicado exige conta para ver. Decisão do Guilherme, com o custo conhecido |
| **pytest** | Testes automáticos em Python | Garante que as regras de limpeza continuam certas quando o código muda | Testar à mão, que ninguém repete |
| **GitHub Actions** | Roda os testes a cada push | Mostra prática de engenharia (CI). Recrutador técnico olha o selo verde no README | Nenhuma alternativa real, é o padrão no GitHub |

**Sobre o Supabase.** Seria um terceiro banco fazendo o mesmo papel do PostgreSQL. O plano gratuito costuma pausar o projeto depois de uma semana sem uso, e o painel quebraria justo quando um recrutador clicasse no link.

## 6. Arquitetura

O mesmo dado percorre dois caminhos que chegam ao mesmo modelo. O caminho local prova SQL. O caminho da nuvem prova Databricks. Os dois precisam dar o mesmo resultado, e essa conferência é parte do projeto.

```
                    CSVs da Olist (data/raw)
                              │
           ┌──────────────────┴──────────────────┐
           ▼                                     ▼
   CAMINHO LOCAL (Docker)                CAMINHO NUVEM (Databricks)
   staging  ─ tipos corretos             bronze ─ cópia crua em Delta
      │                                     │
      ▼                                     ▼
   dw (modelo estrela)                   prata  ─ limpeza em PySpark
      │                                     │
      ├─► testes de integridade             ▼
      ├─► 6 análises SQL                 ouro   ─ fatos, dimensões, KPIs
      └─► teste de hipótese (Python)        │
                                            ▼
                     conferência ◄──── Parquet agregado (app/data)
                  (totais batem?)           │
                                            ▼
                                     Streamlit publicado
```

**Por que dois caminhos e não um.** O PostgreSQL já estava pronto e é o melhor lugar para mostrar SQL puro. O Databricks é o que empresa grande usa. Fazer os dois e provar que batem ensina a habilidade mais valiosa de um analista, que é desconfiar do próprio número e conferir.

## 7. As etapas, uma por uma

Cada etapa tem o que é, por que existe e o que você aprende com ela.

### 7.1 Extração

**O que é.** Baixar os CSVs da fonte oficial para `data/raw` com `scripts/baixar_dados.sh`.

**Por que existe.** Dado bruto não vai para o Git. Ele é grande, pode mudar e tem dono. O script deixa a extração repetível, e qualquer pessoa baixa o mesmo dado.

**Você aprende.** Separar código de dado, `.gitignore`, script de shell e reprodutibilidade.

### 7.2 Staging

**O que é.** Schema `staging` no PostgreSQL. Uma tabela para cada CSV, com os tipos certos (data é data, dinheiro é `NUMERIC`) e nenhuma regra de negócio. Arquivos `001_staging.sql` e `002_carga_staging.sql`.

**Por que existe.** Carregar e transformar ao mesmo tempo esconde onde o erro aconteceu. Com a staging, a carga só copia, e toda transformação fica visível na etapa seguinte. Se um número sair errado, dá para comparar com a staging e achar o culpado.

**Você aprende.** Tipos de dados, chave primária, `\copy`, por que `NUMERIC` e não `FLOAT` para dinheiro.

### 7.3 Modelo estrela

**O que é.** Schema `dw` com duas tabelas fato e quatro dimensões. Arquivo `003_modelo_estrela.sql`.

| Tabela | Tipo | Grão | Para que serve |
|---|---|---|---|
| `fato_itens_pedido` | fato | um item vendido | receita, mix de produto, vendedor |
| `fato_pedidos` | fato | um pedido | entrega, atraso, frete, pagamento, nota |
| `dim_data` | dimensão | um dia | ano, mês, dia da semana |
| `dim_cliente` | dimensão | uma pessoa | cidade, estado, região |
| `dim_produto` | dimensão | um produto | categoria, peso, fotos |
| `dim_vendedor` | dimensão | um vendedor | cidade, estado |

**Por que existe.** O modelo estrela separa o que se mede (fatos) de como se olha (dimensões). As consultas ficam simples e é o formato que ferramentas de BI esperam.

**Por que duas tabelas fato.** Frete, atraso e nota são do pedido, e receita é do item. Numa tabela só, um pedido com 3 itens contaria o frete 3 vezes.

**Você aprende.** Fato e dimensão, grão, chave substituta (`data_sk` no formato AAAAMMDD), CTE, `ROW_NUMBER`, `DISTINCT ON`, `COALESCE`.

### 7.4 Regras de tratamento

Toda regra abaixo está no código e você precisa saber o porquê de cada uma.

| Regra | Onde | Por quê |
|---|---|---|
| Cliente pela pessoa (`customer_unique_id`) | `dim_cliente` | Com `customer_id` a recompra daria exatamente zero |
| Endereço do cliente pelo pedido mais recente | `dim_cliente` | A pessoa pode ter se mudado, e vale onde ela está agora |
| Avaliação duplicada fica com a mais recente | `fato_pedidos` | Evita contar o mesmo pedido duas vezes na nota |
| Produto sem categoria vira `sem_categoria` | `dim_produto` | Nulo some dos agrupamentos sem ninguém perceber |
| Atraso = data entregue menos data prometida, em dias | `fato_pedidos` | Positivo é atraso, negativo é adiantado. Só existe para pedido entregue |
| Calendário gerado como `TIMESTAMP` sem fuso | `dim_data` | Com fuso, o horário de verão de 2016 a 2018 pulava dias e quebrava a chave |
| Janela de 01/2017 a 08/2018 | visões | Fora dela há poucos pedidos e a tendência fica falsa |

### 7.5 Testes de integridade

**O que é.** `sql/testes/integridade.sql` roda ao fim do pipeline e para tudo se uma regra falhar.

| Teste | O que garante |
|---|---|
| Receita do fato igual à da staging | nenhum centavo perdido ou criado |
| Mesma contagem de pedidos | nenhum pedido perdido ou duplicado |
| Calendário sem buracos | foi esse teste que pegou o bug do horário de verão |
| Notas entre 1 e 5 | dado fora da escala não passa |
| Pedido não entregue sem atraso | regra de negócio respeitada |
| Um cliente por pessoa | a dimensão não duplicou |

**Por que existe.** Número errado no painel é pior do que painel nenhum. O teste transforma "acho que está certo" em "está provado que bate".

**Você aprende.** Qualidade de dados, testes como parte do pipeline, `DO $$` e `RAISE EXCEPTION`.

### 7.6 Análises em SQL

Treze consultas em `sql/analises/`, cada uma responde uma pergunta. As sete últimas sustentam os achados do relatório e o filtro por estado do painel, e têm uma tabela gêmea na camada ouro.

| Arquivo | Pergunta | Técnica principal |
|---|---|---|
| `01_kpis_mensais.sql` | Como receita, pedidos e ticket evoluíram? | `LAG`, média móvel |
| `02_curva_abc_categorias.sql` | Quais categorias concentram a receita? | soma acumulada com `SUM OVER` |
| `03_coortes_retencao.sql` | Os clientes voltam? | coortes, `MIN OVER`, `FILTER` |
| `04_rfm_segmentos.sql` | Como segmentar para CRM? | `NTILE` |
| `05_atraso_vs_avaliacao.sql` | O atraso derruba a nota? | agregação condicional |
| `06_atraso_por_estado.sql` | Onde agir primeiro? | `RANK`, `HAVING` |
| `07_nota_por_dia_atraso.sql` | A partir de que dia de atraso a nota despenca? | `FILTER`, contagem por valor exato |
| `08_entrega_por_regiao.sql` | A entrega é menos previsível em alguma região? | `percentile_cont` |
| `09_nota_por_regiao_atraso.sql` | A nota baixa vem da região ou do atraso? | estratificação |
| `10_atraso_vendedor_destino.sql` | O RJ atrasa pelo vendedor ou pela rota? | CTE com `HAVING COUNT(DISTINCT)`, comparação pareada |
| `11_recompra_primeira_compra.sql` | Quem teve a primeira compra atrasada volta menos? | `DISTINCT ON` com desempate |
| `12_faixa_por_estado.sql` | Como a nota cai por faixa de atraso em cada estado? | contagens e somas por estado e faixa, sem taxa pronta |
| `13_recompra_por_estado.sql` | Qual a recompra em cada estado? | pessoas e quem voltou, pelo endereço mais recente |

Os números que o relatório cita sobre esses achados saem de `py -3.12 analise/achados_relatorio.py`, que lê os Parquet já conferidos e diz se cada achado passou no critério combinado antes da análise.

**Você aprende.** Window functions, que são o assunto de SQL que mais aparece em teste técnico.

### 7.7 Teste de hipótese

**O que é.** `analise/teste_hipotese.py` testa se pedidos atrasados recebem nota menor.

**Por que existe.** Ver no gráfico que a nota cai não prova nada. Pode ser acaso. O teste diz qual a chance de a diferença ser acaso e qual o tamanho dela.

**Por que esses testes.** A nota vai de 1 a 5 e não segue distribuição normal, então o teste t não serve. Usamos Mann-Whitney U, que compara posições e não médias, com a correlação rank-biserial para o tamanho do efeito. Para a proporção de notas baixas usamos qui-quadrado e intervalo de confiança de 95%.

**Você aprende.** Hipótese nula, p-valor, tamanho de efeito, intervalo de confiança e por que significância sem tamanho de efeito engana.

### 7.8 Databricks, arquitetura medalhão

**O que é.** O mesmo caminho refeito na nuvem em três camadas, uma por notebook.

| Camada | Notebook | O que tem | Analogia com o caminho local |
|---|---|---|---|
| Bronze | `01_bronze` | os CSVs crus em tabelas Delta | os CSVs em `data/raw` |
| Prata | `02_prata` | dado limpo e padronizado, em PySpark | staging mais as regras da 7.4 |
| Ouro | `03_ouro` | fatos, dimensões e visões de KPI | schema `dw` e as visões |

**Por que três camadas.** Cada camada tem um contrato. A bronze guarda o que chegou, para reprocessar se uma regra mudar. A prata é a verdade limpa. A ouro é o que o negócio consome. Se o painel mostrar algo estranho, você desce camada por camada até achar onde o dado mudou.

**Você aprende.** Spark e por que ele é preguiçoso (só executa quando você pede um resultado), DataFrame distribuído, tabelas Delta, Databricks SQL, catálogo de tabelas.

### 7.9 Exportação e conferência

**O que é.** As tabelas ouro agregadas saem como Parquet para `app/data`, e um teste confere pedidos, receita e clientes contra o PostgreSQL.

**Por que existe.** Duas fontes que deveriam ser iguais e não foram conferidas são duas fontes de erro. A conferência prova que o pipeline da nuvem está certo.

As sete tabelas do relatório e do filtro por estado são conferidas linha a linha contra as análises `07` a `13`, depois de ordenar os dois lados pelo grão. Contagem tem que ser igual e percentil ou soma só pode diferir por arredondamento de ponto flutuante.

**Você aprende.** Formato colunar, reconciliação de dados, teste automatizado comparando fontes.

### 7.10 Painel em Streamlit

**O que é.** App em `app/`, publicado no Streamlit Community Cloud.

| Página | Pergunta | O que mostra |
|---|---|---|
| Visão geral | Como o negócio está indo? | receita, pedidos, ticket médio e nota média, com variação mês a mês |
| Vendas | De onde vem a receita? | evolução mensal, curva ABC, recompra de 3% |
| Logística | Onde a entrega falha? | atraso por estado, folga entre prometido e real, frete por região |
| Cliente | O atraso derruba a nota? | nota por faixa de atraso e a curva de dias de atraso (o teste de hipótese fica no relatório, não na tela) |
| Recomendações | O que fazer primeiro? | as 4 ações com o número que sustenta cada uma |
| Relatório | Quanto dá para confiar nos achados? | atraso e nota por mês e por estado, impacto de cada ação, tamanho do teste A/B e a base de cada número |

**Como os gráficos se filtram.** Clicar num estado (mapa da Visão geral e da Logística, ranking da Logística, dispersão do Relatório ou a sigla no mar) filtra os cartões e as faixas da Visão geral, da Logística e do Cliente, e o estado vale em todas as páginas até clicar em "Ver Brasil inteiro". Clicar num mês (Vendas e Relatório), numa faixa (Visão geral), numa região (Logística) ou num dia (Cliente) destaca o recorte e deixa o resto apagado, porque tendência com barras removidas deixa de ser tendência. Clicar de novo no item já escolhido desfaz o filtro, e os botões de reset continuam para quem usa teclado. A página Vendas continua no Brasil inteiro, já que a receita não está separada por estado na camada ouro, e a página diz isso quando há estado escolhido.

**Por que cada página termina com uma conclusão.** Gráfico sem conclusão obriga o leitor a fazer a análise. Quem contrata analista quer quem entrega a conclusão.

**Você aprende.** Storytelling com dados, escolha de gráfico, cache no Streamlit, deploy.

### 7.11 Testes e CI

**O que é.** `tests/` com pytest e um workflow em `.github/workflows/` que roda os testes a cada push.

**Por que existe.** Sem teste automático, uma mudança pequena quebra uma regra antiga e ninguém percebe. Com CI, o GitHub avisa na hora.

**Você aprende.** Escrever teste que falha antes e passa depois, fixtures, integração contínua.

**Sobre os minutos do Actions.** Os minutos gratuitos só contam para repositório privado. O repositório do projeto é público, então o CI roda sem limite nos runners padrão.

### 7.12 Escala, só no texto

**O que é.** Seção do README final chamada "O que muda com 100x mais dados", que explica como cada etapa do projeto se comportaria com um volume muito maior.

| Ponto | O que muda com 100x mais dados |
|---|---|
| Carga | Em vez de recarregar tudo, carga incremental só com os pedidos novos |
| Delta Lake | Particionar por mês, para consultas de um período lerem só os arquivos daquele mês |
| Chaves | `customer_unique_id` e a chave de data seguem estáveis, então cargas novas não quebram as antigas |
| Testes de integridade | Continuam iguais, porque comparam totais e valem para qualquer volume |
| Painel | Já lê Parquet agregado, então o volume bruto não chega até ele |

**Por que só texto.** A base da Olist tem cerca de 100 mil pedidos e cabe num notebook. Provar escala com ela seria fingir. O que o projeto prova é que o Guilherme sabe como o pipeline escalaria e por quê. Teste com dado sintético multiplicado e pipeline incremental de verdade ficam como próximo passo.

**Você aprende.** Carga incremental, particionamento, o que muda quando o dado deixa de caber em uma máquina.

## 8. Achados já comprovados

Estes números vêm do pipeline local e do teste de hipótese, e o painel precisa reproduzir os mesmos valores.

- A receita mensal cresceu cerca de 6 vezes em 2017 e estabilizou perto de R$ 900 mil por mês em 2018.
- Só 3,0% dos clientes compraram mais de uma vez.
- 18 de 74 categorias somam 81% da receita.
- 6,7% dos pedidos entregues e avaliados chegam atrasados (6,8% de todos os entregues), mas respondem por 32,6% das notas 1 e 2.
- A nota média cai de 4,29 no prazo para 2,27 com atraso. Pedido atrasado tem 6,7 vezes mais chance de nota baixa.
- O RJ tem 12,8% dos pedidos e 22,9% dos atrasos. O Nordeste tem a pior taxa de atraso, 12,8%, contra 4,5% em SP.
- Em média, o pedido chega 11,8 dias antes do prazo prometido.
- A nota baixa vai de 12,4% no dia prometido para 19,7% com 1 dia de atraso, 34,3% com 2 e 50,4% com 3.
- O mesmo vendedor atrasa em média 12,2% dos pedidos para o RJ e 4,4% para SP (124 vendedores, Wilcoxon p = 5,5e-15). O resultado se mantém com vendedores só de SP comparando RJ e MG e com vendedores de fora dos dois estados. O atraso do RJ vem do caminho, não do vendedor.
- Entre os 80% de pedidos do meio, a entrega no Nordeste varia 27 dias e no Sudeste 19. O Nordeste é a única região em que o p90 passa do dia prometido.
- Dentro de cada situação a região quase não muda a nota. No prazo, de 4,20 a 4,30. Atrasado, de 2,14 a 2,37.
- Quem teve a primeira compra atrasada volta um pouco menos, 2,5% contra 3,1% (p = 0,021). Achado secundário, com a ressalva de que quem comprou no fim da janela teve menos tempo para voltar.

## 9. Recomendações de negócio

1. Rever a entrega até o cliente no RJ (transportadora, rota, última milha), porque o vendedor foi descartado como causa.
2. Prometer prazo por região, e não um prazo nacional.
3. Avisar o cliente antes do primeiro dia de atraso, testando com experimento A/B.
4. Criar um programa de segunda compra para os cerca de 14 mil clientes de alto valor que não voltaram.

## 10. Como saber que deu certo

- [ ] `docker compose up -d` termina com "Integridade ok" numa máquina limpa.
- [ ] A camada ouro do Databricks bate com o PostgreSQL em pedidos, receita e clientes.
- [ ] Os testes passam no GitHub Actions, com o selo verde no README.
- [ ] O painel abre pelo link sem login, inclusive no celular.
- [ ] O repositório é público, sem dado bruto nem segredo, e o README tem a seção de escala da 7.12.
- [ ] O Guilherme explica, sem consulta, o porquê de cada item das seções 5 e 7.

## 11. Riscos e como lidar

| Risco | O que fazer |
|---|---|
| A cota diária do Databricks Free Edition acaba no meio do trabalho | Trabalhar com amostra durante o desenvolvimento e rodar a base inteira só no fim |
| O Databricks não conecta direto em algo que precisamos | O Parquet exportado já resolve, porque o painel não depende dele |
| O painel fica bonito mas sem conclusão | Toda página começa pela pergunta da seção 7.10 |
| Aprender devagar demais e o prazo estourar | O prazo é guia, não regra. Entender vem antes de terminar |

## 12. Glossário

| Termo | Em uma frase |
|---|---|
| Grão | O que uma linha da tabela representa |
| Staging | Área de chegada do dado, só com tipos corretos e sem regra |
| Fato | Tabela do que se mede (valores, quantidades, eventos) |
| Dimensão | Tabela de como se olha a medida (tempo, cliente, produto) |
| Modelo estrela | Uma fato no centro ligada às dimensões em volta |
| CTE | Uma consulta com nome (`WITH`) usada dentro de outra, para ler em partes |
| Window function | Cálculo sobre um grupo de linhas sem juntar as linhas (`OVER`) |
| Container | Programa empacotado com tudo o que precisa, rodando igual em qualquer máquina |
| Spark | Motor que divide o processamento entre várias máquinas |
| Delta Lake | Formato de tabela em arquivos com histórico de versões e transações |
| Medalhão | Organização em camadas bronze (cru), prata (limpo) e ouro (pronto para o negócio) |
| Parquet | Arquivo colunar, compacto e rápido para análise |
| p-valor | Chance de ver uma diferença desse tamanho se na verdade ela não existisse |
| Tamanho de efeito | Quanto a diferença importa na prática, além de existir |
| CI | Integração contínua, testes que rodam sozinhos a cada mudança |

## 13. Roteiro

O projeto foi dividido em duas fases. Cada fase termina com uma entrega que funciona sozinha e um post no LinkedIn contando o que foi feito e o que os dados mostraram.

### Fase 1. Pipeline local e análise em SQL

| Etapa | Entrega | Status |
|---|---|---|
| 1 | Git, WSL2, Docker, repositório público, extração dos CSVs | feito |
| 2 | Staging, carga, modelo estrela e "Integridade ok" | feito |
| 3 | Visões, 6 análises SQL e teste de hipótese | feito |
| 4 | README da fase 1 | feito. O post foi trocado por um vídeo único no fim da fase 2 |

### Fase 2. Nuvem, painel e engenharia

| Etapa | Entrega | O que você aprende |
|---|---|---|
| 5 | pytest e GitHub Actions | testes automatizados, CI |
| 6 | Conta no Databricks e notebook bronze | nuvem, Delta, por que guardar o dado cru |
| 7 | Notebook prata em PySpark | PySpark, avaliação preguiçosa, limpeza distribuída |
| 8 | Notebook ouro, Parquet exportado, conferência com o PostgreSQL | Databricks SQL, reconciliação de dados |
| 9 | Streamlit com Visão geral, Vendas, Logística, Cliente e Recomendações | estrutura de app, cache, storytelling |
| 10 | App publicado, README final com prints, link e seção de escala | deploy, documentação, escala |
| 11 | Currículo, Gupy e post da fase 2 | como contar o projeto para recrutador |

## 14. Registro de decisões

Toda decisão relevante entra aqui, com data e motivo. É a memória do projeto e vira resposta pronta para entrevista.

| Data | Decisão | Motivo |
|---|---|---|
| 22/10/2026 | Duas tabelas fato com grãos diferentes | Evitar contar frete e nota uma vez por item |
| 22/10/2026 | Calendário gerado como `TIMESTAMP` sem fuso | Bug do horário de verão quebrava a chave da `dim_data` |
| 22/10/2026 | Cliente pela pessoa (`customer_unique_id`) | Com o cadastro por pedido, a recompra daria zero |
| 26/10/2026 | Databricks no lugar do BigQuery como nuvem | Cobre Databricks, Spark, nuvem e ETL com uma ferramenta, e aparece nas vagas |
| 26/10/2026 | Painel em Streamlit, sem Power BI | Escolha do Guilherme. Custo conhecido, já que Power BI aparece em 68% das vagas |
| 26/10/2026 | PostgreSQL local e Parquet para o app, sem Supabase | O app não pode cair, e o Supabase gratuito pausa por inatividade |
| 26/10/2026 | Projeto num repositório Python único | Pipeline, notebooks e app no mesmo lugar, mais fácil de entender e avaliar |
| 27/10/2026 | Recomeçar do zero, com a versão anterior em `_referencia/` como gabarito | O objetivo é o Guilherme construir e explicar cada arquivo. Código recebido pronto não ensina |
| 27/10/2026 | Repositório público | Os minutos gratuitos do Actions acabaram e só valem para repositório privado. Em repositório público o CI é ilimitado, e o portfólio precisa ser aberto de qualquer forma |
| 27/10/2026 | `_referencia/` fora do Git | O repositório público deve mostrar só o que foi reconstruído. A versão antiga continua na máquina do Guilherme |
| 27/10/2026 | Escala provada só em texto, na seção "O que muda com 100x mais dados" | A Olist tem cerca de 100 mil pedidos, então provar escala seria fingir. Teste sintético e carga incremental viram próximo passo |
| 27/10/2026 | Prazo de 10 para 11 dias, sem datas fixas | O dia 1 passou a incluir instalar WSL2, Docker e Git, e criar o repositório |
| 28/10/2026 | Toda tarefa vira Issue (`correção`, `melhoria` ou `nova função`) e toda entrega entra por Pull Request com modelo fixo | Rastreabilidade do que foi feito e por quê, e um padrão que qualquer agente ou pessoa segue. O fluxo completo está no `CLAUDE.md` |
| 28/10/2026 | Contar registros de CSV com o módulo `csv` do Python, nunca com `wc -l` | O CSV de avaliações tem quebras de linha dentro das aspas (comentários dos clientes). O `wc -l` deu 104.720 linhas contra 99.224 registros reais |
| 29/10/2026 | Staging de avaliações sem chave primária | O `review_id` se repete em 789 casos na origem. Com chave primária a carga quebraria. Escolher a avaliação mais recente é regra de negócio e fica na etapa seguinte |
| 29/10/2026 | Ler CSV com `utf-8-sig` quando o arquivo puder ter BOM | O `product_category_name_translation.csv` começa com o caractere invisível `﻿`, que grudaria no nome da primeira coluna (PySpark e pandas) |
| 03/11/2026 | Projeto dividido em duas fases, cada uma com um post no LinkedIn | Mostrar resultado mais cedo. A fase 1 já prova SQL, modelagem e estatística, que são os itens mais pedidos nas vagas |
| 03/11/2026 | Colunas do `dw` com nomes em português (`vendedor_id`, `produto_id`, `cliente_id`) | A staging espelha o CSV em inglês, e o `dw` é a camada do negócio. A troca de nome deixa claro em que camada cada consulta está |
| 03/11/2026 | Teste 5 da integridade reescrito para "atraso só existe com data de entrega" | A versão anterior exigia ao mesmo tempo atraso calculado e entrega nula, o que nunca acontece. Era um teste que não podia falhar, e teste que não falha não protege nada |
| 03/11/2026 | Um vídeo único no LinkedIn com o projeto inteiro, no lugar de um post por fase | O destaque do portfólio é a stack completa, da extração ao painel. Mostrar só a metade enfraquece a história |
| 09/11/2026 | CI com dois jobs, pytest e pipeline SQL completo | O segundo job sobe o Postgres do zero e só fica verde com o "Integridade ok". Uma migration que quebre uma regra antiga é pega no PR, não na máquina de alguém |
| 09/11/2026 | Dinheiro em `DECIMAL(10,2)` também no Spark | `DOUBLE` não fecha a soma ao centavo, e a ouro precisa bater com o Postgres exatamente |
| 09/11/2026 | Parquet do painel gravado pelo pandas, um arquivo por tabela | O Spark grava uma pasta com vários pedaços. As tabelas do painel têm dezenas de linhas, então o pandas resolve sem custo |
| 09/11/2026 | Conferência ouro x Postgres como teste do pytest, rodando no CI | A regra "toda camada nova é conferida contra a anterior" vira algo que roda sozinho, e não uma checagem manual que alguém esquece |
| 09/11/2026 | Gráficos do painel em Altair | Já vem com o Streamlit, então não entra dependência nova, e permite tooltip e destaque de uma barra |
| 09/11/2026 | `streamlit>=1.50` no `requirements.txt` | A máquina tinha dois Pythons, e o do pytest estava com Streamlit 1.48, sem o parâmetro `width`. Versão mínima fixada evita o mesmo erro no deploy |
| 09/11/2026 | Limpar `attrs` do pandas antes de gravar o Parquet da ouro | No Serverless, o `toPandas()` guarda métricas da execução (`PlanMetrics`) em `df.attrs`. O pandas tenta gravar esse campo no Parquet como JSON e a exportação quebrava com "Object of type PlanMetrics is not JSON serializable" |
| 09/11/2026 | Visão geral abre com a descoberta, não com a receita | O painel vai para um vídeo curto. Quem vê 5 segundos precisa ler o achado (6,7% dos pedidos atrasam e respondem por 32,6% das notas 1 e 2), e não um gráfico de vendas |
| 09/11/2026 | Locale pt-BR no tema do Altair | Sem ele, o Vega escreve 0.2M e "Jan". Com o `locale` no tema, todo eixo e tooltip sai em 0,2 mi e jan/17 sem formatar gráfico por gráfico |
| 09/11/2026 | Mapa do atraso com a malha do IBGE no repositório | O painel lê só arquivos locais para nunca cair, então a malha (98 KB) fica em `app/data`. Os anéis dos polígonos foram invertidos para o sentido que o d3-geo espera, senão o mapa pinta o mundo inteiro |
| 09/11/2026 | Mapa em duas camadas, Brasil em cinza por baixo | O Vega apaga o polígono que não tem valor no campo da cor. Com o filtro de pedidos mínimos, os estados pequenos sumiam e o mapa ficava com buracos |
| 09/11/2026 | Conclusões do painel calculadas a partir dos dados | A primeira versão dizia que o atraso se concentra no Norte. O Norte atrasa 8,6% e o Nordeste 12,8%, contra 6,7% na média. Texto gerado dos números não diverge deles |
| 09/11/2026 | PRs sempre com base na `main`, sem empilhar | Com PRs empilhados, o merge com `--delete-branch` apagou a branch de base e o GitHub fechou os PRs seguintes em vez de trocar a base. Foram reabertos como #34, #35 e #36 |
| 10/11/2026 | Relatório formal em `resultados/relatorio.md` e página Relatório no painel | O painel mostra a conclusão, o relatório mostra a metodologia, a conferência e as limitações. É o que separa análise de gráfico bonito |
| 10/11/2026 | A base de cada número fica escrita no painel e no relatório | O atraso aparece como 6,7% (entregues e avaliados) e 6,8% (todos os entregues). Os dois estão certos, mas sem a base escrita parecem erro |
| 10/11/2026 | A correlação mensal sai com a ressalva dos meses de crise | Com os 20 meses ela é -0,87. Sem nov/17, fev/18 e mar/18 cai para -0,44 e deixa de ser significativa. Esconder isso venderia uma prova mais forte do que ela é |
| 10/11/2026 | Tamanho de amostra do A/B calculado com `statistics.NormalDist` | A biblioteca padrão já tem a normal inversa, então a página não precisa do SciPy para isso |
| 10/11/2026 | Tabela por vendedor só com pedidos de vendedor único | Pedido com dois vendedores não tem um responsável só pelo atraso. São 1.272 de 96.203 entregues, menos de 3% em cada estado comparado. O controle conta vendedores distintos, porque contar itens tiraria pedidos de um vendedor só com vários itens |
| 10/11/2026 | Vendedor só entra na comparação com 20 ou mais pedidos em cada destino | Com 3 pedidos, uma entrega atrasada vira 33% e domina a média. O corte deixa 124 vendedores na comparação RJ contra SP |
| 10/11/2026 | Percentil exato (`percentile` no Spark, `percentile_cont` no Postgres) | `percentile_approx` é mais rápido em dado grande, mas dá valores próximos e não iguais, e a conferência linha a linha pararia. Com 96 mil pedidos o exato custa pouco |
| 10/11/2026 | Primeira compra desempatada por `pedido_id` | Duas compras da mesma pessoa no mesmo segundo deixariam a escolha da primeira ao acaso, e Spark e Postgres poderiam escolher pedidos diferentes |
| 10/11/2026 | Análise SQL enviada ao container com UTF-8 explícito e `ON_ERROR_STOP` | No Windows o Python enviava o arquivo em cp1252, os acentos dos comentários chegavam corrompidos e o psql descartava a consulta, devolvendo vazio sem erro. O teste mostrava `EmptyDataError` em vez da causa |
| 10/11/2026 | Critérios dos achados novos combinados antes de ler os números finais | Escolher o critério depois de ver o resultado é ajustar a régua ao que se quer provar. Os dois critérios estão no topo de `analise/achados_relatorio.py` |
| 10/11/2026 | Análise 11 com window functions numa passada só, e limite de 60 segundos por consulta na conferência | A versão anterior juntava uma CTE com ela mesma. No banco recém-criado do CI, sem ANALYZE, o Postgres estimou 200 linhas de cada lado e escolheu um laço aninhado de bilhões de comparações, e o job ficou preso por mais de 20 minutos. No banco local o autovacuum já tinha coletado estatísticas e a consulta levava menos de 1 segundo |
| 10/11/2026 | Painel de folga da Logística trocado pela faixa de entrega por região (p10 a p90) | A folga média do Nordeste é igual à do Sudeste e escondia a diferença. A faixa mostra que a entrega no Nordeste é menos previsível, que é o que explica o atraso maior |
| 10/11/2026 | Recomendação 1 passou de "atacar o atraso no RJ" para "rever a entrega até o cliente no RJ" | A comparação pelo mesmo vendedor mostrou que o atraso do RJ não vem de quem vende. Cobrar o vendedor seria agir no lugar errado |
| 10/11/2026 | Hipótese de atrasos mais longos nos meses de crise continua aberta | O único número que existe veio da exploração nos CSVs, sem tabela conferida na camada ouro. Número sem conferência não entra no relatório como conclusão |
| 10/11/2026 | Filtro por estado com duas tabelas novas na camada ouro (`faixa_por_estado`, `recompra_por_estado`) | Guardam contagens e somas por estado, então o painel soma qualquer grupo sem fazer média de médias. Somadas, fecham com `nota_por_faixa` e com o resumo, e são conferidas linha a linha contra as análises `12` e `13` |
| 10/11/2026 | Clique em mês, dia, faixa ou região destaca e não remove os outros | Série que perde as barras ao filtrar deixa de mostrar tendência. O recorte fica aceso e o resto continua à vista, apagado |
| 10/11/2026 | O gráfico de vendedores fica fixo no RJ contra SP | A comparação pelo mesmo vendedor é o achado do RJ e não muda com o estado escolhido. Quando o estado é outro, uma legenda diz isso, em vez de refazer a conta com 13 vendedores no ES |
| 10/11/2026 | O estado escolhido fica na Logística mesmo abaixo do mínimo de 300 pedidos, com aviso de amostra pequena | Clicar num estado e vê-lo sumir por causa de um controle ao lado seria pior que o aviso |
| 10/11/2026 | Mapa com dois parâmetros de seleção, `uf` nos polígonos e `uf_sigla` nas siglas | Um parâmetro só, em duas camadas com dados diferentes, fazia o Vega acusar `Duplicate signal name: uf_tuple` e o gráfico não abria |
| 10/11/2026 | Parquet gerado do Postgres serve só para testar o painel local e nunca entra no Git | O painel lê a camada ouro do Databricks. Os dois arquivos novos entraram só depois de rodar o notebook, e foram comparados com o Postgres, que deu o mesmo resultado nas 131 e nas 27 linhas |
| 10/11/2026 | Segundo clique no item escolhido desfaz o filtro, com a regra numa função só (`alternar`) | Ir até outro cartão para clicar em "Ver Brasil inteiro" quebrava o fluxo de quem explora o mapa. A chave de cada gráfico já muda com o filtro, então o segundo clique chega como um clique novo e a função o transforma em limpar. Os botões ficam por acessibilidade |
| 10/11/2026 | Mapa da Logística pode ser pintado pelo volume de pedidos entregues, em azul e com escala de raiz quadrada | Mostra onde o volume se concentra, o que explica por que o mesmo percentual de atraso pesa mais no RJ que no AL. Linear deixava quase todo o mapa claro, porque SP tem 40.403 pedidos e RR tem 46. Azul porque laranja é só atraso. O rótulo diz "pedidos entregues", já que contar todos os status daria 41.746 em SP e não bateria com o resto do painel |
| 10/11/2026 | Visual do painel num arquivo só (`app/estilo.css`), no estilo moldura e folha, com Bricolage Grotesque nos títulos e números | Antes o CSS morava em `Home.py`, em 7 linhas, e a página ficava numa coluna de 1.200 px. Agora a folha branca usa a tela de 1920 px (até 1.840 px), os blocos são um passo de tom acima da folha, sem sombra, e os indicadores viram uma faixa só dividida por linhas finas. As páginas não mudaram de lógica: o CSS mira nos `data-testid` do Streamlit, então todas herdam. O número que responde ao título da Visão geral (nota média com atraso, 2,27) abre a faixa e é o maior. A lista de estados ao lado do mapa exige 300 pedidos ou mais, o mesmo corte do aviso de amostra pequena, porque RR com 46 pedidos apareceria no topo por acaso. Nome e LinkedIn do autor ficam no rodapé e abaixo do título da Visão geral |
