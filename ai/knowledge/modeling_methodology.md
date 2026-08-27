# Metodologia de Modelagem Epidemiológica

## Objetivo

Os modelos do projeto Epidemiological Intelligence têm como objetivo
estimar contagens mensais de casos epidemiológicos utilizando informações
temporais, municipais e climáticas.

Os modelos não foram desenvolvidos para detectar surtos, epidemias ou
realizar diagnóstico clínico.

## Doenças modeladas

O pipeline possui modelos para:

- Asma
- Bronquite Aguda
- Bronquite Crônica
- Infarto Agudo do Miocárdio
- Insuficiência Cardíaca
- Leptospirose

## Modelo estatístico

O modelo utilizado é a regressão Binomial Negativa.

Esse modelo foi escolhido por trabalhar com dados de contagem e permitir
que a variância seja superior à média, situação conhecida como
sobredispersão.

Isso é relevante para dados epidemiológicos, nos quais a quantidade de
casos pode variar significativamente entre municípios e períodos.

## Baseline

Cada doença possui um modelo baseline utilizado como referência.

O modelo final inclui as variáveis selecionadas durante o processo de
modelagem.

A utilidade das variáveis adicionais é avaliada comparando o desempenho
do modelo final com o baseline em dados de teste.

## Divisão temporal

A avaliação utiliza separação temporal entre treino e teste.

Dados futuros não devem ser utilizados para construir features
correspondentes ao período de treinamento.

Essa estratégia busca reduzir data leakage e representar melhor o cenário
real de previsão.

## Variáveis climáticas

Entre as variáveis disponíveis no projeto estão:

- precipitação acumulada;
- precipitação máxima observada;
- temperatura média;
- umidade relativa média;
- ponto de orvalho;
- pressão atmosférica;
- velocidade do vento;
- rajada máxima do vento.

Também podem ser utilizadas versões defasadas (lags) das variáveis.

Um lag representa o valor observado em um período anterior.

Por exemplo, precipitation_sum_mm_lag2 representa a precipitação
observada dois períodos antes.

## Métricas

### MAE

Mean Absolute Error representa a média do erro absoluto entre valores
observados e previstos.

Quanto menor o MAE, melhor.

### RMSE

Root Mean Squared Error penaliza erros grandes com maior intensidade.

Quanto menor o RMSE, melhor.

### R²

R² mede a capacidade do modelo de explicar a variabilidade observada
nos dados.

Valores mais próximos de 1 indicam maior capacidade explicativa.

R² deve ser interpretado em conjunto com outras métricas.

### WAPE

Weighted Absolute Percentage Error representa o erro absoluto total em
relação ao volume total observado.

Quanto menor o WAPE, melhor.

## Significância estatística e previsão

Uma variável estatisticamente significativa não necessariamente melhora
a capacidade preditiva do modelo.

Significância estatística e desempenho fora da amostra representam
questões diferentes e devem ser avaliadas separadamente.

## Associação e causalidade

Os modelos podem identificar associações entre variáveis climáticas e
contagens epidemiológicas.

Essas associações não devem ser interpretadas automaticamente como
relações causais.

Outros fatores epidemiológicos, ambientais, sociais e demográficos que
não estão presentes no modelo podem influenciar o número de casos.

## Limitações

Os modelos utilizam apenas as informações disponíveis no pipeline.

Eventos extremos e mudanças abruptas no padrão epidemiológico podem gerar
erros maiores quando os fatores responsáveis por essas mudanças não estão
adequadamente representados pelas features disponíveis no modelo.

## Caso específico da leptospirose

A leptospirose apresentou desempenho preditivo inferior às demais doenças
quando avaliada no conjunto de teste completo.

Uma característica importante desse período é a presença de 2024, ano em
que ocorreram eventos hidrológicos extremos no Rio Grande do Sul, incluindo
as grandes enchentes.

Esses eventos produziram um comportamento epidemiológico muito diferente
do padrão histórico observado no conjunto de treinamento.

Foi realizada também uma análise alternativa desconsiderando esse período
extremo. Nessa avaliação, o desempenho do modelo de leptospirose apresentou
melhora em relação à avaliação que incluía 2024.

Esse resultado sugere que eventos extremos podem afetar significativamente
a capacidade preditiva do modelo quando esses fenômenos não estão
adequadamente representados pelas variáveis utilizadas.

Entretanto, essa análise não permite afirmar que as enchentes foram a causa
direta do erro do modelo ou do aumento dos casos. Ela mostra apenas que o
desempenho do modelo muda quando um período epidemiologicamente atípico é
retirado da avaliação.

Portanto, os resultados da leptospirose devem ser interpretados em dois
contextos:

- desempenho no conjunto completo, incluindo eventos extremos;
- desempenho em condições mais próximas do padrão histórico.

Essa distinção é importante ao avaliar a capacidade de generalização do
modelo.

## Uso das previsões

As previsões representam estimativas agregadas de contagens de casos
por município e período.

Elas não devem ser utilizadas como:

- diagnóstico individual;
- previsão determinística de surtos;
- recomendação médica;
- evidência de causalidade.