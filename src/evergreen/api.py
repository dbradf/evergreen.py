# -*- encoding: utf-8 -*-
"""API for interacting with evergreen."""
import json
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from json.decoder import JSONDecodeError
from time import time
from typing import Any, Callable, Dict, Generator, Iterable, Iterator, List, Optional, Union, cast

import requests
import structlog
from structlog.stdlib import LoggerFactory
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from evergreen.alias import VariantAlias
from evergreen.api_requests import IssueLinkRequest
from evergreen.build import Build
from evergreen.commitqueue import CommitQueue
from evergreen.config import (
    DEFAULT_API_SERVER,
    DEFAULT_NETWORK_TIMEOUT_SEC,
    EvgAuth,
    get_auth_from_config,
    read_evergreen_config,
    read_evergreen_from_file,
)
from evergreen.distro import Distro
from evergreen.host import Host
from evergreen.manifest import Manifest
from evergreen.patch import Patch
from evergreen.performance_results import PerformanceData
from evergreen.project import Project
from evergreen.recent_versions import RecentVersions
from evergreen.stats import TaskStats, TestStats
from evergreen.task import Task
from evergreen.task_annotations import TaskAnnotation
from evergreen.task_reliability import TaskReliability
from evergreen.tst import Tst
from evergreen.util import evergreen_input_to_output, format_evergreen_date, iterate_by_time_window
from evergreen.version import Requester, Version

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse  # type: ignore


structlog.configure(logger_factory=LoggerFactory())
LOGGER = structlog.getLogger(__name__)

CACHE_SIZE = 5000
DEFAULT_LIMIT = 100
MAX_RETRIES = 3
START_WAIT_TIME_SEC = 2
MAX_WAIT_TIME_SEC = 5


