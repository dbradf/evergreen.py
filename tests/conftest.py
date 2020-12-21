import json
import os
from unittest.mock import MagicMock

import pytest
import yaml

from evergreen.api import CachedEvergreenApi, EvergreenApi, RetryingEvergreenApi
from evergreen.config import EvgAuth
from evergreen.version import Requester

TESTS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA_PATH = os.path.join(TESTS_DIRECTORY, "evergreen", "data")


def get_sample_json(file):
    """Read json data from the specified sample file."""
    with open(os.path.join(SAMPLE_DATA_PATH, file), "r") as file_data:
        return json.load(file_data)


def get_sample_yaml(file):
    """Read yml data from the specified sample file."""
    with open(os.path.join(SAMPLE_DATA_PATH, file), "r") as file_data:
        return yaml.safe_load(file_data)


@pytest.fixture()
def sample_host():
    """Return sample host json."""
    return get_sample_json("host.json")


@pytest.fixture()
def sample_build():
    """Return sample build json."""
    return get_sample_json("build.json")


@pytest.fixture()
def sample_commit_queue():
    """Return sample commit_queue json."""
    return get_sample_json("commit_queue.json")


@pytest.fixture()
def sample_aws_distro():
    """Return sample aws distro json."""
    return get_sample_json("distro_aws.json")


@pytest.fixture()
def sample_static_distro():
    """Return sample static distro json."""
    return get_sample_json("distro_static.json")


@pytest.fixture()
def sample_task():
    """Return sample task json."""
    return get_sample_json("task.json")


@pytest.fixture()
def sample_task_list():
    """Return sample task json."""
    return [
        get_sample_json("task.json"),
        get_sample_json("task.json"),
        get_sample_json("task.json"),
    ]


@pytest.fixture()
def sample_display_task():
    """Return sample display task json."""
    return get_sample_json("task_display_only.json")


@pytest.fixture()
def sample_version():
    """Return sample version json."""
    return get_sample_json("version.json")


@pytest.fixture()
def sample_test_stats():
    """Return sample test_stats json."""
    return get_sample_json("test_stats.json")


@pytest.fixture()
def sample_task_stats():
    """Return sample task_stats json."""
    return get_sample_json("task_stats.json")


@pytest.fixture()
def sample_task_reliability():
    """Return sample task_reliability json."""
    return get_sample_json("task_reliability.json")


@pytest.fixture()
def sample_manifest():
    """Return sample manifest json."""
    return get_sample_json("manifest.json")


@pytest.fixture()
def sample_patch():
    """Return sample patch json."""
    return get_sample_json("patch.json")


@pytest.fixture()
def sample_project():
    """Return sample project json."""
    return get_sample_json("project.json")


@pytest.fixture()
def sample_projects():
    """Return sample projects json."""
    return get_sample_json("projects.json")


@pytest.fixture()
def sample_test():
    """Return sample test json."""
    return get_sample_json("test.json")


@pytest.fixture()
def sample_version_alias():
    """Return sample version alias json."""
    return get_sample_json("version_alias.json")


@pytest.fixture()
def sample_task_annotation():
    """Return sample task annotation json."""
    return get_sample_json("task_annotations.json")


@pytest.fixture()
def sample_recent_versions():
    """Return sample recent versions data."""
    return get_sample_json("recent_versions.json")


@pytest.fixture()
def mocked_api_response():
    """Mocked response returned by mock_api."""
    response_mock = MagicMock()
    response_mock.status_code = 200
    response_mock.json.return_value = [{"create_time": "2019-03-10T02:43:49.330"}]
    return response_mock


@pytest.fixture()
def mocked_api(mocked_api_response):
    """Return an Evergreen API with a mocked session."""
    api = EvergreenApi()
    api._session = MagicMock()
    api._session.request.return_value = mocked_api_response
    return api


@pytest.fixture()
def mocked_cached_api():
    """Return an Evergreen API with a mocked session."""
    api = CachedEvergreenApi()
    api._session = MagicMock()
    response_mock = MagicMock()
    response_mock.status_code = 200
    api._session.request.return_value = response_mock
    return api


@pytest.fixture()
def mocked_retrying_api():
    """Return an Evergreen API with a mocked session."""
    api = RetryingEvergreenApi()
    api._session = MagicMock()
    response_mock = MagicMock()
    response_mock.status_code = 200
    api._session.request.return_value = response_mock
    return api


@pytest.fixture()
def sample_performance_results():
    """Return sample performance results."""
    return get_sample_json("performance_results.json")


@pytest.fixture()
def sample_evergreen_configuration():
    """Return sample evergreen configuration"""
    return get_sample_yaml("evergreen_config.yml")


@pytest.fixture()
def sample_test_run():
    """Return sample evergreen configuration"""
    return get_sample_json("test_run.json")


@pytest.fixture()
def sample_evergreen_auth(sample_evergreen_configuration):
    """Return sample evergreen configuration"""
    return EvgAuth(
        sample_evergreen_configuration["user"], sample_evergreen_configuration["api_key"]
    )


@pytest.fixture(params=(list(Requester)))
def requester_value(request):
    return request.param
