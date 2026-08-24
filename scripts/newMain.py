import pandas as pd
from scipy import stats
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('processados/dados_climaticos_tratados_mensal.csv', sep=';', encoding='latin-1')
df_doencas = pd.read_csv('resultado_final_doencas.csv', sep=";", encoding="latin1")

print(df)

municipios_analisados = ['PORTO ALEGRE', 'SANTA MARIA', 'SANTO AUGUSTO',
                          'URUGUAIANA', 'CACAPAVA DO SUL', 'BAGE',
                          'SOLEDADE', 'LAGOA VERMELHA', 'PASSO FUNDO']

df_merge= df.merge(df_doencas, on=['municipio', 'mes', 'ano'], how='inner')

df_final = df_merge.copy()
df_final['precipitacao_sum'] = df_final['precipitacao_sum'].astype(float)
df_final['temp_orvalho_median'] = df_final['temp_orvalho_median'].astype(float)


df_final_agrupada = df_final.groupby(['municipio', 'ano', 'mes']).agg({
    'precipitacao_sum': 'sum',
    'internacoes': 'sum',
    'temp_orvalho_median': 'median'
}).reset_index()

df_final_filtrada2 = df_final_agrupada[df_final_agrupada['municipio'].isin(municipios_analisados)]
df_final_filtrada2= df_final_filtrada2.drop(df_final_filtrada2[df_final_filtrada2['precipitacao_sum'] <= 0].index)

df_final_filtrada = df_final_filtrada2.copy()

for municipio in municipios_analisados:
    df_municipio = df_final_filtrada[df_final_filtrada['municipio'] == municipio]

    #print(df_final_filtrada)

    coef, p_valor = stats.spearmanr(df_municipio['precipitacao_sum'], df_municipio['internacoes'])
    coef2, p_valor2 = stats.spearmanr(df_municipio['temp_orvalho_median'], df_municipio['internacoes'])

    df_corr = df_municipio[['precipitacao_sum', 'internacoes', 'temp_orvalho_median']].corr(method='spearman')

    df_corr['p_valor'] = None

    df_corr.loc['precipitacao_sum', 'p_valor'] = p_valor
    df_corr.loc['temp_orvalho_median', 'p_valor'] = p_valor2


    df_corr.to_csv(f"processados/novos/correlacao_{municipio}.csv", index=True, sep=";", encoding="latin1", decimal=".")


    print(f"Prep: Coeficiente: {coef:.3f} | p-valor: {p_valor:.4f}")
    print(f"Temp: Coeficiente: {coef2:.3f} | p-valor: {p_valor2:.4f}")
    print(df_corr)

df_plot_filtrado = df_final_filtrada[df_final_filtrada['internacoes'] != 0]
df_plot_filtrado = df_plot_filtrado[df_plot_filtrado['municipio'] == 'PORTO ALEGRE']
df_plot_filtrado['data'] = pd.to_datetime({
    'year': df_plot_filtrado['ano'],
    'month': df_plot_filtrado['mes'],
    'day': 1
})
df_plot_filtrado = df_plot_filtrado.groupby(['municipio', 'data']).agg({'precipitacao_sum': 'sum', 'internacoes': 'sum', 'temp_orvalho_median': 'median'}).reset_index()
print(df_plot_filtrado)
