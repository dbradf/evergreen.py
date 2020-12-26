# -*- encoding: utf-8 -*-
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from evergreen.api_models.task import _EVG_DATE_FIELDS_IN_TASK, StatusScore, Task


def create_mock_task(task_data):
    return Task(MagicMock(), **task_data)


class TestTask(object):
    def test_time_fields_return_time_objects(self, sample_task):
        task = create_mock_task(sample_task)
        for date_field in _EVG_DATE_FIELDS_IN_TASK:
            assert isinstance(getattr(task, date_field), datetime)

    def test_getting_attributes(self, sample_task):
        task = create_mock_task(sample_task)
        assert sample_task["task_id"] == task.task_id
        with pytest.raises(AttributeError):
            task.not_really_an_attribute

    def test_status_attributes(self, sample_task):
        task = create_mock_task(sample_task)
        assert task.is_success()
        assert not task.is_system_failure()
        assert not task.is_timeout()

    def test_bad_status_attributes(self, sample_task):
        sample_task["status_details"]["type"] = "system"
        sample_task["status"] = "failed"
        sample_task["status_details"]["timed_out"] = True
        task = create_mock_task(sample_task)
        assert not task.is_success()
        assert task.is_system_failure()
        assert task.is_timeout()

    def test_wait_time(self, sample_task):
        task = create_mock_task(sample_task)
        assert timedelta(minutes=30) == task.wait_time()

    def test_missing_wait_time(self, sample_task):
        sample_task["start_time"] = None
        task = create_mock_task(sample_task)
        assert not task.wait_time()

    def test_wait_time_once_unblocked(self, sample_task):
        task = create_mock_task(sample_task)
        assert timedelta(minutes=20) == task.wait_time_once_unblocked()

    def test_missing_wait_time_once_unblocked(self, sample_task):
        sample_task["scheduled_time"] = None
        task = create_mock_task(sample_task)
        assert not task.wait_time_once_unblocked()

    def test_get_execution(self, sample_task):
        task = create_mock_task(sample_task)
        execution1 = task.get_execution(1)
        assert execution1.display_name == "aggregation_auth"

        execution0 = task.get_execution(0)
        assert execution0.display_name == "sharding_auth_gen"

        assert not task.get_execution(999)

    def test_get_execution_or_self(self, sample_task):
        task = create_mock_task(sample_task)
        execution = task.get_execution_or_self(0)

        assert execution.display_name == "sharding_auth_gen"

    def test_get_execution_or_self_with_no_execution(self, sample_task):
        task = create_mock_task(sample_task)
        execution = task.get_execution_or_self(999)

        assert execution == task

    def test_artifacts(self, sample_task):
        task = create_mock_task(sample_task)
        assert len(task.artifacts) == len(sample_task["artifacts"])
        assert task.artifacts[0].name == sample_task["artifacts"][0]["name"]

    def test_no_artifacts(self, sample_task):
        sample_task["artifacts"] = None
        task = create_mock_task(sample_task)
        assert task.artifacts is None

    def test_retrieve_log(self, sample_task):
        task = create_mock_task(sample_task)
        log = task.retrieve_log("task_log")
        assert log == task._api.retrieve_task_log.return_value

    def test_retrieve_log_with_raw(self, sample_task):
        task = create_mock_task(sample_task)
        log = task.retrieve_log("task_log", raw=True)
        assert log == task._api.retrieve_task_log.return_value
        task._api.retrieve_task_log.assert_called_with(sample_task["logs"]["task_log"], True)

    def test_stream_log(self, sample_task):
        task = create_mock_task(sample_task)
        log = task.stream_log("task_log")
        assert log == task._api.stream_log.return_value

    def test_successful_task_is_not_undispatched(self, sample_task):
        sample_task["status"] = "success"
        task = create_mock_task(sample_task)

        assert not task.is_undispatched()

    def test_undispatched_task_is_undispatched(self, sample_task):
        sample_task["status"] = "undispatched"
        task = create_mock_task(sample_task)

        assert task.is_undispatched()

    def test_active_task(self, sample_task):
        sample_task["finish_time"] = None
        task = create_mock_task(sample_task)

        assert task.is_active()

    def test_inactive_task_not_scheduled(self, sample_task):
        sample_task["finish_time"] = None
        sample_task["scheduled_time"] = None
        task = create_mock_task(sample_task)

        assert not task.is_active()

    def test_inactive_task_finished(self, sample_task):
        task = create_mock_task(sample_task)

        assert not task.is_active()

    @pytest.mark.parametrize(
        "execution,expected",
        [(None, 1), (0, 0)],
    )
    def test_get_tests(self, sample_task, execution, expected):
        task = create_mock_task(sample_task)

        if execution is None:
            tests = task.get_tests()
        else:
            tests = task.get_tests(execution=execution)

        task._api.tests_by_task.assert_called_once()

        kwargs = task._api.tests_by_task.call_args[1]
        assert "execution" in kwargs and kwargs["execution"] == expected
        assert tests == task._api.tests_by_task.return_value

    @pytest.mark.parametrize(
        "status_string,status_score",
        [
            ("success", StatusScore.SUCCESS),
            ("failure", StatusScore.FAILURE),
            ("undispatched", StatusScore.UNDISPATCHED),
        ],
    )
    def test_no_details_task_is_scored_correctly(self, sample_task, status_string, status_score):
        sample_task["status"] = status_string
        task = create_mock_task(sample_task)

        assert task.get_status_score() == status_score

    @pytest.mark.parametrize(
        "status_string,status_score",
        [(True, StatusScore.FAILURE_TIMEOUT), (False, StatusScore.FAILURE_SYSTEM)],
    )
    def test_detailed_task_is_scored_correctly(self, sample_task, status_string, status_score):
        sample_task["status_details"]["type"] = "system"
        sample_task["status"] = "failed"
        sample_task["status_details"]["timed_out"] = status_string
        task = create_mock_task(sample_task)

        assert task.get_status_score() == status_score

    def test_get_execution_tasks(self, sample_task, sample_display_task):
        display_task = create_mock_task(sample_display_task)
        display_task._api.task_by_id.return_value = create_mock_task(sample_task)

        execution_tasks = display_task.get_execution_tasks()

        assert len(execution_tasks) == len(sample_display_task["execution_tasks"])

    def test_get_execution_tasks_with_filters(self, sample_task, sample_display_task):
        display_task = create_mock_task(sample_display_task)
        display_task._api.task_by_id.return_value = create_mock_task(sample_task)
        max_return = 2
        seen = 0

        def cap_seen(t):
            nonlocal seen
            if seen >= max_return:
                return False
            seen += 1
            return True

        display_task = create_mock_task(sample_display_task)
        execution_tasks = display_task.get_execution_tasks(filter_fn=cap_seen)

        assert len(execution_tasks) == max_return

    def test_get_manifest(self, sample_task):
        task = create_mock_task(sample_task)

        manifest = task.get_manifest()

        assert manifest == task._api.manifest_for_task.return_value
        task._api.manifest_for_task.assert_called_with(task.task_id)
