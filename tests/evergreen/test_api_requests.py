"""Unit tests for api_requests.py"""
from datetime import datetime

import evergreen.api_requests as under_test
from evergreen import Requester
from evergreen.util import format_evergreen_date


class TestStatsSpecification:
    def test_empty_params(self):
        spec = under_test.StatsSpecification(project_id="project id")

        assert spec.get_params() == {}

    def test_params(self):
        expected_params = {
            "after_date": datetime.now(),
            "before_date": datetime.now(),
            "group_num_days": 3,
            "requesters": Requester.GITTER_REQUEST,
            "tasks": ["task1", "task2"],
            "variants": ["variants1", "variants2"],
            "distros": ["distro 1", "distro 2"],
            "group_by": "tasks",
            "sort": "latests",
        }
        spec = under_test.StatsSpecification(project_id="my project", **expected_params)

        expected_params["after_date"] = format_evergreen_date(expected_params["after_date"])
        expected_params["before_date"] = format_evergreen_date(expected_params["before_date"])

        assert "my project" == spec.project_id
        assert expected_params == spec.get_params()
