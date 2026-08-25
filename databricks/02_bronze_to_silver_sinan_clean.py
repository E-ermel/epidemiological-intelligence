# Databricks notebook source
from pyspark.sql import functions as F

sinan_path = "gs://epidemiological-intelligence/bronze/sinan/lesptospirose.csv"

df =(
    spark.read
    .option("header", True)
    .option("sep", ";")
    .option("encoding", "ISO-8859-1")
    .csv(sinan_path)
)

# COMMAND ----------

def process_sinan_file(file_path, disease_name):

    # 1. Lê o arquivo bruto
    df = (
        spark.read
        .option("header", True)
        .option("sep", ";")
        .option("encoding", "ISO-8859-1")
        .csv(file_path)
    )

    # 2. Descobre as colunas mensais
    municipality_column = df.columns[0]

    month_columns = [
        c for c in df.columns
        if c != municipality_column
    ]

    # 3. Wide -> Long
    df_long = (
        df
        .select(
            F.col(municipality_column).alias("municipio"),

            F.explode(
                F.array(*[
                    F.struct(
                        F.lit(c).alias("ano_mes"),
                        F.col(c).alias("valor")
                    )
                    for c in month_columns
                ])
            ).alias("registro")
        )
        .select(
            "municipio",
            F.col("registro.ano_mes").alias("ano_mes"),
            F.col("registro.valor").alias("valor")
        )
    )
    df_long = (
        df_long
        .withColumn(
            "year",
            F.split(
                F.col("ano_mes"),
                "/"
            ).getItem(0).cast("int")
        )
        .withColumn(
            "month_name",
            F.split(
                F.col("ano_mes"),
                "/"
            ).getItem(1)
        )
    )
    month_map = {
        "Jan": 1,
        "Fev": 2,
        "Mar": 3,
        "Abr": 4,
        "Mai": 5,
        "Jun": 6,
        "Jul": 7,
        "Ago": 8,
        "Set": 9,
        "Out": 10,
        "Nov": 11,
        "Dez": 12
    }

    month_mapping = F.create_map(
        *[
            item
            for pair in month_map.items()
            for item in (
                F.lit(pair[0]),
                F.lit(pair[1])
            )
        ]
    )

    df_long = df_long.withColumn(
        "month",
        month_mapping[F.col("month_name")]
    )

    df_long = df_long.withColumn(
        "cases",

        F.when(
            F.trim(F.col("valor")) == "SEM",
            F.lit(None).cast("int")
        )

        .when(
            F.trim(F.col("valor")) == "-",
            F.lit(0)
        )

        .otherwise(
            F.expr(
                "try_cast(trim(valor) as int)"
            )
        )
    )
    df_long = (
        df_long

        .withColumn(
            "municipality_code",
            F.regexp_extract(
                F.col("municipio"),
                r"^(\d+)",
                1
            )
        )

        .withColumn(
            "municipality",
            F.upper(
                F.trim(
                    F.regexp_replace(
                        F.col("municipio"),
                        r"^\d+\s*",
                        ""
                    )
                )
            )
        )
    )
    df_long = df_long.withColumn(
        "reference_date",

        F.to_date(
            F.concat_ws(
                "-",
                F.col("year"),
                F.lpad(
                    F.col("month"),
                    2,
                    "0"
                ),
                F.lit("01")
            ),
            "yyyy-MM-dd"
        )
    )

    df_long = (
        df_long

        .withColumn(
            "disease",
            F.lit(disease_name)
        )

        .withColumn(
            "source_file",
            F.lit(file_path)
        )

        .withColumn(
            "ingestion_timestamp",
            F.current_timestamp()
        )
    )
    df_silver = df_long.select(
        "municipality_code",
        "municipality",
        "year",
        "month",
        "reference_date",
        "cases",
        "disease",
        "source_file",
        "ingestion_timestamp"
)

    return df_silver


# COMMAND ----------

lepto_df = process_sinan_file(
    sinan_path,
    "LEPTOSPIROSE"
)

# COMMAND ----------

lepto_df.printSchema()

display(
    lepto_df.limit(20)
)

# COMMAND ----------

print(
    "Registros:",
    lepto_df.count()
)

# COMMAND ----------

sinan_base_path = "gs://epidemiological-intelligence/bronze/sinan/"

sinan_files = dbutils.fs.ls(sinan_base_path)

for file in sinan_files:
    print(file.name, file.path)

# COMMAND ----------

disease_map = {
    "asma.csv": "ASMA",
    "bronquite_aguda.csv": "BRONQUITE AGUDA",
    "bronquite_cronica.csv": "BRONQUITE CRÔNICA",
    "infarto.csv": "INFARTO AGUDO DO MIOCÁRDIO",
    "insuficiencia_cardiaca.csv": "INSUFICIÊNCIA CARDÍACA",
    "lesptospirose.csv": "LEPTOSPIROSE",
}

# COMMAND ----------

disease_dfs = []

for file in sinan_files:
    file_name = file.name.strip().lower()

    disease_name = disease_map.get(file_name)

    if disease_name is None:
        print("Arquivo ignorado:", file.name)
        continue

    print("Processando:", disease_name)

    df_disease = process_sinan_file(
        file.path,
        disease_name
    )

    disease_dfs.append(df_disease)

    if not disease_dfs:
        raise ValueError("Nenhum dataset epidemiológico foi processado.")

    sinan_silver_df = disease_dfs[0]

    for df in disease_dfs[1:]:
        sinan_silver_df = sinan_silver_df.unionByName(
            df,
            allowMissingColumns=True
        )

# COMMAND ----------

display(
    sinan_silver_df
    .groupBy("disease")
    .agg(
        F.count("*").alias("registros"),
        F.countDistinct("municipality_code").alias("municipios")
    )
    .orderBy("disease")
)
duplicates = (
    sinan_silver_df
    .groupBy(
        "disease",
        "municipality_code",
        "year",
        "month"
    )
    .count()
    .filter(F.col("count") > 1)
)

print("Duplicatas:", duplicates.count())

# COMMAND ----------

display(
    sinan_silver_df
    .groupBy("disease", "year")
    .agg(
        F.count("*").alias("registros"),
        F.count(
            F.when(F.col("cases").isNull(), True)
        ).alias("cases_null")
    )
    .orderBy("disease", "year")
)

# COMMAND ----------

SINAN_SILVER_PATH = (
    "gs://epidemiological-intelligence/"
    "silver/sinan/"
)

(
    sinan_silver_df
    .write
    .mode("overwrite")
    .partitionBy("disease", "year")
    .parquet(SINAN_SILVER_PATH)
)

# COMMAND ----------

sinan_silver_test = spark.read.parquet(
    SINAN_SILVER_PATH
)

print("Original:", sinan_silver_df.count())
print("Silver:", sinan_silver_test.count())

# COMMAND ----------

display(
    sinan_silver_test
    .groupBy("disease")
    .agg(
        F.count("*").alias("records"),
        F.sum("cases").alias("total_cases"),
        F.count(
            F.when(F.col("cases").isNull(), True)
        ).alias("null_cases")
    )
    .orderBy("disease")
)