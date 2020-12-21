# -*- encoding: utf-8 -*-
"""Representation of an evergreen build."""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, PrivateAttr

from evergreen.metrics.buildmetrics import BuildMetrics

if TYPE_CHECKING:
    from evergreen.api import EvergreenApi
    from evergreen.task import Task  # noqa: F401
    from evergreen.version import Version

EVG_BUILD_STATUS_FAILED = "failed"
EVG_BUILD_STATUS_SUCCESS = "success"
EVG_BUILD_STATUS_CREATED = "created"

COMPLETED_STATES = {
    EVG_BUILD_STATUS_FAILED,
    EVG_BUILD_STATUS_SUCCESS,
}


class StatusCounts(BaseModel):
    """Representation of Evergreen StatusCounts."""

    succeeded: int
    failed: int
    started: int
    undispatched: int
    inactivate: Optional[int]
    dispatched: int
    timed_out: int


class Build(BaseModel):
    """Representation of an Evergreen build."""

    id: str = Field(alias="_id")
    project_id: str
    create_time: Optional[datetime]
    start_time: Optional[datetime]
    finish_time: Optional[datetime]
    version: str
    branch: str
    git_hash: str
    build_variant: str
    status: str
    activated: bool
    activated_by: str
    activated_time: Optional[datetime]
    order: int
    tasks: List[str]
    time_taken_ms: int
    display_name: str
    predicted_makespan_ms: int
    actual_makespan_ms: int
    origin: str
    status_counts: StatusCounts

    _api: "EvergreenApi" = PrivateAttr()

    def __init__(self, api: "EvergreenApi", **json: Dict[str, Any]) -> None:
        """
        Create an instance of an evergreen task.

        :param json: Json of build object.
        :param api: Evergreen API.
        """
        super().__init__(**json)

        self._api = api

    def get_tasks(self, fetch_all_executions: bool = False) -> List["Task"]:
        """
        Get all tasks for this build.

        :param fetch_all_executions:  fetch all executions for tasks.
        :return: List of all tasks.
        """
        return self._api.tasks_by_build(self.id, fetch_all_executions)

    def is_completed(self) -> bool:
        """
        Determine if this build has completed running tasks.

        :return: True if build has completed running tasks.
        """
        return self.status in COMPLETED_STATES

    def get_metrics(self, task_filter_fn: Callable = None) -> Optional[BuildMetrics]:
        """
        Get metrics for the build.

        Metrics are only available on build that have finished running..

        :param task_filter_fn: function to filter tasks included for metrics, should accept a task
                               argument.
        :return: Metrics for the build.
        """
        if self.status != EVG_BUILD_STATUS_CREATED:
            return BuildMetrics(self).calculate(task_filter_fn)
        return None

    def get_version(self) -> "Version":
        """
        Get the version this build is a part of.

        :return: Version that this build is a part of.
        """
        return self._api.version_by_id(self.version)

    def __repr__(self) -> str:
        """
        Get a string representation of Task for debugging purposes.

        :return: String representation of Task.
        """
        return f"Build({self.id})"
