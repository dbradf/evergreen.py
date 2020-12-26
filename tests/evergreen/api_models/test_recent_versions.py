"""Unit tests for recent_versions.py."""

import evergreen.api_models.recent_versions as under_test


class TestRecentVersions(object):
    def test_attributes(self, sample_recent_versions):
        recent_versions = under_test.RecentVersions(**sample_recent_versions)

        for variant in sample_recent_versions["build_variants"]:
            assert variant in recent_versions.build_variants

        assert 2 == len(recent_versions.get_versions())
