# -*- encoding: utf-8 -*-
"""Stats representation of evergreen."""
from datetime import date

from pydantic import Field
from pydantic.main import BaseModel


class TaskReliability(BaseModel):
    """Representation of an Evergreen task reliability object."""

    num_success: int
    num_timeout: int
    num_failed: int
    num_system_failed: int
    num_test_failed: int
    num_setup_failed: int
    num_total: int
    success_rate: float
    avg_duration_success: float
    execution_date: date = Field(alias="date")
    variant: str
    task_name: str
    distro: str
