# -*- encoding: utf-8 -*-
"""Performance results representation of evergreen."""
from copy import copy
from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.parser import parse
from pydantic import Field
from pydantic.main import BaseModel


class PerformanceTestResult(BaseModel):
    """Representation of a test result from Evergreen."""

    thread_level: str
    recorded_values: List[float]
    mean_value: float
    measurement: str


class PerformanceTestRun(BaseModel):
    """Representation of a test run from Evergreen."""

    name: str
    workload: Optional[str]
    start: Optional[datetime]
    end: Optional[datetime]
    results: Dict[str, Any]

    @property
    def start_time(self) -> Optional[Any]:
        """Get the start time for the given test run."""
        # Microbenchmarks stores the 'start' and 'end' time of the test in the inner 'results' field
        # while sys-perf stores it in the outer 'results' field.
        # Also, the format of start varies depending on what generated the results.
        if self.start:
            return self.start
        if "start" in self.results:
            return parse(self.results["start"])
        return None

    @property
    def end_time(self) -> Optional[Any]:
        """Get the start time for the given test run."""
        # Microbenchmarks stores the 'start' and 'end' time of the test in the inner 'results' field
        # while sys-perf stores it in the outer 'results' field.
        # Also, the format of end varies depending on what generated the results.
        if self.end:
            return self.end
        if "end" in self.results:
            return parse(self.results["end"])
        return None

    @property
    def test_results(self) -> List[PerformanceTestResult]:
        """Get the performance test results for this run."""
        return [PerformanceTestResult(**item) for item in _format_performance_results(self.results)]


class PerformanceTestBatch(BaseModel):
    """Representation of a batch of tests from Evergreen."""

    start: datetime
    end: Optional[datetime]
    storage_engine: str = Field(alias="storageEngine")
    errors: List[str]
    results: List[PerformanceTestRun]

    def test_runs_matching(self, tests: List[str]) -> List[PerformanceTestRun]:
        """
        Get a list of test run for the given tests.

        :param tests: List of tests to match against.
        :return: List of test runs for the given tests.
        """
        return [item for item in self.results if _is_run_matching(item, tests)]


class PerformanceData(BaseModel):
    """Representation of performance data from Evergreen."""

    name: str
    project_id: str
    task_name: str
    task_id: str
    variant: str
    version_id: str
    build_id: str
    revision: str
    order: int
    tag: str
    create_time: datetime
    data: PerformanceTestBatch
    is_patch: bool

    @property
    def test_batch(self) -> PerformanceTestBatch:
        """Get the performance test batch."""
        return self.data

    def __repr__(self) -> str:
        """
        Get string representation of PerformanceData for debugging purposes.

        :return: String representation of PerformanceData.
        """
        return f"PerformanceData({self.task_id})"


