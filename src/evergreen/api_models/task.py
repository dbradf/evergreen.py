# -*- encoding: utf-8 -*-
"""Task representation of evergreen."""
from datetime import datetime, timedelta
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Union

from pydantic import BaseModel, Extra, PrivateAttr

from evergreen.api_models.manifest import Manifest
from evergreen.api_models.task_annotations import TaskAnnotation
from evergreen.api_requests import IssueLinkRequest

if TYPE_CHECKING:
    from evergreen.api import EvergreenApi
    from evergreen.tst import Tst  # noqa: F401

EVG_SUCCESS_STATUS = "success"
EVG_SYSTEM_FAILURE_STATUS = "system"
EVG_UNDISPATCHED_STATUS = "undispatched"

_EVG_DATE_FIELDS_IN_TASK = frozenset(
    ["create_time", "dispatch_time", "finish_time", "ingest_time", "scheduled_time", "start_time"]
)


class Artifact(BaseModel):
    """Representation of a task artifact from evergreen."""

    name: str
    url: str
    visibility: str
    ignore_for_fetch: bool


class StatusScore(IntEnum):
    """Integer score of the task status."""

    SUCCESS = 1
    FAILURE = 2
    FAILURE_SYSTEM = 3
    FAILURE_TIMEOUT = 4
    UNDISPATCHED = 5

    @classmethod
    def get_task_status_score(cls, task: "Task") -> "StatusScore":
        """
        Retrieve the status score based on the task status.

        :return: Status score.
        """
        if task.is_success():
            return StatusScore.SUCCESS
        if task.is_undispatched():
            return StatusScore.UNDISPATCHED
        if task.is_timeout():
            return StatusScore.FAILURE_TIMEOUT
        if task.is_system_failure():
            return StatusScore.FAILURE_SYSTEM
        return StatusScore.FAILURE


class StatusDetails(BaseModel):
    """Representation of a task status details from evergreen."""

    status: str
    type: str
    desc: str
    timed_out: bool


class DisplayTaskDependency(BaseModel):
    """Dependency on a display task."""

    id: str
    status: str


