"""Unit tests for task_annotations."""

import evergreen.task_annotations as under_test


class TestTaskAnnotation(object):
    def test_getting_attributes(self, sample_task_annotation):
        task_annotation = under_test.TaskAnnotation(**sample_task_annotation)

        assert task_annotation.task_id == sample_task_annotation["task_id"]
        assert task_annotation.task_execution == sample_task_annotation["task_execution"]
        assert task_annotation.note.message == sample_task_annotation["note"]["message"]
        assert len(task_annotation.suspected_issues) == len(
            sample_task_annotation["suspected_issues"]
        )
