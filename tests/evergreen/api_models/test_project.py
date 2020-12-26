# -*- encoding: utf-8 -*-
"""Unit tests for src/evergreen/project.py."""
from __future__ import absolute_import

from unittest.mock import MagicMock

from evergreen.api_models.project import Project


class TestProject(object):
    def test_most_recent_version(self, sample_project):
        mock_api = MagicMock()
        project = Project(mock_api, **sample_project)
        mock_api.versions_by_project.return_value = (
            MagicMock(version_id=f"version_{i}") for i in range(3)
        )

        most_recent_version = project.most_recent_version()

        assert most_recent_version.version_id == "version_0"
