# -*- encoding: utf-8 -*-
"""Version representation of evergreen."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from pydantic import BaseModel, PrivateAttr

from evergreen.manifest import ManifestModule
from evergreen.metrics.versionmetrics import VersionMetrics

if TYPE_CHECKING:
    from evergreen.api import EvergreenApi
    from evergreen.build import Build
    from evergreen.manifest import Manifest
    from evergreen.patch import Patch  # noqa: F401


class Requester(Enum):
    """Requester that created version."""

    PATCH_REQUEST = "patch_request"
    GITTER_REQUEST = "gitter_request"
    GITHUB_PULL_REQUEST = "github_pull_request"
    MERGE_TEST = "merge_test"
    AD_HOC = "ad_hoc"
    TRIGGER_REQUEST = "trigger_request"
    UNKNOWN = "unknown"

    def evg_value(self) -> str:
        """Get the evergreen value for a requester."""
        return self.name.lower()

    def stats_value(self) -> str:
        """Get the value for the stats endpoints."""
        value_mappings = {
            Requester.PATCH_REQUEST: "patch",
            Requester.GITTER_REQUEST: "mainline",
            Requester.GITHUB_PULL_REQUEST: "patch",
            Requester.MERGE_TEST: "",
            Requester.AD_HOC: "adhoc",
            Requester.TRIGGER_REQUEST: "trigger",
            Requester.UNKNOWN: "",
        }

        return value_mappings[self]


PATCH_REQUESTERS = {
    Requester.PATCH_REQUEST,
    Requester.GITHUB_PULL_REQUEST,
    Requester.MERGE_TEST,
}

EVG_VERSION_STATUS_SUCCESS = "success"
EVG_VERSION_STATUS_FAILED = "failed"
EVG_VERSION_STATUS_CREATED = "created"

COMPLETED_STATES = {
    EVG_VERSION_STATUS_FAILED,
    EVG_VERSION_STATUS_SUCCESS,
}


class BuildVariantStatus(BaseModel):
    """Representation of a Build Variants status."""

    build_variant: str
    build_id: str


class Version(BaseModel):
    """Representation of an Evergreen Version."""

    version_id: str
    create_time: datetime
    start_time: Optional[datetime]
    finish_time: Optional[datetime]
    revision: str
    order: int
    project: str
    author: str
    author_email: str
    message: str
    status: str
    repo: str
    branch: str
    # errors = evg_attrib("errors")
    # warnings = evg_attrib("warnings")
    ignored = bool
    requester: Optional[Requester]
    build_variants_status: Optional[List[BuildVariantStatus]]

    _api: "EvergreenApi" = PrivateAttr()
    _build_variants_map: Dict[str, str] = PrivateAttr()

    def __init__(self, api: "EvergreenApi", **json: Dict[str, Any]) -> None:
        """
        Create an instance of an evergreen version.

        :param json: json representing version
        """
        super().__init__(**json)
        self._api = api

        self._build_variants_map = {}

        if self.build_variants_status:
            self._build_variants_map = {
                bvs.build_variant: bvs.build_id for bvs in self.build_variants_status
            }

    def build_by_variant(self, build_variant: str) -> "Build":
        """
        Get a build object for the specified variant.

        :param build_variant: Build variant to get build for.
        :return: Build object for variant.
        """
        return self._api.build_by_id(self._build_variants_map[build_variant])

    def get_manifest(self) -> "Manifest":
        """
        Get the manifest for this version.

        :return: Manifest for this version.
        """
        return self._api.manifest(self.project, self.revision)

    def get_modules(self) -> Optional[Dict[str, ManifestModule]]:
        """
        Get the modules for this version.

        :return: ManifestModules for this version.
        """
        return self.get_manifest().modules

    def get_builds(self) -> List["Build"]:
        """
        Get all the builds that are a part of this version.

        :return: List of build that are a part of this version.
        """
        return self._api.builds_by_version(self.version_id)

    def is_patch(self) -> bool:
        """
        Determine if this version from a patch build.

        :return: True if this version is a patch build.
        """
        if self.requester and self.requester != Requester.UNKNOWN:
            return self.requester in PATCH_REQUESTERS
        return not self.version_id.startswith(self.project.replace("-", "_"))

    def is_completed(self) -> bool:
        """
        Determine if this version has completed running tasks.

        :return: True if version has completed.
        """
        return self.status in COMPLETED_STATES

    def get_patch(self) -> Optional["Patch"]:
        """
        Get the patch information for this version.

        :return: Patch for this version.
        """
        if self.is_patch():
            return self._api.patch_by_id(self.version_id)
        return None

    def get_metrics(self, task_filter_fn: Optional[Callable] = None) -> Optional[VersionMetrics]:
        """
        Calculate the metrics for this version.

        Metrics are only available on versions that have finished running.

        :param task_filter_fn: function to filter tasks included for metrics, should accept a task
                               argument.
        :return: Metrics for this version.
        """
        if self.status != EVG_VERSION_STATUS_CREATED:
            return VersionMetrics(self).calculate(task_filter_fn)
        return None

    def __repr__(self) -> str:
        """
        Get the string representation of Version for debugging purposes.

        :return: String representation of Version.
        """
        return "Version({id})".format(id=self.version_id)
