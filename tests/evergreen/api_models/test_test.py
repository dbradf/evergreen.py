# -*- encoding: utf-8 -*-
"""Unit tests for src/evergreen/test.py."""
from __future__ import absolute_import

from unittest.mock import MagicMock

from evergreen.api_models.tst import Tst


def create_mock_test(test_data):
    return Tst(MagicMock(), **test_data)


class TestTest(object):
    def test_get_attributes(self, sample_test):
        test = create_mock_test(sample_test)
        assert test.task_id == sample_test["task_id"]
        assert test.exit_code == sample_test["exit_code"]

    def test_logs(self, sample_test):
        test = create_mock_test(sample_test)
        assert test.logs.url == sample_test["logs"]["url"]

    def test_log_stream(self, sample_test):
        test = create_mock_test(sample_test)
        stream = test.stream_log()

        test._api.stream_log.assert_called_with(sample_test["logs"]["url_raw"])
        assert stream == test._api.stream_log.return_value
