from airflow import DAG
from airflow.providers.google.cloud.operators.dataflow import DataflowStartPipelineOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryExecuteQueryOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'data_pipeline',
    default_args=default_args,
    description='Data pipeline for processing events',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['data_pipeline'],
) as dag:

    # Check for new batch files
    check_batch_files = GCSObjectExistenceSensor(
        task_id='check_batch_files',
        bucket='{{ var.value.raw_data_bucket }}',
        object='batch/{{ ds_nodash }}/*.json',
        google_cloud_conn_id='google_cloud_default',
    )

    # Start batch Dataflow job
    start_batch_pipeline = DataflowStartPipelineOperator(
        task_id='start_batch_pipeline',
        project_id='{{ var.value.project_id }}',
        location='{{ var.value.region }}',
        dataflow_config={
            'job_name': 'batch-pipeline-{{ ds_nodash }}',
            'temp_location': 'gs://{{ var.value.temp_bucket }}/temp',
            'staging_location': 'gs://{{ var.value.temp_bucket }}/staging',
            'template_location': 'gs://{{ var.value.template_bucket }}/templates/batch_template',
            'parameters': {
                'input_path': 'gs://{{ var.value.raw_data_bucket }}/batch/{{ ds_nodash }}/*.json',
                'output_table': '{{ var.value.project_id }}.events_dataset.events',
            },
        },
    )

    # Run data quality checks
    run_data_quality = BigQueryExecuteQueryOperator(
        task_id='run_data_quality',
        sql="""
        SELECT
            COUNT(*) as total_events,
            COUNT(DISTINCT device_id) as unique_devices,
            COUNT(DISTINCT event_type) as event_types
        FROM `{{ var.value.project_id }}.events_dataset.events`
        WHERE DATE(event_timestamp) = '{{ ds }}'
        """,
        use_legacy_sql=False,
    )

    # Set task dependencies
    check_batch_files >> start_batch_pipeline >> run_data_quality 