def _format_performance_results(results: Dict) -> List[Dict]:
    """
    Extract and sort the thread level and respective results.

    Data gathered from the raw data file from Evergreen,
    adding max result entries as appropriate.
    See below for an example of the transformation:
    Before:
    {
        "16":{
            "95th_read_latency_us":4560.0,
            "95th_read_latency_us_values":[
                4560.0
            ],
            "99th_read_latency_us":9150.0,
            "99th_read_latency_us_values":[
                9150.0
            ],
            "average_read_latency_us":1300.0,
            "average_read_latency_us_values":[
                1300.0
            ],
            "ops_per_sec":1100.0,
            "ops_per_sec_values":[
                1100.0
            ]
        },
        "8":{
            "95th_read_latency_us":4500.0,
            "95th_read_latency_us_values":[
                4000.0,
                5000.0
            ],
            "99th_read_latency_us":10000.0,
            "99th_read_latency_us_values":[
                10000.0
            ],
            "average_read_latency_us":1300.0,
            "average_read_latency_us_values":[
                1300.0
            ],
            "ops_per_sec":1100.0,
            "ops_per_sec_values":[
                1100.0
            ]
        }
    }
    After:
    [
        {
            'thread_level': '16',
            'mean_value': 4560.0,
            'recorded_values': [
                4560.0
            ],
            'measurement': '95th_read_latency_us'
        },
        {
            'thread_level': '16',
            'mean_value': 9150.0,
            'recorded_values': [
                9150.0
            ],
            'measurement': '99th_read_latency_us'
        },
        {
            'thread_level': '16',
            'mean_value': 1300.0,
            'recorded_values': [
                1300.0
            ],
            'measurement': 'average_read_latency_us'
        },
        {
            'thread_level': '16',
            'mean_value': 1100.0,
            'recorded_values': [
                1100.0
            ],
            'measurement': 'ops_per_sec'
        },
        {
            'thread_level': '8',
            'mean_value': 4500.0,
            'recorded_values': [
                4000.0,
                5000.0
            ],
            'measurement': '95th_read_latency_us'
        },
        {
            'thread_level': '8',
            'mean_value': 10000.0,
            'recorded_values': [
                10000.0
            ],
            'measurement': '99th_read_latency_us'
        },
        {
            'thread_level': '8',
            'mean_value': 1300.0,
            'recorded_values': [
                1300.0
            ],
            'measurement': 'average_read_latency_us'
        },
        {
            'thread_level': '8',
            'mean_value': 1100.0,
            'recorded_values': [
                1100.0
            ],
            'measurement': 'ops_per_sec'
        },
        {
            'thread_level': 'max',
            'mean_value': 4560.0,
            'recorded_values': [
                4560.0
            ],
            'measurement': '95th_read_latency_us'
        },
        {
            'thread_level': 'max',
            'mean_value': 10000.0,
            'recorded_values': [
                10000.0
            ],
            'measurement': '99th_read_latency_us'
        },
        {
            'thread_level': 'max',
            'mean_value': 1300.0,
            'recorded_values': [
                1300.0
            ],
            'measurement': 'average_read_latency_us'
        },
        {
            'thread_level': 'max',
            'mean_value': 1100.0,
            'recorded_values': [
                1100.0
            ],
            'measurement': 'ops_per_sec'
        }
    ]

    :param dict results: All the test results from the raw data file from Evergreen.
    :return: A list of PerformanceTestResults with test results organized by thread level.
    """
    thread_levels = _thread_levels_from_results(results)
    performance_results = []
    maxima: Dict[str, Any] = {}

    for thread_level in thread_levels:
        thread_results = results[thread_level]
        measurement_names = [key for key in thread_results.keys() if "values" not in key]
        for measurement in measurement_names:
            if measurement not in maxima:
                maxima[measurement] = None
            formatted = {
                "thread_level": thread_level,
                "mean_value": thread_results[measurement],
                "recorded_values": thread_results[measurement + "_values"],
                "measurement": measurement,
            }
            performance_results.append(formatted)

            if (
                maxima[measurement] is None
                or maxima[measurement]["mean_value"] < formatted["mean_value"]
            ):
                max_copy = copy(formatted)
                max_copy["thread_level"] = "max"
                maxima[measurement] = max_copy

    return performance_results + list(maxima.values())


def _thread_levels_from_results(results: Dict) -> List[str]:
    """
    Gather the thread levels from the results dict.

    :param results: Dictionary of performance results.
    :return: List of thread levels.
    """
    # Sort as integers
    thread_levels = sorted(int(key) for key in results.keys() if key.isdigit())
    # Cast back to string
    return [str(entry) for entry in thread_levels]


def _is_run_matching(test_run: PerformanceTestRun, tests: List[str]) -> bool:
    """
    Determine if the given test_run.json matches a set of tests.

    :param test_run: test_run.json to check.
    :param tests: List of tests to upload.
    :return: True if the test_run.json contains relevant data.
    """
    if tests is not None and test_run.name not in tests:
        return False

    if test_run.start is None:
        return False

    if all(result.mean_value is None for result in test_run.test_results):
        return False

    return True
