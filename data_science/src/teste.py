from epidemiological_intelligence.data.bigquery import (
    load_gold_from_bigquery,
)

from epidemiological_intelligence.pipeline.run_modeling import (
    run_disease_pipeline,
)


df = load_gold_from_bigquery()

result = run_disease_pipeline(
    df=df,
    disease="LEPTOSPIROSE",
)

print(result["version"])
print(result["metadata"])