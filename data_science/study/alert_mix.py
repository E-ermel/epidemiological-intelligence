"""
Cenário misto do canal endêmico: doenças do SIH (internações) com o canal
sem 2020-2021 (queda da pandemia) e doenças do SINAN com o canal normal.

Junta output/alert (canal normal) e output/alert_sem_pandemia em
output/alert_misto, escolhendo por doença os rótulos e as previsões de
cada modelo presente nos dois; depois:
    STUDY_ALERT_DIR=alert_misto python alert_evaluate.py

Uso: python alert_mix.py
"""

import pandas as pd

from common import OUTPUT_DIR

SIH_DISEASES = ["ASMA", "BRONQUITE AGUDA", "BRONQUITE CRÔNICA", "INFARTO AGUDO DO MIOCÁRDIO", "INSUFICIÊNCIA CARDÍACA"]
NORMAL, NO_PANDEMIC, MIXED = (OUTPUT_DIR / d for d in ("alert", "alert_sem_pandemia", "alert_misto"))


def mix(name: str) -> None:
    normal = pd.read_parquet(NORMAL / name)
    no_pandemic = pd.read_parquet(NO_PANDEMIC / name)
    sih = no_pandemic["disease"].astype(str).isin(SIH_DISEASES)
    mixed = pd.concat([no_pandemic[sih], normal[~normal["disease"].astype(str).isin(SIH_DISEASES)]], ignore_index=True)
    mixed.to_parquet(MIXED / name, index=False)
    print(f"{name}: {sih.sum()} linhas SIH sem pandemia + {len(mixed) - sih.sum()} SINAN")


def main() -> None:
    MIXED.mkdir(parents=True, exist_ok=True)
    common = sorted({p.name for p in NORMAL.glob("*.parquet")} & {p.name for p in NO_PANDEMIC.glob("*.parquet")})
    for name in common:
        mix(name)


if __name__ == "__main__":
    main()
