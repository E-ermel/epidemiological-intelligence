# Metodologia: estudo clima × doenças e alerta de surtos

## Visão geral

O projeto Epidemiological Intelligence tem duas partes de modelagem:

- um **estudo** da relação entre clima, ambiente e doenças, que mede
  associações (não causas);
- um **alerta de surtos** mensal, que estima a probabilidade de surto de
  1 a 3 meses à frente, por UF e por município.

Os dados cobrem os 5.570 municípios do Brasil, mês a mês, desde janeiro
de 2015. Os casos são contados pelo município de residência.

## Doenças

- Internações do SIH/SUS: asma, bronquite aguda, bronquite crônica,
  infarto agudo do miocárdio, insuficiência cardíaca e Oropouche.
- Notificações do SINAN: leptospirose (casos confirmados) e acidentes
  por animais peçonhentos, separados por animal (abelha, aranha,
  escorpião, lagarta, serpente e outros).

Oropouche não tem estudo nem alerta: são poucos casos no período.

## Fontes de clima e ambiente

- Clima (INMET): chuva do mês, chuva extrema (máxima horária),
  temperatura média e umidade relativa. Municípios sem estação usam a
  estação mais próxima com dado, até 100 km.
- Uso do solo (MapBiomas), desmatamento (PRODES/INPE), saneamento
  (SNIS), IDHM e indicadores sociais (Atlas Brasil, censo 2010),
  população e densidade (IBGE/SIDRA).

## Estudo: DLNM

O DLNM (modelo de defasagem distribuída não linear) é uma regressão
binomial negativa por doença, com offset de população, efeito fixo de
UF e de mês do ano e tendência temporal. Ele mede quanto o risco muda
com a chuva e a temperatura e com que atraso (de 0 a 3 meses), em
relação ao padrão sazonal de cada UF.

Principais resultados (treino 2015–2023):

- Leptospirose e chuva: um mês de 312 mm aumenta o risco em 56% no
  próprio mês, 40% no mês seguinte, 25% dois meses depois e 9% três
  meses depois. No acumulado, 440 mm de chuva multiplicam o risco por
  3,7.
- Frio (13 °C): aumenta as internações por bronquite crônica (+55%),
  bronquite aguda (+40%), asma (+19%) e insuficiência cardíaca (+19%).
- Calor (31 °C): aumenta o infarto (+17%).
- Acidentes com lagarta sobem com chuva (risco 3,1 vezes maior).

## Estudo: LightGBM e SHAP

Um LightGBM por doença, com as mesmas entradas do DLNM, mede quais
variáveis mais pesam (SHAP). A UF é a variável mais forte em quase
todas as doenças (33% em média). O clima pesa 37% na leptospirose e de
7% a 24% nas outras doenças. Entre as variáveis de ambiente, as que
mais pesam são população urbana, IDHM e densidade; desmatamento e
saneamento pesam pouco quando a UF já está no modelo.

## Alerta de surtos: definição de surto

Um mês está em surto quando os casos passam do canal endêmico (média
mais 1,96 desvio-padrão do mesmo mês nos 5 anos anteriores) e atingem
um mínimo de 5 casos na UF ou 3 no município.

Para as internações do SIH, o canal pula 2020 e 2021: a queda de
internações na pandemia inflava o desvio-padrão do canal e escondia
surtos. O SINAN não teve essa queda e usa o canal normal.

O alerta municipal só cobre séries com pelo menos 1 caso por mês em
média nos últimos 5 anos; os demais municípios ficam cobertos pelo
alerta da UF.

## Alerta de surtos: modelo

O modelo é o Chronos-2 (Amazon), um modelo de fundação para séries
temporais usado sem treino nos dados do projeto (zero-shot). Ele recebe
a série de casos e o clima dos meses passados, e prevê a distribuição
de casos de 1 a 3 meses à frente. A probabilidade de surto é a chance
de os casos passarem do limite do canal endêmico.

O modelo usa cross-learning: lê juntas as séries da mesma doença em UFs
ou municípios vizinhos, o que ajuda as séries pequenas e ruidosas.

Um alerta dispara quando a probabilidade passa do corte: 0,30 na UF e
0,20 no município. Os cortes foram escolhidos em 2023 para o maior F1.

## Alerta de surtos: origens fechada e provisória

Cada rodada mensal prevê a partir de duas origens:

- "fechado": o último mês com dados completos. No SIH, o último mês sem
  dado provisório (as internações chegam com até 4 meses de atraso). No
  SINAN, dois meses antes do último mês com dados. É a leitura padrão e
  a mais confiável; parte dos meses previstos pode já ter passado.
- "provisorio": o último mês disponível, com dados ainda incompletos,
  que tendem a subestimar os casos e a gerar menos alertas.

## Alerta de surtos: desempenho no teste

O teste usou 2024 e 2025, com o corte escolhido em 2023:

- UF: precisão 0,56, recall 0,55, F1 0,55, AUC-ROC 0,83. De cada 100
  alertas, 56 foram surtos; de cada 100 surtos, 55 foram alertados.
- Município: precisão 0,33, recall 0,54, F1 0,41, AUC-ROC 0,81. O
  alerta pega metade dos surtos municipais, com cerca de 2 alarmes
  falsos para cada acerto.

O Chronos-2 superou os modelos estatísticos (GLM binomial negativo) e
de aprendizado de máquina (LightGBM) testados, e também a regra de
persistência (alertar se o mês atual está em surto).

## Limitações

- O alerta aprende com a dinâmica recente dos casos. Ele não antecipou
  o pico de leptospirose no RS em maio de 2024, causado pela enchente:
  a chuva extrema caiu no próprio mês previsto.
- Variáveis de ambiente e a previsão do tempo foram testadas como
  entradas do alerta e não melhoraram o resultado no município.
- Os dados recentes são provisórios: o SINAN do ano corrente é
  preliminar e o SIH recebe internações atrasadas.
- O estudo mede associação, não causalidade. Os indicadores do Atlas
  são do censo de 2010.
- "Surto" aqui é uma definição estatística, não uma declaração oficial
  da vigilância epidemiológica.
