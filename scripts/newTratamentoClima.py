import os
import pandas as pd
import numpy as np
import re

caminho = "Dados climáticos INMET"
os.makedirs("processados", exist_ok=True)
dados = []

def padronizar_municipio(nome):
    if re.search(r'porto alegre', nome, flags=re.IGNORECASE):
        return 'PORTO ALEGRE'
    return nome.strip().upper()

for raiz, pastas, arquivos in os.walk(caminho):

    for arquivo in arquivos:
            caminho_completo = os.path.join(raiz, arquivo)

            cabecalho = pd.read_csv(caminho_completo, sep=";", encoding="latin1", on_bad_lines="skip")
            df = pd.read_csv(caminho_completo, sep=";", encoding="latin1",
                             decimal=",", skiprows=8,  on_bad_lines="skip")

            df.drop(columns=[
                            'PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)',
                            'PRESSÃO ATMOSFERICA MAX.NA HORA ANT. (AUT) (mB)',
                            'PRESSÃO ATMOSFERICA MIN. NA HORA ANT. (AUT) (mB)',
                            'RADIACAO GLOBAL (Kj/m�)',
                            'RADIACAO GLOBAL (Kj/m²)',
                            'TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)',
                            'TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)',
                            'TEMPERATURA ORVALHO MAX. NA HORA ANT. (AUT) (°C)',
                            'TEMPERATURA ORVALHO MIN. NA HORA ANT. (AUT) (°C)',
                            'UMIDADE REL. MAX. NA HORA ANT. (AUT) (%)',
                            'UMIDADE REL. MIN. NA HORA ANT. (AUT) (%)',
                            'UMIDADE RELATIVA DO AR, HORARIA (%)',
                            'VENTO, DIREÇÃO HORARIA (gr) (° (gr))',
                            'VENTO, RAJADA MAXIMA (m/s)',
                            'VENTO, VELOCIDADE HORARIA (m/s)',
                            'Unnamed: 19'
                            ], inplace=True, errors='ignore' )

            dados.append({
                "arquivo": arquivo,
                "cabecalho": cabecalho,
                "dados": df
            })


resultados_lista = []

for item in dados:
    df = item["dados"].copy()
    cabecalho = item['cabecalho']

    #pega o nome do municipio
    nome_municipio = cabecalho.iloc[1, 1]

    #separa a coluna de data e converte para datetime
    col_data = df.columns[0]
    df[col_data] = pd.to_datetime(df[col_data], errors='coerce')

    #desmembra a data em ano e mês, e adiciona o nome do município
    df['ano'] = df[col_data].dt.year
    df['mes'] = df[col_data].dt.month
    df['dia'] = df[col_data].dt.day
    df['municipio'] = nome_municipio

    #dropa as colunas desnecessarias com nomes variantes
    df_nova = df.drop(df.columns[[0, 1, 3]], axis=1, errors='ignore')
    #limpa os nomes das colunas
    df_nova.columns = df_nova.columns.str.strip()
    nome_municipio = nome_municipio.strip().upper()

    #renomeia as colunas para nomes padronizados
    novos_nomes = {df_nova.columns[0]: 'precipitacao', df_nova.columns[1]: 'temp_orvalho'}
    df_nova = df_nova.rename(columns=novos_nomes)

    #converte as colunas de precipitação e temperatura de orvalho para numéricas, tratando os erros e arredondando para 2 casas decimais
    df_nova['precipitacao'] = pd.to_numeric(df_nova['precipitacao'], errors='coerce').round(2)
    df_nova['temp_orvalho'] = pd.to_numeric(df_nova['temp_orvalho'], ).round(2)

    #substitui os valores -9999 por NaN e trata os valores negativos de precipitação
    df_nova = df_nova.replace(-9999, 0)


    #agrupa por município, ano e mês, calculando a soma,
    # mediana e máximo da precipitação, e a mediana, mínimo e máximo da temperatura de orvalho

    df_agrupada = df_nova.groupby(['municipio', 'ano', 'mes', 'dia']).agg({
        'precipitacao': ['sum','median', 'max'],
        'temp_orvalho': ['median', 'min', 'max']
    }).reset_index()

    #renomeia as colunas para um formato mais simples
    df_agrupada.columns = [
    '_'.join([c for c in col if c]).strip() if isinstance(col, tuple) else col
    for col in df_agrupada.columns
]

    #ordena os dados por município, ano, mês e dia
    df_agrupada = df_agrupada.sort_values(['municipio', 'ano', 'mes', 'dia'])

    #trata os valores faltantes usando interpolação e preenchimento para frente e para trás
    '''"Dados Respiratorios"
    cols = [
            'precipitacao_sum', 'precipitacao_median', 'precipitacao_max',
            'temp_orvalho_median', 'temp_orvalho_min', 'temp_orvalho_max'
        ]

    df_agrupada[cols] = df_agrupada[cols].interpolate()
    df_agrupada[cols] = df_agrupada[cols].ffill().bfill()
    '''
    resultados_lista.append(df_agrupada)


#concatena os resultados em um unico dataframe
df_final = pd.concat(resultados_lista, ignore_index=True)
#cria uma coluna de data usando as colunas de datas
df_final['data'] = pd.to_datetime(
    dict(year=df_final['ano'], month=df_final['mes'], day=df_final['dia'])
)
#dropa as colunas de ano, mês e dia, pois agora temos a coluna de data completa
df_final= df_final.drop(columns=['ano', 'mes', 'dia'], errors='ignore')
#ordena os dados por município, ano, mês e dia
df_final = df_final.sort_values('data')
cols_numericas = [
    'precipitacao_sum', 'precipitacao_median', 'precipitacao_max',
    'temp_orvalho_median', 'temp_orvalho_min', 'temp_orvalho_max'
]

df_final[cols_numericas] = df_final[cols_numericas].round(2)
#salva o dataframe final em um arquivo csv
df_final['municipio'] = df_final['municipio'].apply(padronizar_municipio)
df_final.to_csv("processados/dados_climaticos_tratados_novos.csv", index=False, sep=";", encoding="latin1", decimal=",")

print(df_final.head(10))

df_final_anual = df_final.drop(columns={'precipitacao_median', 'precipitacao_max', 'temp_orvalho_min', 'temp_orvalho_max'}, errors='ignore')
df_final_anual['ano'] = df_final_anual['data'].dt.year

df_final_mes = df_final_anual.copy()
df_final_mes['mes'] = df_final_anual['data'].dt.month

df_final_anual = df_final_anual.groupby(['municipio', 'ano']).agg({'precipitacao_sum': 'sum', 'temp_orvalho_median': 'median'}).reset_index().round(3)
print(df_final_anual)

df_final_mes = df_final_mes.groupby(['municipio', 'ano', 'mes']).agg({'precipitacao_sum': 'sum', 'temp_orvalho_median': 'median'}).reset_index().round(3)
print(df_final_mes)


df_final_anual.to_csv("processados/dados_climaticos_tratados_anual.csv", index=False, sep=";", encoding="latin1", decimal=".")
df_final_mes.to_csv("processados/dados_climaticos_tratados_mensal.csv", index=False, sep=";", encoding="latin1", decimal=".")
