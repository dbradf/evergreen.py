# -*- encoding: utf-8 -*-
"""Unit tests for stats representation of evergreen."""
import evergreen.task_reliability as under_test


class TestTaskReliability(object):
    def test_get_attributes(self, sample_task_reliability):
        task_reliability = under_test.TaskReliability(**sample_task_reliability)
        assert task_reliability.task_name == sample_task_reliability["task_name"]
        assert task_reliability.success_rate == sample_task_reliability["success_rate"]
