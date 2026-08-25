# Databricks notebook source
# MAGIC %md
# MAGIC ## 1. Imports e configuração
# MAGIC

# COMMAND ----------

from pyspark.sql import functions as F

BRONZE_PATH = "gs://epidemiological-intelligence/bronze/inmet/"
SILVER_PATH = "gs://epidemiological-intelligence/silver/inmet/"


# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Funções de leitura e transformação
# MAGIC

# COMMAND ----------

def read_inmet_raw(file_path):
    binary_df = (
        spark.read
        .format("binaryFile")
        .load(file_path)
    )

    raw = (
        binary_df
        .select(
            F.explode(
                F.split(
                    F.decode(F.col("content"), "ISO-8859-1"),
                    r"\r?\n"
                )
            ).alias("value")
        )
    )

    return raw


# COMMAND ----------

def extract_metadata(raw_df):
    metadata = {}

    rows = (
        raw_df
        .filter(~F.col("value").rlike(r"^\d{4}[-/]\d{2}[-/]\d{2};"))
        .limit(8)
        .collect()
    )

    for row in rows:
        line = row["value"]

        if ";" not in line:
            continue

        key, value = line.split(";", 1)
        key = key.strip().upper()
        value = value.strip()

        if "ESTAÇÃO" in key or "ESTACAO" in key:
            metadata["station_name"] = value
        elif "CODIGO" in key:
            metadata["station_code"] = value
        elif key.startswith("UF"):
            metadata["state"] = value
        elif "LATITUDE" in key:
            metadata["latitude"] = value.replace(",", ".")
        elif "LONGITUDE" in key:
            metadata["longitude"] = value.replace(",", ".")
        elif "ALTITUDE" in key:
            metadata["altitude"] = value.replace(",", ".")

    return metadata


# COMMAND ----------

def parse_inmet_file(file_path):
    raw = read_inmet_raw(file_path)
    metadata = extract_metadata(raw)

    data_lines = raw.filter(
        F.col("value").rlike(r"^\d{4}[-/]\d{2}[-/]\d{2};")
    )

    parsed = data_lines.withColumn(
        "fields",
        F.split(F.col("value"), ";")
    )

    df = parsed.select(
        F.col("fields")[0].alias("date"),
        F.col("fields")[1].alias("hour"),
        F.col("fields")[2].alias("precipitation_mm"),
        F.col("fields")[3].alias("atmospheric_pressure_mb"),
        F.col("fields")[7].alias("temperature_c"),
        F.col("fields")[8].alias("dew_point_temperature_c"),
        F.col("fields")[15].alias("relative_humidity_pct"),
        F.col("fields")[16].alias("wind_direction_deg"),
        F.col("fields")[17].alias("wind_gust_ms"),
        F.col("fields")[18].alias("wind_speed_ms"),
    )

    numeric_columns = [
        "precipitation_mm",
        "atmospheric_pressure_mb",
        "temperature_c",
        "dew_point_temperature_c",
        "relative_humidity_pct",
        "wind_direction_deg",
        "wind_gust_ms",
        "wind_speed_ms",
    ]

    for column in numeric_columns:
        df = df.withColumn(
            column,
            F.trim(
                F.regexp_replace(F.col(column), ",", ".")
            )
        )

        df = df.withColumn(
            column,
            F.when(
                (F.col(column) == "-9999") |
                (F.col(column) == ""),
                None
            ).otherwise(
                F.expr(f"try_cast(`{column}` as double)")
            )
        )

    # Normaliza os formatos de data encontrados nos arquivos do INMET.
    df = df.withColumn(
        "date",
        F.regexp_replace(F.col("date"), "/", "-")
    )

    # Normaliza formatos como "0000 UTC" para "00:00".
    df = df.withColumn(
        "hour",
        F.regexp_replace(
            F.trim(F.col("hour")),
            r"\s*UTC$",
            ""
        )
    )

    df = df.withColumn(
        "hour",
        F.when(
            F.col("hour").rlike(r"^\d{4}$"),
            F.concat(
                F.substring("hour", 1, 2),
                F.lit(":"),
                F.substring("hour", 3, 2)
            )
        ).otherwise(F.col("hour"))
    )

    df = df.withColumn(
        "timestamp",
        F.to_timestamp(
            F.concat_ws(" ", F.col("date"), F.col("hour")),
            "yyyy-MM-dd HH:mm"
        )
    ).drop("date", "hour")

    df = (
        df
        .withColumn("station_code", F.lit(metadata.get("station_code")))
        .withColumn("station_name", F.lit(metadata.get("station_name")))
        .withColumn(
            "municipality",
            F.upper(F.trim(F.lit(metadata.get("station_name"))))
        )
        .withColumn("state", F.lit(metadata.get("state")))
        .withColumn("latitude", F.lit(metadata.get("latitude")).cast("double"))
        .withColumn("longitude", F.lit(metadata.get("longitude")).cast("double"))
        .withColumn("altitude", F.lit(metadata.get("altitude")).cast("double"))
        .withColumn("source_file", F.lit(file_path))
        .withColumn("ingestion_timestamp", F.current_timestamp())
    )

    return df


