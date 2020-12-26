# -*- encoding: utf-8 -*-
"""Host representation of evergreen."""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import PrivateAttr
from pydantic.main import BaseModel

if TYPE_CHECKING:
    from evergreen.api import EvergreenApi
    from evergreen.api_models.build import Build
    from evergreen.api_models.version import Version


class HostDistro(BaseModel):
    """Representation of a distro."""

    distro_id: str
    provider: str
    image_id: str


class RunningTask(BaseModel):
    """Representation of a running task."""

    task_id: Optional[str]
    name: Optional[str]
    dispatch_time: Optional[datetime]
    version_id: Optional[str]
    build_id: Optional[str]


class Host(BaseModel):
    """Representation of an Evergreen host."""

    host_id: str
    host_url: str
    provisioned: bool
    started_by: str
    host_type: str
    user: str
    status: Optional[str]
    user_host: bool
    distro: HostDistro
    running_task: RunningTask

    _api: "EvergreenApi" = PrivateAttr()

    def __init__(self, api: "EvergreenApi", **json: Dict[str, Any]) -> None:
        """Create an instance of an evergreen host."""
        super().__init__(**json)

        self._api = api

    def get_build(self) -> Optional["Build"]:
        """
        Get the build for the build using this host.

        :return: build for task running on this host.
        """
        if self.running_task.build_id:
            return self._api.build_by_id(self.running_task.build_id)
        return None

    def get_version(self) -> Optional["Version"]:
        """
        Get the version for the task using this host.

        :return: version for task running on this host.
        """
        if self.running_task.version_id:
            return self._api.version_by_id(self.running_task.version_id)
        return None

    def __str__(self) -> str:
        """Get a human readable string version of this host."""
        return f"{self.host_id}: {self.distro.distro_id} - {self.status}"
