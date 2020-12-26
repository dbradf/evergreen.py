# -*- encoding: utf-8 -*-
"""Stats representation of evergreen."""
from datetime import date

from pydantic import Field
from pydantic.main import BaseModel


class TestStats(BaseModel):
    """Representation of an Evergreen test stats object."""

    test_file: str
    task_name: str
    variant: str
    distro: str
    execution_date: date = Field(alias="date")
    num_pass: int
    num_fail: int
    avg_duration_pass: float


class TaskStats(BaseModel):
    """Representation of an Evergreen task stats object."""

    test_file: str
    task_name: str
    variant: str
    distro: str
    execution_date: date = Field(alias="date")
    num_pass: int
    num_fail: int
    avg_duration_pass: float