# COMMAND ----------

def list_csv_files(path):
    csv_files = []

    for item in dbutils.fs.ls(path):
        if item.isDir():
            csv_files.extend(list_csv_files(item.path))
        elif item.path.lower().endswith(".csv"):
            csv_files.append(item)

    return csv_files


# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Processamento Bronze → DataFrame Silver
# MAGIC

# COMMAND ----------

files = list_csv_files(BRONZE_PATH)

print("Arquivos CSV encontrados:", len(files))

all_dfs = []

for file in files:
    all_dfs.append(parse_inmet_file(file.path))

if not all_dfs:
    raise ValueError("Nenhum arquivo CSV do INMET foi encontrado.")

print("DataFrames processados:", len(all_dfs))


# COMMAND ----------

inmet_silver_df = all_dfs[0]

for df in all_dfs[1:]:
    inmet_silver_df = inmet_silver_df.unionByName(
        df,
        allowMissingColumns=True
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Padronização final
# MAGIC

# COMMAND ----------

# Em alguns arquivos (especialmente 2019), o nome da estação não foi
# recuperado do cabeçalho. O nome do arquivo é usado como fallback.

inmet_silver_df = inmet_silver_df.withColumn(
    "municipality_from_file",
    F.regexp_extract(
        F.col("source_file"),
        r"INMET_S_RS_[A-Z0-9]+_(.*?)_\d{2}-\d{2}-\d{4}",
        1
    )
)

inmet_silver_df = inmet_silver_df.withColumn(
    "municipality",
    F.when(
        F.col("municipality").isNull(),
        F.upper(F.trim(F.col("municipality_from_file")))
    ).otherwise(F.col("municipality"))
)

inmet_silver_df = inmet_silver_df.withColumn(
    "station_name",
    F.when(
        F.col("station_name").isNull(),
        F.col("municipality")
    ).otherwise(F.col("station_name"))
)

inmet_silver_df = (
    inmet_silver_df
    .drop("municipality_from_file")
    .withColumn("year", F.year("timestamp"))
)


# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Data Quality
# MAGIC

# COMMAND ----------

print("Total de registros:", inmet_silver_df.count())
print(
    "Timestamps nulos:",
    inmet_silver_df.filter(F.col("timestamp").isNull()).count()
)
print(
    "Municipality nulos:",
    inmet_silver_df.filter(F.col("municipality").isNull()).count()
)
print(
    "Station name nulos:",
    inmet_silver_df.filter(F.col("station_name").isNull()).count()
)
print(
    "Station code nulos:",
    inmet_silver_df.filter(F.col("station_code").isNull()).count()
)
print(
    "Precipitações negativas:",
    inmet_silver_df.filter(F.col("precipitation_mm") < 0).count()
)


# COMMAND ----------

duplicates = (
    inmet_silver_df
    .groupBy("station_code", "timestamp")
    .count()
    .filter(F.col("count") > 1)
)

print("Duplicatas station_code + timestamp:", duplicates.count())


# COMMAND ----------

quality_columns = [
    "precipitation_mm",
    "atmospheric_pressure_mb",
    "temperature_c",
    "dew_point_temperature_c",
    "relative_humidity_pct",
    "wind_direction_deg",
    "wind_gust_ms",
    "wind_speed_ms",
]

total = inmet_silver_df.count()

quality_df = inmet_silver_df.select([
    F.count(F.when(F.col(c).isNull(), c)).alias(f"{c}_nulls")
    for c in quality_columns
])

null_percentages = inmet_silver_df.select([
    (
        F.count(F.when(F.col(c).isNull(), c)) /
        F.lit(total) * 100
    ).alias(f"{c}_null_pct")
    for c in quality_columns
])

display(quality_df)
display(null_percentages)


# COMMAND ----------

display(
    inmet_silver_df
    .groupBy("year")
    .agg(
        F.count("*").alias("registros"),
        F.countDistinct("station_code").alias("estacoes")
    )
    .orderBy("year")
)


# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Escrita da camada Silver
# MAGIC

# COMMAND ----------

(
    inmet_silver_df
    .write
    .mode("overwrite")
    .partitionBy("year")
    .parquet(SILVER_PATH)
)


# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Validação pós-escrita
# MAGIC

# COMMAND ----------

silver_test = spark.read.parquet(SILVER_PATH)

original_count = inmet_silver_df.count()
silver_count = silver_test.count()

print("Original:", original_count)
print("Silver:", silver_count)

if original_count != silver_count:
    raise ValueError(
        f"Contagem divergente: original={original_count}, silver={silver_count}"
    )


# COMMAND ----------

display(
    silver_test
    .groupBy("year")
    .agg(
        F.count("*").alias("registros"),
        F.countDistinct("station_code").alias("estacoes")
    )
    .orderBy("year")
)
