"""Representation of project aliases."""
from typing import List, Optional

from pydantic import Field
from pydantic.main import BaseModel


class DisplayTaskAlias(BaseModel):
    """Representation of a DisplayTask in an alias."""

    name: str = Field(alias="Name")
    execution_tasks: Optional[List[str]] = Field(alias="ExecutionTasks")


class VariantAlias(BaseModel):
    """Representation of an alias for a particular build variant."""

    variant: str = Field(alias="Variant")
    tasks: List[str] = Field(alias="Tasks")
    display_tasks: List[DisplayTaskAlias] = Field(alias="DisplayTasks")
