# Databricks notebook source
from pyspark.sql import functions as F

INMET_SILVER_PATH = (
    "gs://epidemiological-intelligence/"
    "silver/inmet/"
)

SINAN_SILVER_PATH = (
    "gs://epidemiological-intelligence/"
    "silver/sinan/"
)

inmet = spark.read.parquet(INMET_SILVER_PATH)
sinan = spark.read.parquet(SINAN_SILVER_PATH)

# COMMAND ----------

inmet.printSchema()
sinan.printSchema()


# COMMAND ----------


print("INMET:", inmet.count())
print("SINAN:", sinan.count())

# COMMAND ----------

inmet_gold_base = (
    inmet
    .withColumn(
        "municipality_normalized",
        F.when(
            F.upper(F.col("municipality")).startswith("PORTO ALEGRE"),
            F.lit("PORTO ALEGRE")
        ).otherwise(
            F.col("municipality")
        )
    )
)

# COMMAND ----------

inmet_station_monthly = (
    inmet_gold_base
    .withColumn("year", F.year("timestamp"))
    .withColumn("month", F.month("timestamp"))

    .groupBy(
        "municipality_normalized",
        "station_code",
        "year",
        "month"
    )

    .agg(
        F.sum("precipitation_mm")
            .alias("precipitation_sum_mm"),

        F.avg("precipitation_mm")
            .alias("precipitation_avg_observation_mm"),

        F.max("precipitation_mm")
            .alias("precipitation_max_observation_mm"),

        F.avg("temperature_c")
            .alias("temperature_avg_c"),

        F.avg("dew_point_temperature_c")
            .alias("dew_point_avg_c"),

        F.avg("relative_humidity_pct")
            .alias("relative_humidity_avg_pct"),

        F.avg("atmospheric_pressure_mb")
            .alias("atmospheric_pressure_avg_mb"),

        F.avg("wind_speed_ms")
            .alias("wind_speed_avg_ms"),

        F.max("wind_gust_ms")
            .alias("wind_gust_max_ms")
    )
)

# COMMAND ----------

inmet_monthly = (
    inmet_station_monthly

    .groupBy(
        "municipality_normalized",
        "year",
        "month"
    )

    .agg(
        F.avg("precipitation_sum_mm")
            .alias("precipitation_sum_mm"),

        F.avg("precipitation_avg_observation_mm")
            .alias("precipitation_avg_observation_mm"),

        F.max("precipitation_max_observation_mm")
            .alias("precipitation_max_observation_mm"),

        F.avg("temperature_avg_c")
            .alias("temperature_avg_c"),

        F.avg("dew_point_avg_c")
            .alias("dew_point_avg_c"),

        F.avg("relative_humidity_avg_pct")
            .alias("relative_humidity_avg_pct"),

        F.avg("atmospheric_pressure_avg_mb")
            .alias("atmospheric_pressure_avg_mb"),

        F.avg("wind_speed_avg_ms")
            .alias("wind_speed_avg_ms"),

        F.max("wind_gust_max_ms")
            .alias("wind_gust_max_ms"),

        F.countDistinct("station_code")
            .alias("station_count")
    )

    .withColumnRenamed(
        "municipality_normalized",
        "municipality"
    )
)

# COMMAND ----------

display(
    inmet_monthly
    .filter(F.col("municipality") == "PORTO ALEGRE")
    .select(
        "municipality",
        "year",
        "month",
        "station_count",
        "precipitation_avg_mm",
        "temperature_avg_c"
    )
    .orderBy("year", "month")
)

# COMMAND ----------

duplicates = (
    inmet_monthly
    .groupBy(
        "municipality",
        "year",
        "month"
    )
    .count()
    .filter(F.col("count") > 1)
)

print("Duplicatas:", duplicates.count())

# COMMAND ----------

gold_df = (
    sinan
    .join(
        inmet_monthly,
        on=["municipality", "year", "month"],
        how="left"
    )
)

# COMMAND ----------

print("SINAN:", sinan.count())
print("GOLD:", gold_df.count())

print(
    "Sem clima:",
    gold_df.filter(F.col("precipitation_avg_mm").isNull()).count()
)

# COMMAND ----------

duplicates = (
    gold_df
    .groupBy(
        "disease",
        "municipality",
        "year",
        "month"
    )
    .count()
    .filter(F.col("count") > 1)
)

print("Duplicatas após join:", duplicates.count())

# COMMAND ----------

GOLD_PATH = (
    "gs://epidemiological-intelligence/"
    "gold/epidemiology_climate/"
)

(
    gold_df
    .write
    .mode("overwrite")
    .parquet(GOLD_PATH)
)

# COMMAND ----------

gold_test = spark.read.parquet(GOLD_PATH)

gold_test.printSchema()

# COMMAND ----------

print("Gold:", gold_test.count())