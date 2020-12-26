from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

import evergreen.cli.main as under_test
from evergreen.api_models.host import Host
from evergreen.api_models.patch import Patch
from evergreen.api_models.project import Project

output_formats = [
    "--json",
    "--yaml",
    None,
]


@pytest.fixture(params=output_formats)
def output_fmt(request):
    return request.param


def _create_api_mock(monkeypatch):
    mock_generator = MagicMock()
    evg_api_mock = mock_generator.get_api.return_value
    monkeypatch.setattr(under_test, "EvergreenApi", mock_generator)
    return evg_api_mock


def test_list_hosts(monkeypatch, sample_host, output_fmt):
    evg_api_mock = _create_api_mock(monkeypatch)
    evg_api_mock.all_hosts.return_value = [Host(evg_api_mock, **sample_host)]

    runner = CliRunner()
    cmd_list = [output_fmt, "list-hosts"] if output_fmt else ["list-hosts"]
    result = runner.invoke(under_test.cli, cmd_list)
    assert result.exit_code == 0
    assert sample_host["host_id"] in result.output


def test_list_patches(monkeypatch, sample_patch, output_fmt):
    evg_api_mock = _create_api_mock(monkeypatch)
    evg_api_mock.patches_by_project.return_value = [
        Patch(evg_api_mock, **sample_patch) for _ in range(10)
    ]

    runner = CliRunner()
    cmd_list = ["list-patches", "--project", "project", "--limit", "5"]
    if output_fmt:
        cmd_list = [output_fmt] + cmd_list
    result = runner.invoke(under_test.cli, cmd_list)
    assert result.exit_code == 0
    assert sample_patch["patch_id"] in result.output


def test_list_projects(monkeypatch, sample_project, output_fmt):
    evg_api_mock = _create_api_mock(monkeypatch)
    evg_api_mock.all_projects.return_value = [
        Project(evg_api_mock, **sample_project) for _ in range(10)
    ]

    runner = CliRunner()
    cmd_list = ["list-projects"]
    if output_fmt:
        cmd_list = [output_fmt] + cmd_list
    result = runner.invoke(under_test.cli, cmd_list)
    assert result.exit_code == 0
    assert sample_project["identifier"] in result.output
