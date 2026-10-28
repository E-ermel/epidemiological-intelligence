# Benchmark de modelos de previsão

Compara modelos para prever os casos mensais de cada doença × município
de residência, 12 meses à frente, sobre o gold nacional.

- **Janelas de teste:** histórico até dez/2023 → prevê 2024; até dez/2024 → prevê 2025.
- **Métricas:** MAE, RMSE e WAPE, no nível município × mês e somado por UF × mês.

| Script | Modelo | Clima |
|---|---|---|
| `run_seasonal_naive.py` | mesmo mês do ano anterior | — |
| `run_glm.py` | estrutura do modelo atual (município + mês + clima), Poisson por UF | do mês previsto |
| `run_chronos.py` | Chronos-2 (Amazon), zero-shot | com e sem |
| `run_timesfm.py` | TimesFM 2.5 (Google), zero-shot | sem |
| `run_moirai.py` | Moirai 2.0 (Salesforce), zero-shot | com e sem |
| `run_neuralforecast.py` | PatchTST e TFT, nacional ou por UF | TFT: com |

"Com clima" usa o clima observado nos meses previstos, como o modelo
atual faz. É um cenário otimista: numa previsão real o clima futuro
também seria uma previsão.

## Ambiente

As bibliotecas pedem Python 3.11, torch < 2.5 (por causa do `uni2ts`) e
GPU com CUDA. Fora do `.venv` do projeto:

```powershell
uv python install 3.11
uv venv data_science/benchmarks/.venv --python 3.11
uv pip install --python data_science/benchmarks/.venv/Scripts/python.exe torch==2.4.1 --index-url https://download.pytorch.org/whl/cu121
uv pip install --python data_science/benchmarks/.venv/Scripts/python.exe "torch==2.4.1" "numpy~=1.26.0" "transformers>=4.41,<4.50" "pyarrow<18" uni2ts chronos-forecasting "timesfm[torch]" neuralforecast scikit-learn pandas --extra-index-url https://download.pytorch.org/whl/cu121 --index-strategy unsafe-best-match
```

## Rodar

```powershell
cd data_science/benchmarks
.venv\Scripts\python.exe run_all.py <pasta do gold em parquet>
```

Saída em `output/` (fora do git): `dataset.parquet`, `predictions/` e
`metrics_*.csv`.
