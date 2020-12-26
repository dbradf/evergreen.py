"""Recent versions for an evergreen project."""
from datetime import datetime
from itertools import chain
from typing import Any, Dict, List, Optional, Set

from pydantic import Field
from pydantic.main import BaseModel

from evergreen.api_models.build import StatusCounts
from evergreen.api_models.version import BuildVariantStatus


class RecentBuild(BaseModel):
    """Recent Evergreen Build."""

    id: str = Field(alias="_id")
    project_id: str
    create_time: Optional[datetime]
    start_time: Optional[datetime]
    finish_time: Optional[datetime]
    version: str
    git_hash: str
    build_variant: str
    status: str
    activated: bool
    activated_by: str
    activated_time: Optional[datetime]
    order: int
    tasks: List[str]
    time_taken_ms: int
    display_name: str
    predicted_makespan_ms: int
    actual_makespan_ms: int
    origin: str
    status_counts: StatusCounts


class RecentVersion(BaseModel):
    """Recent Evergreen Version."""

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
    parameters: List[Any]
    build_variants_status: Optional[List[BuildVariantStatus]]
    requester: str
    errors: List[str]


class VersionRow(BaseModel):
    """Row of recent Evergreen versions."""

    rolled_up: bool
    versions: List[RecentVersion]


class BuildRow(BaseModel):
    """Row of recent Evergreen builds."""

    build_variant: str
    builds: Dict[str, RecentBuild]


class RecentVersions(BaseModel):
    """Wrapper for the data object returned by /projects/{project_id}/recent_versions."""

    rows: Dict[str, BuildRow]
    build_variants: Set[str]
    versions: List[VersionRow]

    def get_versions(self) -> List[RecentVersion]:
        """
        Get the list of versions from the recent versions response object.

        :return: List of versions from the response object
        """
        return list(chain.from_iterable([v.versions for v in self.versions]))
