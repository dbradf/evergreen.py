# -*- encoding: utf-8 -*-
"""Host representation of evergreen."""
from typing import Any, Dict, List, Optional

from pydantic import PrivateAttr
from pydantic.main import BaseModel

AWS_AUTO_PROVIDER = "ec2-auto"
AWS_ON_DEMAND_PROVIDER = "ec2-ondemand"
DOCKER_PROVIDER = "docker"
STATIC_PROVIDER = "static"


class MountPoint(BaseModel):
    """Representation of Mount Point in distro settings."""

    device_name: str
    size: int
    virtual_name: str


class DistroHost(BaseModel):
    """Host running the distro."""

    name: str


class StaticDistroSettings(BaseModel):
    """Representation of Evergreen static distro settings."""

    hosts: Optional[List[DistroHost]]

    def host_list(self) -> List[str]:
        """Get the list of names of hosts."""
        if self.hosts:
            return [host.name for host in self.hosts]
        return []


class DockerDistroSettings(BaseModel):
    """Representation of docker distro settings."""

    image_url: str


class AwsDistroSettings(BaseModel):
    """Representation of AWS Distro Settings."""

    ami: str
    aws_access_key_id: Optional[str]
    aws_access_secret_id: Optional[str]
    bid_price: float
    instance_type: str
    ipv6: Optional[str]
    is_vpc: bool
    key_name: str
    mount_points: Optional[List[MountPoint]]
    region: Optional[str]
    security_group: str
    security_group_ids: List[str]
    subnet_id: str
    # user_data = evg_attrib("user_data")
    vpc_name: str


class PlannerSettings(BaseModel):
    """Representation of planner settings."""

    version: str
    minimum_hosts: int
    maximum_hosts: int
    target_time: int
    acceptable_host_idle_time: int
    group_versions: Optional[bool]
    patch_zipper_factor: int
    task_ordering: str


class FinderSettings(BaseModel):
    """Representation of finder settings."""

    version: str


class DistroExpansion(BaseModel):
    """Expansion for a distro."""

    key: str
    value: str


_PROVIDER_MAP = {
    AWS_ON_DEMAND_PROVIDER: AwsDistroSettings,
    AWS_AUTO_PROVIDER: AwsDistroSettings,
    DOCKER_PROVIDER: DockerDistroSettings,
    STATIC_PROVIDER: StaticDistroSettings,
}


class Distro(BaseModel):
    """Representation of an Evergreen Distro."""

    name: str
    user_spawn_allowed: bool
    provider: str
    image_id: Optional[str]
    arch: str
    work_dir: str
    pool_size: int
    setup_as_sudo: bool
    setup: str
    teardown: str
    user: str
    bootstrap_method: str
    communication_method: str
    clone_method: str
    shell_path: str
    curator_dir: str
    client_dir: str
    jasper_credentials_path: Optional[str]
    ssh_key: str
    ssh_options: List[str]
    disabled: bool
    container_pool: str
    expansions: List[DistroExpansion]
    planner_settings: Optional[PlannerSettings]
    finder_settings: FinderSettings
    settings: Optional[Dict[str, Any]]

    _expansion_map: Dict[str, str] = PrivateAttr()

    def __init__(self, **json: Dict[str, Any]) -> None:
        """
        Create an instance of a distro.

        :param json: Json of a distro.
        """
        super().__init__(**json)

        self._expansion_map = {exp.key: exp.value for exp in self.expansions}

    @property
    def distro_settings(self) -> Optional[Any]:
        """
        Retrieve the settings for the distro.

        :return: settings for distro.
        """
        if self.settings:
            if self.provider in _PROVIDER_MAP:
                return _PROVIDER_MAP[self.provider](**self.settings)
            return self.settings
        return None

    @property
    def expansion(self) -> Dict[str, str]:
        """Get a dictionary of defined expansions."""
        return self._expansion_map
