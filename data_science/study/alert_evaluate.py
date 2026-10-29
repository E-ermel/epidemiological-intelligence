"""
Parte B, avaliação do alerta. Lê as probabilidades de cada modelo
(OUTPUT_DIR/alert/<modelo>_<nível>.parquet), escolhe o corte de cada
modelo × nível no ano de calibração (2023, maior F1) e mede no teste
(2024-2025), só nas linhas que todos os modelos do nível preveem:

- metrics.csv: geral por modelo × nível;
- metrics_horizon.csv / metrics_disease.csv: o mesmo por horizonte e
  por doença (com o corte geral);
- confusion.csv: matriz de confusão (VP, FP, FN, VN) geral;
- metrics_group_cutoff.csv: geral, mas com um corte por doença ×
  horizonte (também escolhido em 2023; grupo com menos de
  MIN_GROUP_POSITIVES surtos na calibração fica com o corte geral);
- case_rs_lepto_2024.csv: probabilidade de cada modelo para
  leptospirose no RS em 2024 (enchente de maio), horizonte 1.

Uso: python alert_evaluate.py
"""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from alert_features import load_labels
from common import ALERT_DIR, CALIBRATION_TARGETS, TEST_TARGETS

EVAL_DIR = ALERT_DIR / "eval"
CASE_SERIES = "LEPTOSPIROSE|RS"
CASE_MONTHS = ("2024-01-01", "2024-12-01")
MIN_GROUP_POSITIVES = 20


def load_predictions() -> pd.DataFrame:
    paths = [p for p in sorted(ALERT_DIR.glob("*.parquet")) if not p.name.startswith("labels_")]
    frames = []
    for level in ("uf", "municipio"):
        level_frames = [
            pd.read_parquet(p).astype({"ds": "datetime64[ns]", "horizon": "int64", "disease": str, "state": str})
            for p in paths if p.stem.endswith(f"_{level}")
        ]
        if not level_frames:
            continue
        truth = load_labels(level)[["series_id", "ds", "y", "threshold", "outbreak"]]
        df = pd.concat(level_frames, ignore_index=True)
        df["model"] = df["model"].str.removesuffix(f"_{level}")
        df = df.merge(truth, on=["series_id", "ds"], how="inner")
        df = df[(df["outbreak"] >= 0) & df["probability"].notna()]  # TimesFM: NaN na 1ª origem

        # Mesmas linhas para todos os modelos do nível.
        key = ["series_id", "ds", "horizon"]
        counts = df.groupby(key)["model"].transform("nunique")
        df = df[counts == df["model"].nunique()]
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def best_cutoff(y: np.ndarray, p: np.ndarray) -> float:
    """Corte que maximiza o F1 (alerta se p >= corte)."""

    candidates = np.unique(np.quantile(p, np.linspace(0, 1, 401)))
    candidates = candidates[candidates > 0] if (candidates > 0).any() else candidates
    best, best_f1 = 0.5, -1.0
    for c in candidates:
        alert = p >= c
        tp = (alert & (y == 1)).sum()
        f1 = 2 * tp / (alert.sum() + (y == 1).sum()) if alert.sum() + (y == 1).sum() else 0.0
        if f1 > best_f1:
            best, best_f1 = float(c), f1
    return best


