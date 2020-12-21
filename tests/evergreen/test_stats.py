# -*- encoding: utf-8 -*-
"""Unit tests for stats representation of evergreen."""
from __future__ import absolute_import

import evergreen.stats as under_test


class TestTestStats(object):
    def test_get_attributes(self, sample_test_stats):
        test_stats = under_test.TestStats(**sample_test_stats)
        assert test_stats.test_file == sample_test_stats["test_file"]
        assert test_stats.task_name == sample_test_stats["task_name"]


class TestTaskStats(object):
    def test_get_attributes(self, sample_task_stats):
        task_stats = under_test.TaskStats(**sample_task_stats)
        assert task_stats.test_file == sample_task_stats["test_file"]
        assert task_stats.task_name == sample_task_stats["task_name"]
