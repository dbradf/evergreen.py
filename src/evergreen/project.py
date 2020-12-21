# -*- encoding: utf-8 -*-
"""Evergreen representation of a project."""
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, PrivateAttr

from evergreen.version import Version

if TYPE_CHECKING:
    from evergreen.api import EvergreenApi


class ProjectCommitQueue(BaseModel):
    """Status of commit queue for the project."""

    enabled: bool
    merge_method: str
    patch_type: str


class Project(BaseModel):
    """Representation of an Evergreen project."""

    batch_time: int
    branch_name: str
    display_name: str
    enabled: bool
    identifier: str
    owner_name: str
    private: bool
    remote_path: str
    repo_name: str
    tracked: bool
    deactivated_previous: Optional[bool]
    admins: List[str]
    tracks_push_events: bool
    pr_testing_enabled: bool
    commit_queue: ProjectCommitQueue

    _api: "EvergreenApi" = PrivateAttr()

    def __init__(self, api: "EvergreenApi", **json: Dict[str, Any]) -> None:
        """
        Create an instance of an evergreen project.

        :param api: evergreen api object.
        """
        super().__init__(**json)
        self._api = api

    def __str__(self) -> str:
        """Get a string version of the Project."""
        return self.identifier

    def most_recent_version(self) -> Version:
        """
        Fetch the most recent version.

        :return: Version queried for.
        """
        version_iterator = self._api.versions_by_project(self.identifier)
        return next(version_iterator)
