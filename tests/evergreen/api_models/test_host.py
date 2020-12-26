# -*- encoding: utf-8 -*-
"""Unit tests for src/evergreen/host.py."""
from __future__ import absolute_import

from datetime import datetime
from unittest.mock import MagicMock

from evergreen.api_models.host import Host


def create_mock_host(host_data):
    return Host(MagicMock(), **host_data)


class TestHost(object):
    def test_get_attributes(self, sample_host):
        host = create_mock_host(sample_host)
        assert host.status == sample_host["status"]
        assert host.host_id == sample_host["host_id"]

    def test_running_task(self, sample_host):
        host = create_mock_host(sample_host)
        running_task = host.running_task
        assert running_task.task_id == sample_host["running_task"]["task_id"]
        assert isinstance(running_task.dispatch_time, datetime)

    def test_get_build(self, sample_host):
        host = create_mock_host(sample_host)
        assert host._api.build_by_id.return_value == host.get_build()

    def test_get_version(self, sample_host):
        host = create_mock_host(sample_host)
        assert host._api.version_by_id.return_value == host.get_version()

    def test_missing_values(self, sample_host):
        del sample_host["status"]
        host = create_mock_host(sample_host)
        assert not host.status
