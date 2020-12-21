import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from unittest.mock import MagicMock, patch

import pytest
import requests
from requests.exceptions import HTTPError

import evergreen.api as under_test
from evergreen.config import DEFAULT_NETWORK_TIMEOUT_SEC
from evergreen.util import EVG_DATETIME_FORMAT, parse_evergreen_datetime


def ns(relative):
    return "evergreen.api." + relative


def from_iso_format(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


class TestConfiguration(object):
    def test_uses_passed_auth(self, sample_evergreen_auth):
        kwargs = under_test.EvergreenApi._setup_kwargs(auth=sample_evergreen_auth)
        assert kwargs["auth"] == sample_evergreen_auth
        assert kwargs["timeout"] == DEFAULT_NETWORK_TIMEOUT_SEC

    @patch(ns("read_evergreen_config"))
    def test_uses_default_config_file(
        self, mock_read_evergreen_config, sample_evergreen_configuration, sample_evergreen_auth
    ):
        mock_read_evergreen_config.return_value = sample_evergreen_configuration
        kwargs = under_test.EvergreenApi._setup_kwargs(use_config_file=True)
        mock_read_evergreen_config.assert_called_once()
        assert kwargs["auth"] == sample_evergreen_auth
        assert kwargs["timeout"] == DEFAULT_NETWORK_TIMEOUT_SEC

    @patch(ns("read_evergreen_from_file"))
    def test_uses_passed_config_file(
        self, read_evergreen_from_file, sample_evergreen_configuration, sample_evergreen_auth
    ):
        read_evergreen_from_file.return_value = sample_evergreen_configuration
        kwargs = under_test.EvergreenApi._setup_kwargs(config_file="config.yml")
        read_evergreen_from_file.assert_called_once_with("config.yml")
        assert kwargs["auth"] == sample_evergreen_auth
        assert kwargs["timeout"] == DEFAULT_NETWORK_TIMEOUT_SEC


class TestRaiseForStatus(object):
    @pytest.mark.skipif(
        sys.version_info.major == 2, reason="JSONDecodeError is not used in python2"
    )
    def test_non_json_error(self, mocked_api):
        mocked_response = MagicMock()
        mocked_response.json.side_effect = JSONDecodeError("json error", "", 0)
        mocked_response.status_code = 500
        mocked_response.raise_for_status.side_effect = HTTPError()
        mocked_api.session.request.return_value = mocked_response

        with pytest.raises(HTTPError):
            mocked_api.version_by_id("version_id")

        mocked_response.raise_for_status.assert_called_once()

    def test_json_errors_are_passed_through(self, mocked_api):
        error_msg = "the error"
        mocked_response = MagicMock()
        mocked_response.json.return_value = {"error": error_msg}
        mocked_response.status_code = 500
        mocked_response.raise_for_status.side_effect = HTTPError()
        mocked_api.session.request.return_value = mocked_response

        with pytest.raises(HTTPError) as excinfo:
            mocked_api.version_by_id("version_id")

        assert error_msg in str(excinfo.value)
        mocked_response.raise_for_status.assert_not_called()


class TestLazyPagination(object):
    def test_with_no_next(self, mocked_api):
        returned_items = ["item 1", "item 2", "item 3"]
        mocked_api.session.request.return_value.json.return_value = returned_items

        results = mocked_api._lazy_paginate("http://url")

        result_count = 0
        for result in results:
            assert result in returned_items
            result_count += 1

        assert len(returned_items) == result_count

    def test_next_in_response(self, mocked_api):
        returned_items = ["item 1", "item 2", "item 3"]
        next_url = "http://url_to_next"
        mocked_api.session.request.return_value.json.return_value = returned_items
        mocked_api.session.request.return_value.links = {"next": {"url": next_url}}

        results = mocked_api._lazy_paginate("http://url")

        items_to_check = len(returned_items) * 3
        for i, result in enumerate(results):
            assert result in returned_items
            if i > items_to_check:
                break

        assert i > items_to_check


class TestSessions(object):
    def test_session_can_be_created(self):
        evg_api = under_test.EvergreenApi()

        session_instance_one = evg_api.session
        session_instance_two = evg_api.session

        assert session_instance_one is not None
        assert session_instance_two is not None
        assert session_instance_one != session_instance_two

    def test_with_session_creates_a_new_session(self):
        original_evg_api = under_test.EvergreenApi()

        with original_evg_api.with_session() as evg_api_with_session:
            session_instance_one = evg_api_with_session.session
            session_instance_two = evg_api_with_session.session

            assert session_instance_one == session_instance_two
            assert original_evg_api.session != evg_api_with_session.session


class TestProjectApi(object):
    def test_all_projects_with_filter(self, mocked_api, mocked_api_response, sample_projects):
        mocked_api_response.json.return_value = sample_projects

        def filter_fn(project):
            return project.identifier == "project 2"

        projects = mocked_api.all_projects(filter_fn)

        assert len(projects) == 1
        assert projects[0].identifier == "project 2"

    def test_versions_by_project_time_window(self, mocked_api, sample_version, mocked_api_response):
        version_list = [
            deepcopy(sample_version),
            deepcopy(sample_version),
            deepcopy(sample_version),
        ]
        # Create a window of 1 day, and set the dates so that only the middle items should be
        # returned.
        one_day = timedelta(days=1)
        one_hour = timedelta(hours=1)
        before_date = parse_evergreen_datetime(version_list[1]["create_time"])
        after_date = before_date - one_day

        version_list[0]["create_time"] = (before_date + one_day).strftime(EVG_DATETIME_FORMAT)
        version_list[1]["create_time"] = (before_date - one_hour).strftime(EVG_DATETIME_FORMAT)
        version_list[2]["create_time"] = (after_date - one_day).strftime(EVG_DATETIME_FORMAT)

        mocked_api_response.json.return_value = version_list

        windowed_versions = mocked_api.versions_by_project_time_window(
            "project_id", before_date, after_date
        )

        windowed_list = list(windowed_versions)

        assert len(windowed_list) == 1
        assert version_list[1]["version_id"] == windowed_list[0].version_id

    def test_configure_patch(self, mocked_api):
        variants = ["my_variant", ["*"]]
        description = "mypatch"
        mocked_api.configure_patch("patch_id", description=description, variants=variants)
        expected_url = mocked_api._create_url("/patches/patch_id/configure")
        expected_data = json.dumps({"variants": variants, "description": description})
        mocked_api.session.request.assert_called_with(
            url=expected_url, params=None, timeout=None, data=expected_data, method="POST"
        )

    def test_configure_patch_variants(self, mocked_api):
        variants = ["my_variant", ["task_one", "task_two"]]
        mocked_api.configure_patch("patch_id", variants=variants)
        expected_url = mocked_api._create_url("/patches/patch_id/configure")
        expected_data = json.dumps({"variants": variants})
        mocked_api.session.request.assert_called_with(
            url=expected_url, params=None, timeout=None, data=expected_data, method="POST"
        )

    def test_patches_by_project_time_window(self, mocked_api, sample_patch, mocked_api_response):
        patch_list = [
            deepcopy(sample_patch),
            deepcopy(sample_patch),
            deepcopy(sample_patch),
        ]
        # Create a window of 1 day, and set the dates so that only the middle items should be
        # returned.
        one_day = timedelta(days=1)
        one_hour = timedelta(hours=1)
        before_date = parse_evergreen_datetime(patch_list[1]["create_time"])
        after_date = before_date - one_day

        patch_list[0]["create_time"] = (before_date + one_day).strftime(EVG_DATETIME_FORMAT)
        patch_list[1]["create_time"] = (before_date - one_hour).strftime(EVG_DATETIME_FORMAT)
        patch_list[2]["create_time"] = (after_date - one_day).strftime(EVG_DATETIME_FORMAT)

        mocked_api_response.json.return_value = patch_list

        windowed_versions = mocked_api.patches_by_project_time_window(
            "project_id", before_date, after_date
        )

        windowed_list = list(windowed_versions)

        assert len(windowed_list) == 1
        assert patch_list[1]["patch_id"] == windowed_list[0].patch_id


class TestLogApi(object):
    def test_retrieve_log(self, mocked_api):
        mocked_api.retrieve_task_log("log_url")
        mocked_api.session.request.assert_called_with(
            url="log_url", params={}, timeout=None, data=None, method="GET"
        )

    def test_retrieve_log_with_raw(self, mocked_api):
        mocked_api.retrieve_task_log("log_url", raw=True)
        mocked_api.session.request.assert_called_with(
            url="log_url", params={"text": "true"}, timeout=None, data=None, method="GET"
        )

    def test_stream_log(self, mocked_api):
        streamed_data = ["line_{}".format(i) for i in range(10)]
        mocked_response = MagicMock()
        mocked_response.iter_lines.return_value = streamed_data
        mocked_response.status_code = 200
        mocked_api.session.get.return_value.__enter__.return_value = mocked_response

        for line in mocked_api.stream_log("log_url"):
            assert line in streamed_data


class TestRetryingEvergreenApi(object):
    def test_no_retries_on_success(self, mocked_retrying_api, sample_version):
        version_id = "version id"
        mocked_retrying_api.session.request.return_value.json.return_value = sample_version

        mocked_retrying_api.version_by_id(version_id)
        assert mocked_retrying_api.session.request.call_count == 1

    @pytest.mark.skipif(
        not os.environ.get("RUN_SLOW_TESTS"), reason="Slow running test due to retries"
    )
    def test_three_retries_on_failure(self, mocked_retrying_api):
        version_id = "version id"
        mocked_retrying_api.session.request.side_effect = HTTPError()

        with pytest.raises(HTTPError):
            mocked_retrying_api.version_by_id(version_id)

        assert mocked_retrying_api.session.request.call_count == under_test.MAX_RETRIES

    @pytest.mark.skipif(
        not os.environ.get("RUN_SLOW_TESTS"), reason="Slow running test due to retries"
    )
    def test_pass_on_retries_after_failure(self, mocked_retrying_api, sample_version):
        version_id = "version id"
        successful_response = mocked_retrying_api.session.request.return_value
        mocked_retrying_api.session.request.return_value.json.return_value = sample_version
        mocked_retrying_api.session.request.side_effect = [HTTPError(), successful_response]

        mocked_retrying_api.version_by_id(version_id)

        assert mocked_retrying_api.session.request.call_count == 2

    @pytest.mark.skipif(
        not os.environ.get("RUN_SLOW_TESTS"), reason="Slow running test due to retries"
    )
    def test_pass_on_retries_after_connection_error(self, mocked_retrying_api, sample_version):
        version_id = "version id"
        successful_response = mocked_retrying_api.session.request.return_value
        mocked_retrying_api.session.request.return_value.json.return_value = sample_version

        mocked_retrying_api.session.request.side_effect = [
            requests.exceptions.ConnectionError(),
            successful_response,
        ]

        mocked_retrying_api.version_by_id(version_id)

        assert mocked_retrying_api.session.request.call_count == 2

    def test_no_retries_on_non_http_errors(self, mocked_retrying_api):
        version_id = "version id"
        mocked_retrying_api.session.request.side_effect = ValueError("Unexpected Failure")

        with pytest.raises(ValueError):
            mocked_retrying_api.version_by_id(version_id)

        assert mocked_retrying_api.session.request.call_count == 1
