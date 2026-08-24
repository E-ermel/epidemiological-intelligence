import pandas as pd
import numpy as np

mes_map = {
    'Jan': 1, 'Fev': 2, 'Mar': 3, 'Abr': 4,
    'Mai': 5, 'Jun': 6, 'Jul': 7, 'Ago': 8,
    'Set': 9, 'Out': 10, 'Nov': 11, 'Dez': 12
}

df = pd.read_csv(
    "dados_climaticos\Dados Respiratorios\Lepto.csv",
    sep=";",
    encoding="latin1"
)


# garantir nome da coluna
df = df.rename(columns={df.columns[0]: 'municipio'})

df.columns = df.columns.str.strip()
df['municipio'] = df['municipio'].str.strip()

df = df.replace('-', 0)
df = df.replace('SEM', 0)
print(df.head())

df_long = df.melt(
    id_vars='municipio',
    var_name='ano_mes',
    value_name='valor'
)

df_long[['ano', 'mes']] = df_long['ano_mes'].str.split('/', expand=True)

df_long['mes'] = df_long['mes'].map(mes_map)
df_long['ano'] = pd.to_numeric(df_long['ano'], errors='coerce')

df_long['data'] = pd.to_datetime(
    dict(year=df_long['ano'], month=df_long['mes'], day=1)
)
print(df_long.head())

df_long['valor'] = (
    df_long['valor']
    .astype(str)
    .str.strip()
    .str.replace(',', '.', regex=False)
)

df_long['valor'] = pd.to_numeric(df_long['valor'], errors='coerce')
df_long['valor'] = df_long['valor'].fillna(0)
print(df_long.head())
# 🔥 agregação correta
resultado = df_long.groupby(['municipio', 'data'])['valor'].sum().reset_index()
print(resultado.head())

resultado = resultado.rename(columns={'valor': 'internacoes'})

resultado['municipio'] = (
    resultado['municipio']
    .str.replace(r'^\d+\s*', '', regex=True)
    .str.strip()
    .str.upper()
)
print(resultado.head())

resultado['mes'] = resultado['data'].dt.month
resultado['ano'] = resultado['data'].dt.year
resultado['internacoes'] = resultado['internacoes'].astype(int)
resultado = resultado.groupby(['municipio', 'ano', 'mes'])['internacoes'].sum().reset_index()

print(resultado.head())
resultado.to_csv('dados_climaticos/resultado_final_doencas.csv', sep=";", index=False, encoding="latin1")