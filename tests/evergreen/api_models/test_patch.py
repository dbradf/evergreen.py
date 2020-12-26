# -*- encoding: utf-8 -*-
"""Unit tests for src/evergreen/host.py."""
from __future__ import absolute_import

from unittest.mock import MagicMock

from evergreen.api_models.patch import Patch


def create_mock_patch(patch_data):
    return Patch(MagicMock(), **patch_data)


class TestPatch(object):
    def test_get_attributes(self, sample_patch):
        patch = create_mock_patch(sample_patch)
        assert patch.description == sample_patch["description"]
        assert patch.version == sample_patch["version"]
        assert patch.github_patch_data.pr_number == sample_patch["github_patch_data"]["pr_number"]

    def test_variants_tasks(self, sample_patch):
        patch = create_mock_patch(sample_patch)
        assert len(patch.variants_tasks) == len(sample_patch["variants_tasks"])
        for vt, svt in zip(patch.variants_tasks, sample_patch["variants_tasks"]):
            assert vt.name == svt["name"]
            assert isinstance(vt.tasks, set)

    def test_task_list_for_variant(self, sample_patch):
        patch = create_mock_patch(sample_patch)
        sample_variant = sample_patch["variants_tasks"][0]
        variant_name = sample_variant["name"]
        assert patch.task_list_for_variant(variant_name) == set(sample_variant["tasks"])
