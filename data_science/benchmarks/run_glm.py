"""
Referência: a estrutura do modelo atual (data_science/.../train.py),
um modelo por UF × doença:

    log E[casos] = município + mês do ano + clima do mês previsto

Estimado como regressão de Poisson (scikit-learn, matriz esparsa), não
como binomial negativa por statsmodels: com uma coluna por município
(853 em MG), a matriz densa do statsmodels passou de 20 GB de RAM. A
média prevista tem a mesma forma -- a binomial negativa só muda a
variância assumida, não a estrutura da previsão.

As mesmas 6 variáveis de clima para todas as doenças (a seleção por
doença do MODEL_CONFIG só existe para as 6 doenças originais). Como no
modelo atual, o clima é o observado no mês previsto.
"""

import time
import warnings

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import PoissonRegressor

from common import CLIMATE_COLUMNS, load_dataset, save_predictions, windows

warnings.filterwarnings("ignore")


def _design(df: pd.DataFrame, municipalities: pd.Index, means: pd.Series, stds: pd.Series) -> sparse.csr_matrix:
    rows = np.arange(len(df))

    municipality = municipalities.get_indexer(df["municipality_code"])
    municipality_part = sparse.csr_matrix(
        (np.ones(len(df)), (rows, municipality)), shape=(len(df), len(municipalities))
    )
    month_part = sparse.csr_matrix(
        (np.ones(len(df)), (rows, df["ds"].dt.month.to_numpy() - 1)), shape=(len(df), 12)
    )
    climate_part = sparse.csr_matrix(((df[CLIMATE_COLUMNS] - means) / stds).to_numpy(dtype=float))

    return sparse.hstack([municipality_part, month_part, climate_part], format="csr")


def fit_predict(history: pd.DataFrame, target: pd.DataFrame) -> np.ndarray:
    y = history["y"].to_numpy(dtype=float)
    if y.sum() == 0:
        return np.zeros(len(target))

    municipalities = pd.Index(sorted(history["municipality_code"].unique()))
    means, stds = history[CLIMATE_COLUMNS].mean(), history[CLIMATE_COLUMNS].std().replace(0, 1)

    # alpha mínimo: só o bastante para municípios sem nenhum caso no
    # histórico não empurrarem o coeficiente para -infinito.
    model = PoissonRegressor(alpha=1e-6, max_iter=300)
    model.fit(_design(history, municipalities, means, stds), y)

    return model.predict(_design(target, municipalities, means, stds))


def main() -> None:
    df = load_dataset()
    predictions = []

    for window, history, target in windows(df):
        started = time.time()
        for (state, disease), group_history in history.groupby(["state", "disease"]):
            group_target = target[(target["state"] == state) & (target["disease"] == disease)]
            predictions.append(
                group_target[["unique_id", "ds"]].assign(window=window, y_hat=fit_predict(group_history, group_target))
            )
        print(f"glm janela {window}: {time.time() - started:.0f}s", flush=True)

    save_predictions(pd.concat(predictions, ignore_index=True), "glm_estado")


if __name__ == "__main__":
    main()
