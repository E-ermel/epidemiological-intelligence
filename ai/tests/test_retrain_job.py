from google.cloud.run_v2.types import Condition, Execution

from epidemiological_agent.api.retrain_job import summarize_execution_status


def test_running_with_no_completed_condition_yet():
    execution = Execution(task_count=1, running_count=1)

    assert summarize_execution_status(execution) == "running"


def test_succeeded_from_completed_condition():
    execution = Execution(
        task_count=1,
        succeeded_count=1,
        conditions=[
            Condition(type_="Completed", state=Condition.State.CONDITION_SUCCEEDED)
        ],
    )

    assert summarize_execution_status(execution) == "succeeded"


def test_failed_from_completed_condition():
    execution = Execution(
        task_count=1,
        failed_count=1,
        conditions=[
            Condition(type_="Completed", state=Condition.State.CONDITION_FAILED)
        ],
    )

    assert summarize_execution_status(execution) == "failed"


def test_falls_back_to_counts_when_no_completed_condition_present():
    succeeded = Execution(task_count=1, succeeded_count=1)
    failed = Execution(task_count=1, failed_count=1)

    assert summarize_execution_status(succeeded) == "succeeded"
    assert summarize_execution_status(failed) == "failed"