class EvergreenApi(object):
    """Base methods for building API objects."""

    def __init__(
        self,
        api_server: str = DEFAULT_API_SERVER,
        auth: Optional[EvgAuth] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        """
        Create a _BaseEvergreenApi object.

        :param api_server: URI of Evergreen API server.
        :param auth: EvgAuth object with auth information.
        :param timeout: Time (in sec) to wait before considering a call as failed.
        :param session: Session to use for requests.
        """
        self._timeout = timeout
        self._api_server = api_server
        self._auth = auth
        self._session = session

    @contextmanager
    def with_session(self) -> Generator["EvergreenApi", None, None]:
        """Yield an instance of the API client with a shared session."""
        session = self._create_session()
        evg_api = EvergreenApi(self._api_server, self._auth, self._timeout, session)
        yield evg_api

    @property
    def session(self) -> requests.Session:
        """
        Get the shared session if it exists, else create a new session.

        :return: Session to query the API with.
        """
        if self._session:
            return self._session

        return self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a new session to query the API with."""
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter()
        session.mount(f"{urlparse(self._api_server).scheme}://", adapter)
        auth = self._auth
        if auth:
            session.headers.update({"Api-User": auth.username, "Api-Key": auth.api_key})
        return session

    def _create_url(self, endpoint: str) -> str:
        """
        Format a call to a v2 REST API endpoint.

        :param endpoint: endpoint to call.
        :return: Full url to get endpoint.
        """
        return f"{self._api_server}/rest/v2{endpoint}"

    def _create_plugin_url(self, endpoint: str) -> str:
        """
        Format the a call to a plugin endpoint.

        :param endpoint: endpoint to call.
        :return: Full url to get endpoint.
        """
        return f"{self._api_server}/plugin/json{endpoint}"

    @staticmethod
    def _log_api_call_time(response: requests.Response, start_time: float) -> None:
        """
        Log how long the api call took.

        :param response: Response from API.
        :param start_time: Time the response was started.
        """
        duration = round(time() - start_time, 2)
        if duration > 10:
            LOGGER.info("Request completed.", url=response.request.url, duration=duration)
        else:
            LOGGER.debug("Request completed.", url=response.request.url, duration=duration)

    def _call_api(
        self,
        url: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        data: Optional[str] = None,
    ) -> requests.Response:
        """
        Make a call to the evergreen api.

        :param url: Url of call to make.
        :param params: parameters to pass to api.
        :return: response from api server.
        """
        start_time = time()
        response = self.session.request(
            url=url, params=params, timeout=self._timeout, data=data, method=method
        )

        self._log_api_call_time(response, start_time)

        self._raise_for_status(response)
        return response

    def _stream_api(self, url: str, params: Dict = None) -> Iterable:
        """
        Make a streaming call to an api.

        :param url: url to call
        :param params: url parameters
        :return: Iterable over the lines of the returned content.
        """
        start_time = time()
        with self.session.get(url=url, params=params, stream=True, timeout=self._timeout) as res:
            self._log_api_call_time(res, start_time)
            self._raise_for_status(res)

            for line in res.iter_lines(decode_unicode=True):
                yield line

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        """
        Raise an exception with the evergreen message if it exists.

        :param response: response from evergreen api.
        """
        try:
            json_data = response.json()
            if response.status_code >= 400 and "error" in json_data:
                raise requests.exceptions.HTTPError(json_data["error"], response=response)
        except JSONDecodeError:
            pass

        response.raise_for_status()

    def _paginate(self, url: str, params: Dict = None) -> List[Dict[str, Any]]:
        """
        Paginate until all results are returned and return a list of all JSON results.

        :param url: url to make request to.
        :param params: parameters to pass to request.
        :return: json list of all results.
        """
        response = self._call_api(url, params)
        json_data = response.json()
        while "next" in response.links:
            if params and "limit" in params and len(json_data) >= params["limit"]:
                break
            response = self._call_api(response.links["next"]["url"])
            if response.json():
                json_data.extend(response.json())

        return json_data

    def _lazy_paginate(self, url: str, params: Dict = None) -> Iterable:
        """
        Lazy paginate, the results are returned lazily.

        :param url: URL to query.
        :param params: Params to pass to url.
        :return: A generator to get results from.
        """
        if not params:
            params = {
                "limit": DEFAULT_LIMIT,
            }

        next_url = url
        while True:
            response = self._call_api(next_url, params)
            json_response = response.json()
            if not json_response:
                break
            for result in json_response:
                yield result
            if "next" not in response.links:
                break

            next_url = response.links["next"]["url"]

    def _lazy_paginate_by_date(self, url: str, params: Dict = None) -> Iterable:
        """
        Paginate based on date, the results are returned lazily.

        :param url: URL to query.
        :param params: Params to pass to url.
        :return: A generator to get results from.
        """
        if not params:
            params = {
                "limit": DEFAULT_LIMIT,
            }

        while True:
            data = self._call_api(url, params).json()
            if not data:
                break
            for result in data:
                yield result
            params["start_at"] = evergreen_input_to_output(data[-1]["create_time"])

    def all_distros(self) -> List[Distro]:
        """
        Get all distros in evergreen.

        :return: List of all distros in evergreen.
        """
        url = self._create_url("/distros")
        distro_list = self._paginate(url)
        return [Distro(**distro) for distro in distro_list]

    def all_hosts(self, status: Optional[str] = None) -> List[Host]:
        """
        Get all hosts in evergreen.

        :param status: Only return hosts with specified status.
        :return: List of all hosts in evergreen.
        """
        params = {}
        if status:
            params["status"] = status

        url = self._create_url("/hosts")
        host_list = self._paginate(url, params)
        return [Host(self, **host) for host in host_list]

    def configure_task(
        self, task_id: str, activated: Optional[bool] = None, priority: Optional[int] = None
    ) -> None:
        """
        Update a task.

        :param task_id: Id of the task to update
        :param activated: If specified, will update the task to specified value True or False
        :param priority: If specified, will update the task's priority to specified number
        """
        url = self._create_url(f"/tasks/{task_id}")
        data: Dict[str, Union[bool, int]] = {}
        if activated:
            data["activated"] = activated
        if priority:
            data["priority"] = priority
        self._call_api(url, data=json.dumps(data), method="PATCH")

    def restart_task(self, task_id: str) -> None:
        """
        Restart a task.

        :param task_id: Id of the task to restart
        """
        url = self._create_url(f"/tasks/{task_id}/restart")
        self._call_api(url, method="POST")

    def abort_task(self, task_id: str) -> None:
        """
        Abort a task.

        :param task_id: Id of the task to abort
        """
        url = self._create_url(f"/tasks/{task_id}/abort")
        self._call_api(url, method="POST")

    def all_projects(self, project_filter_fn: Optional[Callable] = None) -> List[Project]:
        """
        Get all projects in evergreen.

        :param project_filter_fn: function to filter projects, should accept a project_id argument.
        :return: List of all projects in evergreen.
        """
        url = self._create_url("/projects")
        project_list = self._paginate(url)
        projects = [Project(self, **project) for project in project_list]
        if project_filter_fn:
            return [project for project in projects if project_filter_fn(project)]
        return projects

    def project_by_id(self, project_id: str) -> Project:
        """
        Get a project by project_id.

        :param project_id: Id of project to query.
        :return: Project specified.
        """
        url = self._create_url(f"/projects/{project_id}")
        return Project(self, **self._call_api(url).json())

    def recent_versions_by_project(
        self, project_id: str, params: Optional[Dict] = None
    ) -> RecentVersions:
        """
        Get recent versions created in specified project.

        :param project_id: Id of project to query.
        :param params: parameters to pass to endpoint.
        :return: List of recent versions.
        """
        url = self._create_url(f"/projects/{project_id}/recent_versions")
        resp = self._call_api(url, params)
        return RecentVersions(**resp.json())

    def alias_for_version(
        self, version_id: str, alias: str, include_deps: bool = False
    ) -> List[VariantAlias]:
        """
        Get the tasks and variants that an alias would select for an evergreen version.

        :param version_id: Evergreen version to query against.
        :param alias: Alias to query.
        :param include_deps: If true, will also select tasks that are dependencies.
        :return: List of Variant alias details.
        """
        params = {"version": version_id, "alias": alias, "include_deps": include_deps}
        url = self._create_url("/projects/test_alias")
        variant_alias_list: List[Dict[str, Any]] = self._paginate(url, params)
        return [VariantAlias(**variant_alias) for variant_alias in variant_alias_list]

    def versions_by_project(
        self, project_id: str, requester: Requester = Requester.GITTER_REQUEST
    ) -> Iterator[Version]:
        """
        Get the versions created in the specified project.

        :param project_id: Id of project to query.
        :param requester: Type of versions to query.
        :return: Generator of versions.
        """
        url = self._create_url(f"/projects/{project_id}/versions")
        params = {"requester": requester.name.lower()}
        version_list = self._lazy_paginate(url, params)
        return (Version(self, **version) for version in version_list)

    def versions_by_project_time_window(
        self,
        project_id: str,
        before: datetime,
        after: datetime,
        requester: Requester = Requester.GITTER_REQUEST,
        time_attr: str = "create_time",
    ) -> Iterable[Version]:
        """
        Get an iterator over the patches for the given time window.

        :param project_id: Id of project to query.
        :param requester: Type of version to query
        :param before: Return versions earlier than this timestamp.
        :param after: Return versions later than this timestamp.
        :param time_attr: Attributes to use to window timestamps.
        :return: Iterator for the given time window.
        """
        return iterate_by_time_window(
            self.versions_by_project(project_id, requester), before, after, time_attr
        )

    def patches_by_project(self, project_id: str, params: Dict = None) -> Iterable[Patch]:
        """
        Get a list of patches for the specified project.

        :param project_id: Id of project to query.
        :param params: parameters to pass to endpoint.
        :return: List of recent patches.
        """
        url = self._create_url(f"/projects/{project_id}/patches")
        patches = self._lazy_paginate_by_date(url, params)
        return (Patch(self, **patch) for patch in patches)

    def configure_patch(
        self,
        patch_id: str,
        variants: List[Dict[str, Union[str, List[str]]]],
        description: Optional[str] = None,
    ) -> None:
        """
        Update a patch.

        :param patch_id: Id of the patch to update
        :param variants: list of objects with keys "id" who's value is the variant ID, and key "tasks"
            with value of a list of task names to configure for specified variant. See the documentation for more details
            https://github.com/evergreen-ci/evergreen/wiki/REST-V2-Usage#configureschedule-a-patch
        :param description: If specified, will update the patch's description with the string provided
        """
        url = self._create_url(f"/patches/{patch_id}/configure")
        data: Dict[str, Union[List, str]] = {}
        if variants:
            data["variants"] = variants
        if description:
            data["description"] = description

        self._call_api(url, data=json.dumps(data), method="POST")

    def patches_by_project_time_window(
        self,
        project_id: str,
        before: datetime,
        after: datetime,
        params: Dict = None,
        time_attr: str = "create_time",
    ) -> Iterable[Patch]:
        """
        Get an iterator over the patches for the given time window.

        :param project_id: Id of project to query.
        :param params: Parameters to pass to endpoint.
        :param before: Return patches earlier than this timestamp
        :param after: Return patches later than this timestamp.
        :param time_attr: Attributes to use to window timestamps.
        :return: Iterator for the given time window.
        """
        return iterate_by_time_window(
            self.patches_by_project(project_id, params), before, after, time_attr
        )

    def patches_by_user(
        self, user_id: str, start_at: Optional[datetime] = None, limit: Optional[int] = None
    ) -> Iterable[Patch]:
        """
        Get an iterable of recent patches by the given user.

        :param user_id: Id of user to query.
        :param start_at: If specified, query starting at the given date.
        :param limit: If specified, limit the output per page.
        """
        params: Dict[str, Any] = {}
        if start_at:
            params["start_at"] = start_at
        if limit:
            params["limit"] = limit
        url = self._create_url(f"/users/{user_id}/patches")
        return (Patch(self, **patch) for patch in self._lazy_paginate(url, params))

    def commit_queue_for_project(self, project_id: str) -> CommitQueue:
        """
        Get the current commit queue for the specified project.

        :param project_id: Id of project to query.
        :return: Current commit queue for project.
        """
        url = self._create_url(f"/commit_queue/{project_id}")
        return CommitQueue(**self._call_api(url).json())

    def test_stats_by_project(
        self,
        project_id: str,
        after_date: datetime,
        before_date: datetime,
        group_num_days: Optional[int] = None,
        requesters: Optional[Requester] = None,
        tests: Optional[List[str]] = None,
        tasks: Optional[List[str]] = None,
        variants: Optional[List[str]] = None,
        distros: Optional[List[str]] = None,
        group_by: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> List[TestStats]:
        """
        Get a patch by patch id.

        :param project_id: Id of patch to query for.
        :param after_date: Collect stats after this date.
        :param before_date: Collect stats before this date.
        :param group_num_days: Aggregate statistics to this size.
        :param requesters: Filter by requestors (mainline, patch, trigger, or adhoc).
        :param tests: Only include specified tests.
        :param tasks: Only include specified tasks.
        :param variants: Only include specified variants.
        :param distros: Only include specified distros.
        :param group_by: How to group results (test_task_variant, test_task, or test)
        :param sort: How to sort results (earliest or latest).
        :return: Patch queried for.
        """
        params: Dict[str, Any] = {
            "after_date": format_evergreen_date(after_date),
            "before_date": format_evergreen_date(before_date),
        }
        if group_num_days:
            params["group_num_days"] = group_num_days
        if requesters:
            params["requesters"] = requesters
        if tests:
            params["tests"] = tests
        if tasks:
            params["tasks"] = tasks
        if variants:
            params["variants"] = variants
        if distros:
            params["distros"] = distros
        if group_by:
            params["group_by"] = group_by
        if sort:
            params["sort"] = sort
        url = self._create_url(f"/projects/{project_id}/test_stats")
        test_stats_list = self._paginate(url, params)
        return [TestStats(**test_stat) for test_stat in test_stats_list]

    def tasks_by_project(self, project_id: str, statuses: Optional[List[str]] = None) -> List[Task]:
        """
        Get all the tasks for a project.

        :param project_id: The project's id.
        :param statuses: the types of statuses to get tasks for.
        :return: The list of matching tasks.
        """
        url = self._create_url(f"/projects/{project_id}/versions/tasks")
        params = {"status": statuses} if statuses else None
        return [Task(self, **json) for json in self._paginate(url, params)]

    def tasks_by_project_and_commit(
        self, project_id: str, commit_hash: str, params: Optional[Dict] = None
    ) -> List[Task]:
        """
        Get all the tasks for a revision in specified project.

        :param project_id: Project id associated with the revision
        :param commit_hash: Commit to get tasks for
        :param params: Dictionary of parameters to pass to query.
        :return: The list of matching tasks.
        """
        url = self._create_url(f"/projects/{project_id}/revisions/{commit_hash}/tasks")
        return [Task(self, **json) for json in self._call_api(url, params).json()]

    def task_stats_by_project(
        self,
        project_id: str,
        after_date: datetime,
        before_date: datetime,
        group_num_days: Optional[int] = None,
        requesters: Optional[Requester] = None,
        tasks: Optional[List[str]] = None,
        variants: Optional[List[str]] = None,
        distros: Optional[List[str]] = None,
        group_by: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> List[TaskStats]:
        """
        Get task stats by project id.

        :param project_id: Id of patch to query for.
        :param after_date: Collect stats after this date.
        :param before_date: Collect stats before this date.
        :param group_num_days: Aggregate statistics to this size.
        :param requesters: Filter by requestors (mainline, patch, trigger, or adhoc).
        :param tasks: Only include specified tasks.
        :param variants: Only include specified variants.
        :param distros: Only include specified distros.
        :param group_by: How to group results (test_task_variant, test_task, or test)
        :param sort: How to sort results (earliest or latest).
        :return: Patch queried for.
        """
        params: Dict[str, Any] = {
            "after_date": format_evergreen_date(after_date),
            "before_date": format_evergreen_date(before_date),
        }
        if group_num_days:
            params["group_num_days"] = group_num_days
        if requesters:
            params["requesters"] = requesters.stats_value()
        if tasks:
            params["tasks"] = tasks
        if variants:
            params["variants"] = variants
        if distros:
            params["distros"] = distros
        if group_by:
            params["group_by"] = group_by
        if sort:
            params["sort"] = sort
        url = self._create_url(f"/projects/{project_id}/task_stats")
        task_stats_list = self._paginate(url, params)
        return [TaskStats(**task_stat) for task_stat in task_stats_list]

    def task_reliability_by_project(
        self,
        project_id: str,
        after_date: Optional[datetime] = None,
        before_date: Optional[datetime] = None,
        group_num_days: Optional[int] = None,
        requesters: Optional[Requester] = None,
        tasks: Optional[List[str]] = None,
        variants: Optional[List[str]] = None,
        distros: Optional[List[str]] = None,
        group_by: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> List[TaskReliability]:
        """
        Get task reliability scores.

        :param project_id: Id of patch to query for.
        :param after_date: Collect stats after this date.
        :param before_date: Collect stats before this date, defaults to nothing.
        :param group_num_days: Aggregate statistics to this size.
        :param requesters: Filter by requesters (mainline, patch, trigger, or adhoc).
        :param tasks: Only include specified tasks.
        :param variants: Only include specified variants.
        :param distros: Only include specified distros.
        :param group_by: How to group results (test_task_variant, test_task, or test)
        :param sort: How to sort results (earliest or latest).
        :return: Patch queried for.
        """
        params: Dict[str, Any] = {}
        if after_date:
            params["after_date"] = format_evergreen_date(after_date)
        if before_date:
            params["before_date"] = format_evergreen_date(before_date)
        if group_num_days:
            params["group_num_days"] = group_num_days
        if requesters:
            params["requesters"] = requesters.stats_value()
        if tasks:
            params["tasks"] = tasks
        if variants:
            params["variants"] = variants
        if distros:
            params["distros"] = distros
        if group_by:
            params["group_by"] = group_by
        if sort:
            params["sort"] = sort

        url = self._create_url(f"/projects/{project_id}/task_reliability")
        task_reliability_scores = self._paginate(url, params)
        return [TaskReliability(**task_reliability) for task_reliability in task_reliability_scores]

    def build_by_id(self, build_id: str) -> Build:
        """
        Get a build by id.

        :param build_id: build id to query.
        :return: Build queried for.
        """
        url = self._create_url(f"/builds/{build_id}")
        return Build(self, **self._call_api(url).json())

    def tasks_by_build(
        self, build_id: str, fetch_all_executions: Optional[bool] = None
    ) -> List[Task]:
        """
        Get all tasks for a given build.

        :param build_id: build_id to query.
        :param fetch_all_executions: Fetch all executions for a given task.
        :return: List of tasks for the specified build.
        """
        params = {}
        if fetch_all_executions:
            params["fetch_all_executions"] = 1

        url = self._create_url(f"/builds/{build_id}/tasks")
        task_list = self._paginate(url, params)
        return [Task(self, **task) for task in task_list]

    def version_by_id(self, version_id: str) -> Version:
        """
        Get version by version id.

        :param version_id: Id of version to query.
        :return: Version queried for.
        """
        url = self._create_url(f"/versions/{version_id}")
        return Version(self, **self._call_api(url).json())

    def builds_by_version(self, version_id: str, params: Optional[Dict] = None) -> List[Build]:
        """
        Get all builds for a given Evergreen version_id.

        :param version_id: Version Id to query for.
        :param params: Dictionary of parameters to pass to query.
        :return: List of builds for the specified version.
        """
        url = self._create_url(f"/versions/{version_id}/builds")
        build_list = self._paginate(url, params)
        return [Build(self, **build) for build in build_list]

    def patch_by_id(self, patch_id: str, params: Dict = None) -> Patch:
        """
        Get a patch by patch id.

        :param patch_id: Id of patch to query for.
        :param params: Parameters to pass to endpoint.
        :return: Patch queried for.
        """
        url = self._create_url(f"/patches/{patch_id}")
        return Patch(self, **self._call_api(url, params).json())

    def task_by_id(self, task_id: str, fetch_all_executions: Optional[bool] = None) -> Task:
        """
        Get a task by task_id.

        :param task_id: Id of task to query for.
        :param fetch_all_executions: Should all executions of the task be fetched.
        :return: Task queried for.
        """
        params = None
        if fetch_all_executions:
            params = {"fetch_all_executions": fetch_all_executions}
        url = self._create_url(f"/tasks/{task_id}")
        return Task(self, **self._call_api(url, params).json())

    def tests_by_task(
        self, task_id: str, status: Optional[str] = None, execution: Optional[int] = None
    ) -> List[Tst]:
        """
        Get all tests for a given task.

        :param task_id: Id of task to query for.
        :param status: Limit results to given status.
        :param execution: Retrieve the specified task execution (defaults to 0).
        :return: List of tests for the specified task.
        """
        params: Dict[str, Any] = {}
        if status:
            params["status"] = status
        if execution:
            params["execution"] = execution
        url = self._create_url(f"/tasks/{task_id}/tests")
        return [Tst(self, **test) for test in self._paginate(url, params)]

    def single_test_by_task_and_test_file(self, task_id: str, test_file: str) -> Tst:
        """
        Get a test for a given task.

        :param task_id: Id of task to query for.
        :param test_file: the name of the test_file of the test.
        :return: the test for the specified task.
        """
        url = self._create_url(f"/tasks/{task_id}/tests")
        return Tst(self, **self._call_api(url, params={"test_name": test_file}).json())

    def manifest_for_task(self, task_id: str) -> Manifest:
        """
        Get the manifest for the given task.

        :param task_id: Task Id fo query.
        :return: Manifest for the given task.
        """
        url = self._create_url(f"/tasks/{task_id}/manifest")
        return Manifest(**self._call_api(url).json())

    def get_task_annotation(
        self,
        task_id: str,
        execution: Optional[int] = None,
        fetch_all_executions: Optional[bool] = None,
    ) -> List[TaskAnnotation]:
        """
        Get the task annotations for the given task.

        :param task_id: Id of task to query.
        :param execution: Execution number of task to query (defaults to latest).
        :param fetch_all_executions: Get annotations for all executions of this task.
        :return: The task annotations for the given task, if any exists.
        """
        if execution is not None and fetch_all_executions is not None:
            raise ValueError("'execution' and 'fetch_all_executions' are mutually-exclusive")

        url = self._create_url(f"/tasks/{task_id}/annotations")
        params: Dict[str, Any] = {}
        if execution:
            params["execution"] = execution
        if fetch_all_executions:
            params["fetch_all_executions"] = fetch_all_executions

        response = self._call_api(url, params)
        if response.text.strip() == "null":
            return []
        return [TaskAnnotation(**annotation) for annotation in response.json()]

    def annotate_task(
        self,
        task_id: str,
        execution: Optional[int] = None,
        message: Optional[str] = None,
        issues: Optional[List[IssueLinkRequest]] = None,
        suspected_issues: Optional[List[IssueLinkRequest]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Annotate the specified task.

        :param task_id: ID of task to annotate.
        :param execution: Execution number of task to annotate (default to latest).
        :param message: Message to add to the annotations.
        :param issues: Issues to attach to the annotation.
        :param suspected_issues: Suspected issues to add to the annotation.
        :param metadata: Extra metadata to add to the issue.
        """
        url = self._create_url(f"/tasks/{task_id}/annotation")
        request: Dict[str, Any] = {
            "task_id": task_id,
        }

        if execution:
            request["task_execution"] = execution

        if message:
            request["note"] = {"message": message}

        if issues:
            request["issues"] = [issue.as_dict() for issue in issues]

        if suspected_issues:
            request["suspected_issues"] = [issue.as_dict() for issue in suspected_issues]

        if metadata:
            request["metadata"] = metadata

        self._call_api(url, method="PUT", data=json.dumps(request))

    def performance_results_by_task(self, task_id: str) -> PerformanceData:
        """
        Get the 'perf.json' performance results for a given task_id.

        :param task_id: Id of task to query for.
        :return: Contents of 'perf.json'
        """
        url = self._create_plugin_url(f"/task/{task_id}/perf")
        return PerformanceData(**self._call_api(url).json())

    def performance_results_by_task_name(
        self, task_id: str, task_name: str
    ) -> List[PerformanceData]:
        """
        Get the 'perf.json' performance results for a given task_id and task_name.

        :param task_id: Id of task to query for.
        :param task_name: Name of task to query for.
        :return: Contents of 'perf.json'
        """
        url = f"{self._api_server}/api/2/task/{task_id}/json/history/{task_name}/perf"
        return [PerformanceData(**result) for result in self._paginate(url)]

    def json_by_task(self, task_id: str, json_key: str) -> Dict[str, Any]:
        """
        Get the json reported for task {task_id} using the key {json_key}.

        :param task_id: Id of task to query for.
        :param json_key: The key that json was published under, e.g. "perf".
        :return: The json published for that task.
        """
        url = self._create_plugin_url(f"/task/{task_id}/{json_key}")
        return cast(Dict[str, Any], self._paginate(url))

    def json_history_for_task(
        self, task_id: str, task_name: str, json_key: str
    ) -> List[Dict[str, Any]]:
        """
        Get the history of json reported for task {task_id} using the key {json_key}.

        :param task_id: Id of task to query for.
        :param task_name: Name of task to query for.
        :param json_key: The key that json was published under, e.g. "perf".
        :return: A chronological list of json published for that task.
        """
        url = f"{self._api_server}/api/2/task/{task_id}/json/history/{task_name}/{json_key}"
        return cast(List[Dict[str, Any]], self._paginate(url))

    def _create_old_url(self, endpoint: str) -> str:
        """
        Build a url for an pre-v2 endpoint.

        :param endpoint: endpoint to build url for.
        :return: An string pointing to the given endpoint.
        """
        return f"{self._api_server}/{endpoint}"

    def manifest(self, project_id: str, revision: str) -> Manifest:
        """
        Get the manifest for the given revision.

        :param project_id: Project the revision belongs to.
        :param revision: Revision to get manifest of.
        :return: Manifest of the given revision of the given project.
        """
        url = self._create_old_url(f"plugin/manifest/get/{project_id}/{revision}")
        return Manifest(**self._call_api(url).json())

    def retrieve_task_log(self, log_url: str, raw: bool = False) -> str:
        """
        Get the request log file from a task.

        :param log_url: URL of log to retrieve.
        :param raw: Retrieve the raw version of the log
        :return: Contents of specified log file.
        """
        params = {}
        if raw:
            params["text"] = "true"
        return self._call_api(log_url, params=params).text

    def stream_log(self, log_url: str) -> Iterable:
        """
        Stream the given log url as a python generator.

        :param log_url: URL of log file to stream.
        :return: Iterable for contents of log_url.
        """
        params = {"text": "true"}
        return self._stream_api(log_url, params)

    @classmethod
    def get_api(
        cls,
        auth: Optional[EvgAuth] = None,
        use_config_file: bool = False,
        config_file: Optional[str] = None,
        timeout: Optional[int] = DEFAULT_NETWORK_TIMEOUT_SEC,
    ) -> "EvergreenApi":
        """
        Get an evergreen api instance based on config file settings.

        :param auth: EvgAuth with authentication to use.
        :param use_config_file: attempt to read auth from default config file.
        :param config_file: config file with authentication information.
        :param timeout: Network timeout.
        :return: EvergreenApi instance.
        """
        kwargs = EvergreenApi._setup_kwargs(
            timeout=timeout, auth=auth, use_config_file=use_config_file, config_file=config_file
        )
        return cls(**kwargs)

    @staticmethod
    def _setup_kwargs(
        auth: Optional[EvgAuth] = None,
        use_config_file: bool = False,
        config_file: Optional[str] = None,
        timeout: Optional[int] = DEFAULT_NETWORK_TIMEOUT_SEC,
    ) -> Dict:
        kwargs = {"auth": auth, "timeout": timeout}
        config = None
        if use_config_file:
            config = read_evergreen_config()
        elif config_file is not None:
            config = read_evergreen_from_file(config_file)

        if config is not None:
            auth = get_auth_from_config(config)
            if auth:
                kwargs["auth"] = auth

            # If there is a value for api_server_host, then use it.
            if "evergreen" in config and config["evergreen"].get("api_server_host", None):
                kwargs["api_server"] = config["evergreen"]["api_server_host"]

        return kwargs


class CachedEvergreenApi(EvergreenApi):
    """Access to the Evergreen API server that caches certain calls."""

    def __init__(
        self,
        api_server: str = DEFAULT_API_SERVER,
        auth: Optional[EvgAuth] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """Create an Evergreen Api object."""
        super(CachedEvergreenApi, self).__init__(api_server, auth, timeout)

    @lru_cache(maxsize=CACHE_SIZE)
    def build_by_id(self, build_id: str) -> Build:
        """
        Get a build by id.

        :param build_id: build id to query.
        :return: Build queried for.
        """
        return super(CachedEvergreenApi, self).build_by_id(build_id)

    @lru_cache(maxsize=CACHE_SIZE)
    def version_by_id(self, version_id: str) -> Version:
        """
        Get version by version id.

        :param version_id: Id of version to query.
        :return: Version queried for.
        """
        return super(CachedEvergreenApi, self).version_by_id(version_id)

    def clear_caches(self) -> None:
        """Clear the cache."""
        cached_functions = [
            self.build_by_id,
            self.version_by_id,
        ]
        for fn in cached_functions:
            fn.cache_clear()  # type: ignore[attr-defined]


class RetryingEvergreenApi(EvergreenApi):
    """An Evergreen Api that retries failed calls."""

    def __init__(
        self,
        api_server: str = DEFAULT_API_SERVER,
        auth: Optional[EvgAuth] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """Create an Evergreen Api object."""
        super(RetryingEvergreenApi, self).__init__(api_server, auth, timeout)

    @retry(
        retry=retry_if_exception_type(  # type: ignore[no-untyped-call]
            (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
            )
        ),
        stop=stop_after_attempt(MAX_RETRIES),  # type: ignore[no-untyped-call]
        wait=wait_exponential(multiplier=1, min=START_WAIT_TIME_SEC, max=MAX_WAIT_TIME_SEC),  # type: ignore[no-untyped-call]
        reraise=True,
    )
    def _call_api(
        self,
        url: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        data: Optional[str] = None,
    ) -> requests.Response:
        """
        Call into the evergreen api.

        :param url: Url to call.
        :param params: Parameters to pass to api.
        :return: Result from calling API.
        """
        return super()._call_api(url, params, method, data)
