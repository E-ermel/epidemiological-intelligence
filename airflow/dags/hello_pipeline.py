from datetime import datetime
from airflow.sdk import DAG, task


with DAG(
    dag_id="hello_epidemiological_pipeline",
    start_date = datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["learning"],
) as dag:
    @task
    def process_inmet():
        print("INMET data processed")
    
    @task
    def process_sinan():
        print("SINAN data processed")
        
    @task
    def create_gold():
        print("Gold data created")
        
    inmet = process_inmet()
    sinan = process_sinan()
    gold = create_gold()
    
    [inmet, sinan] >> gold       

