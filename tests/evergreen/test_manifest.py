# -*- encoding: utf-8 -*-
"""Unit tests for src/evergreen/manifest.py."""
from __future__ import absolute_import

from evergreen.manifest import Manifest


class TestManifest(object):
    def test_get_attributes(self, sample_manifest):
        manifest = Manifest(**sample_manifest)
        assert manifest.id == sample_manifest["id"]
        assert manifest.revision == sample_manifest["revision"]

    def test_manifest_modules(self, sample_manifest):
        manifest = Manifest(**sample_manifest)
        assert len(manifest.modules) == len(sample_manifest["modules"])
        for module in sample_manifest["modules"]:
            assert module in manifest.modules
            manifest_module = manifest.modules[module]
            assert manifest_module.revision == sample_manifest["modules"][module]["revision"]
