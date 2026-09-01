from google.cloud import run_v2
from google.cloud.run_v2.types import Condition, Execution

from epidemiological_agent.config import DS_JOB_NAME, GCP_REGION, PROJECT_ID


def trigger_retrain(disease: str | None = None) -> str:
    """
    Starts an execution of the data_science Cloud Run Job
    ("epidemiological-ds-modeling", google_cloud_run_v2_job.data_science
    in infrastructure/terraform/cloud_run.tf), optionally filtered to a
    single disease via a DISEASE_FILTER env override -- see
    data_science/src/epidemiological_intelligence/run_all_models.py.
    Passing disease=None (the "Retreinar modelos" bulk action) runs
    every disease in one execution, same as the scheduled/Airflow-driven
    run.

    Fire-and-forget: the job takes up to an hour, so this returns the
    started Execution's resource name as soon as it's accepted, without
    waiting for training to finish -- pass it to get_execution_status()
    to poll progress.
    """

    client = run_v2.JobsClient()

    overrides = None
    if disease is not None:
        overrides = run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    env=[run_v2.EnvVar(name="DISEASE_FILTER", value=disease)]
                )
            ]
        )

    request = run_v2.RunJobRequest(
        name=f"projects/{PROJECT_ID}/locations/{GCP_REGION}/jobs/{DS_JOB_NAME}",
        overrides=overrides,
    )

    operation = client.run_job(request=request)

    # operation.metadata is an Execution message populated synchronously
    # as soon as Cloud Run accepts the request -- its .name is the real
    # Execution resource name. operation.operation.name is a *different*,
    # LRO-internal name that ExecutionsClient.get_execution() can't look
    # up, so it must not be used here even though it's also a string.
    return operation.metadata.name


def get_execution_status(execution_name: str) -> Execution:
    """
    Fetches the current state of a retrain execution previously started
    by trigger_retrain() -- backs GET /models/retrain/status, polled by
    the frontend while a retrain is in progress.
    """

    client = run_v2.ExecutionsClient()
    return client.get_execution(name=execution_name)


def summarize_execution_status(execution: Execution) -> str:
    """
    Collapses an Execution's conditions/task counts into one of
    "running" / "succeeded" / "failed" for the frontend. The Cloud Run
    Job here has a single task (the container loops over diseases
    itself -- see run_all_models.py), so this is a job-level status,
    not per-disease progress; log_uri on the response is how the UI
    lets you see what's actually happening inside that task.
    """

    completed = next(
        (c for c in execution.conditions if c.type_ == "Completed"), None
    )
    if completed is not None:
        if completed.state == Condition.State.CONDITION_SUCCEEDED:
            return "succeeded"
        if completed.state == Condition.State.CONDITION_FAILED:
            return "failed"

    if execution.failed_count > 0:
        return "failed"
    if execution.task_count > 0 and execution.succeeded_count >= execution.task_count:
        return "succeeded"
    return "running"
