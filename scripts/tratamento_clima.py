import os
import pandas as pd
import numpy as np

caminho = "Dados climáticos INMET"
os.makedirs("processados", exist_ok=True)
dados = []

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
    
    nome_municipio = cabecalho.iloc[1, 1]
    
    col_data = df.columns[0]
    df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
    
    df['ano'] = df[col_data].dt.year
    df['mes'] = df[col_data].dt.month
    df['Município'] = nome_municipio
    

    df_nova = df.drop(df.columns[[0, 1, 3]], axis=1, errors='ignore') 
    df_nova.columns = df_nova.columns.str.strip()
    nome_municipio = nome_municipio.strip().upper()

    novos_nomes = {df_nova.columns[0]: 'Precipitação', df_nova.columns[1]: 'Temp_Orvalho'}
    df_nova = df_nova.rename(columns=novos_nomes)
    
    df_nova = df_nova.replace(-9999, np.nan)

    df_nova['Precipitação'] = df_nova['Precipitação'].apply(
            lambda x: np.nan if x < 0 else x
    )
    
    df_agrupada = df_nova.groupby(['Município', 'ano', 'mes']).agg({
        'Precipitação': ['sum','median', 'max'],
        'Temp_Orvalho': ['median', 'min', 'max']
    }).reset_index()
    
    df_agrupada.columns = [
    '_'.join([c for c in col if c]).strip() if isinstance(col, tuple) else col
    for col in df_agrupada.columns
]

    df_agrupada = df_agrupada.sort_values(['Município', 'ano', 'mes'])

    cols = [
            'Precipitação_sum', 'Precipitação_median', 'Precipitação_max',
            'Temp_Orvalho_median', 'Temp_Orvalho_min', 'Temp_Orvalho_max'
        ]

    df_agrupada[cols] = df_agrupada[cols].interpolate()
    df_agrupada[cols] = df_agrupada[cols].ffill().bfill()
    
    resultados_lista.append(df_agrupada)
    
df_final = pd.concat(resultados_lista, ignore_index=True)
df_final['data'] = pd.to_datetime(
    dict(year=df_final['ano'], month=df_final['mes'], day=1)
)
df_final= df_final.drop(columns=['ano', 'mes'], errors='ignore')
df_final = df_final.sort_values('data')
df_final.to_csv("processados/dados_climaticos_tratados.csv", index=False, sep=";", encoding="latin1")

print(df_final.head())