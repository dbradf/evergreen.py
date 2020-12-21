# -*- encoding: utf-8 -*-
"""Unit tests for src/evergreen/host.py."""
from __future__ import absolute_import

from evergreen.distro import Distro


class TestDistro(object):
    def test_get_attributes(self, sample_aws_distro):
        distro = Distro(**sample_aws_distro)

        assert distro.name == sample_aws_distro["name"]
        assert distro.provider == sample_aws_distro["provider"]
        assert distro.planner_settings.version == sample_aws_distro["planner_settings"]["version"]
        assert distro.finder_settings.version == sample_aws_distro["finder_settings"]["version"]

    def test_settings(self, sample_aws_distro):
        distro = Distro(**sample_aws_distro)
        settings = distro.distro_settings
        setting_json = sample_aws_distro["settings"]

        assert settings.ami == setting_json["ami"]

        mount_point = settings.mount_points[0]
        assert mount_point.device_name == setting_json["mount_points"][0]["device_name"]

    def test_expansions(self, sample_aws_distro):
        distro = Distro(**sample_aws_distro)

        for expansion in sample_aws_distro["expansions"]:
            assert distro.expansion[expansion["key"]] == expansion["value"]

    def test_missing_attributes(self, sample_aws_distro):
        del sample_aws_distro["settings"]
        distro = Distro(**sample_aws_distro)

        assert not distro.settings

    def test_missing_mount_points(self, sample_aws_distro):
        del sample_aws_distro["settings"]["mount_points"]
        distro = Distro(**sample_aws_distro)

        assert not distro.distro_settings.mount_points

    def test_static_distro(self, sample_static_distro):
        distro = Distro(**sample_static_distro)

        assert len(distro.distro_settings.hosts) == len(sample_static_distro["settings"]["hosts"])
        for host in sample_static_distro["settings"]["hosts"]:
            assert host["name"] in distro.distro_settings.host_list()

    def test_static_distro_missing_hosts(self, sample_static_distro):
        del sample_static_distro["settings"]["hosts"]
        distro = Distro(**sample_static_distro)

        assert not distro.distro_settings

    def test_unknown_provider_distro(self, sample_aws_distro):
        sample_aws_distro["provider"] = "some_unknown_provider"
        distro = Distro(**sample_aws_distro)

        assert distro.settings == sample_aws_distro["settings"]
