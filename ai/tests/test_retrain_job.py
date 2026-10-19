from google.cloud.run_v2.types import Condition, Execution, ListExecutionsResponse

from epidemiological_agent.api import retrain_job
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


class _FakePager:
    def __init__(self, executions):
        self.pages = iter([ListExecutionsResponse(executions=executions)] if executions else [])


class _FakeExecutionsClient:
    def __init__(self, executions):
        self._executions = executions
        self.requests = []

    def list_executions(self, request):
        self.requests.append(request)
        return _FakePager(self._executions)


def _patch_client(monkeypatch, executions):
    fake = _FakeExecutionsClient(executions)
    monkeypatch.setattr(retrain_job.run_v2, "ExecutionsClient", lambda: fake)
    return fake


def test_has_running_execution_true_when_latest_is_running(monkeypatch):
    finished = Execution(task_count=1, succeeded_count=1)
    running = Execution(task_count=1, running_count=1)
    fake = _patch_client(monkeypatch, [running, finished])

    assert retrain_job.has_running_execution() is True
    assert fake.requests[0].parent.endswith(f"/jobs/{retrain_job.DS_JOB_NAME}")


def test_has_running_execution_false_when_all_finished(monkeypatch):
    _patch_client(
        monkeypatch,
        [
            Execution(task_count=1, succeeded_count=1),
            Execution(task_count=1, failed_count=1),
        ],
    )

    assert retrain_job.has_running_execution() is False


def test_has_running_execution_false_when_job_never_ran(monkeypatch):
    _patch_client(monkeypatch, [])

    assert retrain_job.has_running_execution() is False
