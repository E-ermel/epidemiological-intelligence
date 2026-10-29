#!/usr/bin/env bash
# Teste do alerta com o canal endêmico sem 2020-2021 (falsos surtos da
# pandemia). Tudo vai para output/alert_sem_pandemia/, sem tocar no
# alerta atual. Espera a GPU ficar livre antes do Chronos-2.
set -u
cd "$(dirname "$0")"
PY=../benchmarks/.venv/Scripts/python.exe
export PYTHONIOENCODING=utf-8 STUDY_ALERT_DIR=alert_sem_pandemia STUDY_CHANNEL_EXCLUDE=2020,2021
LOG=output/logs/sem_pandemia.log
mkdir -p output/logs

echo "== rótulos $(date +%T)" >> "$LOG"
$PY -u alert_prepare.py >> "$LOG" 2>&1 || { echo "FALHOU alert_prepare"; exit 1; }
echo "== modelos com atributos $(date +%T)" >> "$LOG"
$PY -u alert_models.py >> "$LOG" 2>&1 || { echo "FALHOU alert_models"; exit 1; }

# A GPU está com os cenários de previsão do tempo; o último a rodar é
# chronos2_cross_climatologia (municipio).
GPU_DONE=output/logs/foundation_chronos2_cross_climatologia.log
until grep -q "chronos2_cross_climatologia municipio:" "$GPU_DONE" 2>/dev/null; do
  sleep 60
done
echo "== chronos2_clima_cross $(date +%T)" >> "$LOG"
$PY -u alert_foundation.py chronos2_clima_cross >> "$LOG" 2>&1 || { echo "FALHOU chronos"; exit 1; }
echo "== avaliação $(date +%T)" >> "$LOG"
$PY -u alert_evaluate.py >> "$LOG" 2>&1 || { echo "FALHOU avaliação"; exit 1; }
echo "== fim $(date +%T)" >> "$LOG"