class Task(BaseModel):
    """Representation of an Evergreen task."""

    activated: bool
    activated_by: str
    artifacts: Optional[List[Artifact]]
    build_id: str
    build_variant: str
    create_time: datetime
    depends_on: Optional[List[Union[str, DisplayTaskDependency]]]
    dispatch_time: Optional[datetime]
    display_name: str
    display_only: bool
    distro_id: str
    est_wait_to_start_ms: int
    estimated_cost: float
    execution: int
    execution_tasks: Optional[List[str]]
    expected_duration_ms: int
    finish_time: Optional[datetime]
    generate_task: bool
    generated_by: str
    host_id: str
    ingest_time: Optional[datetime]
    logs: Dict[str, Optional[str]]
    mainline: Optional[bool]
    order: int
    project_id: str
    priority: int
    restarts: int
    revision: str
    scheduled_time: Optional[datetime]
    start_time: Optional[datetime]
    status: str
    status_details: StatusDetails
    task_group: Optional[str]
    task_group_max_hosts: Optional[int]
    task_id: str
    time_taken_ms: int
    version_id: str

    _api: "EvergreenApi" = PrivateAttr()

    def __init__(self, api: "EvergreenApi", **json: Dict[str, Any]) -> None:
        """Create an instance of an evergreen task."""
        super().__init__(**json)

        self._api = api

    def retrieve_log(self, log_name: str, raw: bool = False) -> str:
        """
        Retrieve the contents of the specified log.

        :param log_name: Name of log to retrieve.
        :param raw: Retrieve raw version of log.
        :return: Contents of the specified log.
        """
        log_url = self.logs.get(log_name)
        if log_url:
            return self._api.retrieve_task_log(log_url, raw)
        return ""

    def stream_log(self, log_name: str) -> Iterable[str]:
        """
        Retrieve an iterator of a streamed log contents for the given log.

        :param log_name: Log to stream.
        :return: Iterable log contents.
        """
        log_url = self.logs.get(log_name)
        if log_url:
            return self._api.stream_log(log_url)
        return []

    def get_status_score(self) -> StatusScore:
        """
        Retrieve the status score enum for the given task.

        :return: Status score.
        """
        return StatusScore.get_task_status_score(self)

    def get_execution(self, execution: int) -> Optional["Task"]:
        """
        Get the task info for the specified execution.

        :param execution: Index of execution.
        :return: Task info for specified execution.
        """
        if self.execution == execution:
            return self

        raw_task = self.dict()
        for task in raw_task.get("previous_executions", []):
            if task.get("execution") == execution:
                return Task(self._api, **task)

        return None

    def get_execution_or_self(self, execution: int) -> "Task":
        """
        Get the specified execution if it exists.

        If the specified execution does not exist, return self.

        :param execution: Index of execution.
        :return: Task info for specified execution or self.
        """
        task_execution = self.get_execution(execution)
        if task_execution:
            return task_execution
        return self

    def wait_time(self) -> Optional[timedelta]:
        """
        Get the time taken until the task started running.

        :return: Time taken until task started running.
        """
        if self.start_time and self.ingest_time:
            return self.start_time - self.ingest_time
        return None

    def wait_time_once_unblocked(self) -> Optional[timedelta]:
        """
        Get the time taken until the task started running.

        Once it is unblocked by task dependencies.

        :return: Time taken until task started running.
        """
        if self.start_time and self.scheduled_time:
            return self.start_time - self.scheduled_time
        return None

    def is_success(self) -> bool:
        """
        Whether task was successful.

        :return: True if task was successful.
        """
        return self.status == EVG_SUCCESS_STATUS

    def is_undispatched(self) -> bool:
        """
        Whether the task was undispatched.

        :return: True is task was undispatched.
        """
        return self.status == EVG_UNDISPATCHED_STATUS

    def is_system_failure(self) -> bool:
        """
        Whether task resulted in a system failure.

        :return: True if task was a system failure.
        """
        if not self.is_success() and self.status_details and self.status_details.type:
            return self.status_details.type == EVG_SYSTEM_FAILURE_STATUS
        return False

    def is_timeout(self) -> bool:
        """
        Whether task results in a timeout.

        :return: True if task was a timeout.
        """
        if not self.is_success() and self.status_details and self.status_details.timed_out:
            return self.status_details.timed_out
        return False

    def is_active(self) -> bool:
        """
        Determine if the given task is active.

        :return: True if task is active.
        """
        return bool(self.scheduled_time and not self.finish_time)

    def get_tests(
        self, status: Optional[str] = None, execution: Optional[int] = None
    ) -> List["Tst"]:
        """
        Get the test results for this task.

        :param status: Only return tests with the given status.
        :param execution: Return results for specified execution, if specified.
        :return: List of test results for the task.
        """
        return self._api.tests_by_task(
            self.task_id,
            status=status,
            execution=self.execution if execution is None else execution,
        )

    def get_execution_tasks(
        self, filter_fn: Optional[Callable[["Task"], bool]] = None
    ) -> Optional[List["Task"]]:
        """
        Get a list of execution tasks associated with this task.

        If this is a display task, return the tasks execution tasks associated with it.
        If this is not a display task, returns None.

        :param filter_fn: Function to filter returned results.
        :return: List of execution tasks.
        """
        if self.display_only:
            if not self.execution_tasks:
                return []

            execution_tasks = [
                self._api.task_by_id(task_id, fetch_all_executions=True)
                for task_id in self.execution_tasks
            ]

            execution_tasks = [
                task.get_execution_or_self(self.execution) for task in execution_tasks
            ]

            if filter_fn:
                return [task for task in execution_tasks if filter_fn(task)]

            return execution_tasks

        return None

    def get_manifest(self) -> Manifest:
        """Get the Manifest for this task."""
        return self._api.manifest_for_task(self.task_id)

    def get_task_annotation(self) -> List[TaskAnnotation]:
        """Get the task annotation for this task."""
        return self._api.get_task_annotation(self.task_id, self.execution)

    def annotate(
        self,
        message: Optional[str] = None,
        issues: Optional[List[IssueLinkRequest]] = None,
        suspected_issues: Optional[List[IssueLinkRequest]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Annotate the specified task.

        :param message: Message to add to the annotations.
        :param issues: Issues to attach to the annotation.
        :param suspected_issues: Suspected issues to add to the annotation.
        :param metadata: Extra metadata to add to the issue.
        """
        self._api.annotate_task(
            self.task_id, self.execution, message, issues, suspected_issues, metadata
        )

    def __repr__(self) -> str:
        """
        Get a string representation of Task for debugging purposes.

        :return: String representation of Task.
        """
        return f"Task({self.task_id})"

    class Config:
        """Pydantic configuration for tasks."""

        extra = Extra.allow
