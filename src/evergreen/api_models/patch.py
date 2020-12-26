"""Representation of an evergreen patch."""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from pydantic import PrivateAttr
from pydantic.main import BaseModel

if TYPE_CHECKING:
    from evergreen.api import EvergreenApi
    from evergreen.api_models.version import Version


class GithubPatchData(BaseModel):
    """Representation of github patch data in a patch object."""

    pr_number: int
    base_owner: str
    base_repo: str
    head_owner: str
    head_repo: str
    head_hash: str
    author: str


class VariantsTasks(BaseModel):
    """Representation of a variants tasks object."""

    name: str
    tasks: Set[str]


class Patch(BaseModel):
    """Representation of an Evergreen patch."""

    patch_id: str
    description: str
    project_id: str
    branch: str
    git_hash: str
    patch_number: int
    author: str
    version: str
    status: str
    create_time: datetime
    start_time: Optional[datetime]
    finish_time: Optional[datetime]
    builds: List[str]
    tasks: List[str]
    activated: bool
    alias: str
    variants_tasks: List[VariantsTasks]
    github_patch_data: GithubPatchData

    _api: "EvergreenApi" = PrivateAttr()
    _variant_task_dict: Dict[str, Set[str]] = PrivateAttr()

    def __init__(self, api: "EvergreenApi", **json: Dict[str, Any]) -> None:
        """
        Create an instance of an evergreen patch.

        :param json: json representing patch.
        """
        super().__init__(**json)

        self._api = api
        self._variant_task_dict = {vt.name: vt.tasks for vt in self.variants_tasks}

    def task_list_for_variant(self, variant: str) -> Set[str]:
        """
        Retrieve the list of tasks for the given variant.

        :param variant: name of variant to search for.
        :return: list of tasks belonging to the specified variant.
        """
        return self._variant_task_dict[variant]

    def get_version(self) -> "Version":
        """
        Get version for this patch.

        :return: Version object.
        """
        return self._api.version_by_id(self.version)

    def __str__(self) -> str:
        """Get a human readable string version of the patch."""
        return f"{self.patch_id}: {self.description}"
