# -*- encoding: utf-8 -*-
from __future__ import absolute_import

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from evergreen.manifest import Manifest
from evergreen.metrics.versionmetrics import VersionMetrics
from evergreen.version import Requester, Version

SAMPLE_VERSION_ID_FOR_PATCH = "5c9e8453d6d80a457091d74e"
EXPECTED_REQUESTER_PAIRS = [
    (Requester.PATCH_REQUEST, "patch"),
    (Requester.GITTER_REQUEST, "mainline"),
    (Requester.GITHUB_PULL_REQUEST, "patch"),
    (Requester.AD_HOC, "adhoc"),
    (Requester.TRIGGER_REQUEST, "trigger"),
]


def create_mock_version(version_data):
    return Version(MagicMock(), **version_data)


class TestRequester(object):
    @pytest.mark.parametrize(["requester", "value"], EXPECTED_REQUESTER_PAIRS)
    def test_stats_value(self, requester, value):
        assert requester.stats_value() == value


class TestVersion(object):
    def test_get_attributes(self, sample_version):
        version = create_mock_version(sample_version)
        assert version.version_id == sample_version["version_id"]

    def test_dates_are_correct(self, sample_version):
        version = create_mock_version(sample_version)
        assert isinstance(version.create_time, datetime)

    def test_build_variant_status(self, sample_version):
        version = create_mock_version(sample_version)
        assert len(sample_version["build_variants_status"]) == len(version.build_variants_status)

    def test_missing_build_variant_status(self, sample_version):
        del sample_version["build_variants_status"]
        version = create_mock_version(sample_version)

        assert not version.build_variants_status

        sample_version["build_variants_status"] = None
        version = create_mock_version(sample_version)

        assert not version.build_variants_status

    def test_get_manifest(self, sample_version, sample_manifest):
        version = create_mock_version(sample_version)
        version._api.manifest.return_value = Manifest(**sample_manifest)

        manifest = version.get_manifest()

        version._api.manifest.assert_called_with(
            sample_version["project"], sample_version["revision"]
        )
        assert len(manifest.modules) == len(sample_manifest["modules"])

    def test_get_modules(self, sample_version, sample_manifest):
        version = create_mock_version(sample_version)
        version._api.manifest.return_value = Manifest(**sample_manifest)

        modules = version.get_modules()

        assert len(modules) == len(sample_manifest["modules"])

    def test_is_patch_with_requester(self, sample_version):
        del sample_version["requester"]
        version = create_mock_version(sample_version)
        assert not version.is_patch()

        sample_version["version_id"] = SAMPLE_VERSION_ID_FOR_PATCH
        version = create_mock_version(sample_version)
        assert version.is_patch()

    def test_is_patch(self, sample_version):
        sample_version["requester"] = Requester.GITTER_REQUEST.evg_value()
        version = create_mock_version(sample_version)
        assert not version.is_patch()

        sample_version["requester"] = Requester.PATCH_REQUEST.evg_value()
        version = create_mock_version(sample_version)
        assert version.is_patch()

    def test_requester(self, requester_value, sample_version):
        sample_version["requester"] = requester_value.evg_value()
        version = create_mock_version(sample_version)
        assert version.requester == requester_value

    def test_get_builds(self, sample_version):
        version = create_mock_version(sample_version)
        assert version.get_builds() == version._api.builds_by_version.return_value

    def test_build_by_variant(self, sample_version):
        version = create_mock_version(sample_version)
        build_variant = sample_version["build_variants_status"][0]

        build = version.build_by_variant(build_variant["build_variant"])
        assert build == version._api.build_by_id.return_value
        version._api.build_by_id.assert_called_once_with(build_variant["build_id"])

    def test_get_patch_for_non_patch(self, sample_version):
        sample_version["requester"] = Requester.GITTER_REQUEST.evg_value()
        version = create_mock_version(sample_version)

        assert not version.get_patch()

    def test_get_patch_for_patch(self, sample_version):
        sample_version["version_id"] = SAMPLE_VERSION_ID_FOR_PATCH
        version = create_mock_version(sample_version)

        assert version.get_patch() == version._api.patch_by_id.return_value

    def test_started_version_is_not_completed(self, sample_version):
        sample_version["status"] = "started"
        version = create_mock_version(sample_version)

        assert not version.is_completed()

    def test_failed_version_is_completed(self, sample_version):
        sample_version["status"] = "failed"
        version = create_mock_version(sample_version)

        assert version.is_completed()

    def test_get_metrics_uncompleted(self, sample_version):
        sample_version["status"] = "created"
        version = create_mock_version(sample_version)

        assert not version.get_metrics()

    def test_get_metrics_completed(self, sample_version):
        sample_version["status"] = "failed"
        version = create_mock_version(sample_version)

        metrics = version.get_metrics()
        assert isinstance(metrics, VersionMetrics)