def scores(y: np.ndarray, p: np.ndarray, cutoff: float) -> dict:
    alert = p >= cutoff
    tp = int((alert & (y == 1)).sum())
    fp = int((alert & (y == 0)).sum())
    fn = int((~alert & (y == 1)).sum())
    tn = int((~alert & (y == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    both = len(np.unique(y)) == 2
    return {
        "n": len(y),
        "outbreak_pct": float(y.mean() * 100),
        "accuracy": (tp + tn) / len(y),
        "balanced_accuracy": (recall + specificity) / 2,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "auc_pr": average_precision_score(y, p) if both else np.nan,
        "auc_roc": roc_auc_score(y, p) if both else np.nan,
        "brier": float(np.mean((p - y) ** 2)),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def evaluate(df: pd.DataFrame, by: list[str], cutoffs: dict) -> pd.DataFrame:
    rows = []
    for key, group in df.groupby(["level", "model", *by], observed=True):
        key = key if isinstance(key, tuple) else (key,)
        cutoff = cutoffs[key[:2]]
        rows.append({**dict(zip(["level", "model", *by], key)), "cutoff": cutoff,
                     **scores(group["outbreak"].to_numpy(), group["probability"].to_numpy(), cutoff)})
    return pd.DataFrame(rows)


def group_cutoff_metrics(calibration: pd.DataFrame, test: pd.DataFrame, cutoffs: dict) -> pd.DataFrame:
    """Métricas gerais com um corte por doença × horizonte."""

    group = ["disease", "horizon"]
    rows = []
    for (level, model), cal in calibration.groupby(["level", "model"]):
        if cutoffs[(level, model)] == 0.5 and np.isin(cal["probability"], [0.0, 1.0]).all():
            continue  # persistência e sazonal: 0/1, sem corte a escolher
        by_group = {}
        for key, g in cal.groupby(group):
            y = g["outbreak"].to_numpy()
            by_group[key] = (
                best_cutoff(y, g["probability"].to_numpy()) if y.sum() >= MIN_GROUP_POSITIVES
                else cutoffs[(level, model)]
            )
        t = test[(test["level"] == level) & (test["model"] == model)]
        cut = np.array([by_group.get(k, cutoffs[(level, model)]) for k in zip(t["disease"], t["horizon"])])
        alert = (t["probability"].to_numpy() >= cut).astype(float)
        # scores() aplica o corte; aqui o alerta já vem decidido (0/1).
        s = scores(t["outbreak"].to_numpy(), alert, 0.5)
        s["auc_pr"], s["auc_roc"] = (
            average_precision_score(t["outbreak"], t["probability"]),
            roc_auc_score(t["outbreak"], t["probability"]),
        )
        s["brier"] = float(np.mean((t["probability"] - t["outbreak"]) ** 2))
        rows.append({"level": level, "model": model, **s})
    return pd.DataFrame(rows).sort_values(["level", "f1"], ascending=[True, False])


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    df = load_predictions()
    calibration = df[df["ds"].between(*CALIBRATION_TARGETS)]
    test = df[df["ds"].between(*TEST_TARGETS)]

    cutoffs = {}
    for (level, model), group in calibration.groupby(["level", "model"]):
        p = group["probability"].to_numpy()
        binary = np.isin(p, [0.0, 1.0]).all()  # persistência e sazonal: 0/1
        cutoffs[(level, model)] = 0.5 if binary else best_cutoff(group["outbreak"].to_numpy(), p)

    overall = evaluate(test, [], cutoffs).sort_values(["level", "f1"], ascending=[True, False])
    overall.to_csv(EVAL_DIR / "metrics.csv", index=False)
    overall[["level", "model", "tp", "fp", "fn", "tn"]].to_csv(EVAL_DIR / "confusion.csv", index=False)
    evaluate(test, ["horizon"], cutoffs).to_csv(EVAL_DIR / "metrics_horizon.csv", index=False)
    evaluate(test, ["disease"], cutoffs).to_csv(EVAL_DIR / "metrics_disease.csv", index=False)
    group_cutoff_metrics(calibration, test, cutoffs).to_csv(EVAL_DIR / "metrics_group_cutoff.csv", index=False)

    case = df[(df["series_id"] == CASE_SERIES) & (df["horizon"] == 1) & df["ds"].between(*CASE_MONTHS)]
    case = case.assign(alert=[p >= cutoffs[(lv, m)] for lv, m, p in zip(case["level"], case["model"], case["probability"])])
    case.pivot_table(index=["ds", "y", "threshold", "outbreak"], columns="model", values="probability").round(3).to_csv(
        EVAL_DIR / "case_rs_lepto_2024.csv"
    )

    pd.set_option("display.width", 200)
    columns = ["level", "model", "cutoff", "accuracy", "balanced_accuracy", "precision", "recall", "f1", "auc_pr",
               "auc_roc", "brier"]
    print(overall[columns].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
