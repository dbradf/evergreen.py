"""Models to working with task annotations."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic.main import BaseModel


class Source(BaseModel):
    """Source of where an annotation was generated."""

    author: str
    time: datetime
    requester: str


class IssueLink(BaseModel):
    """Representation of a issue added as a task annotation."""

    url: str
    issue_key: str
    source: Source


class Note(BaseModel):
    """Representation of a note associated with a task annotation."""

    message: str
    source: Source


class TaskAnnotation(BaseModel):
    """Representation of a task annotation."""

    task_id: str
    task_execution: int
    issues: List[IssueLink]
    suspected_issues: List[IssueLink]
    note: Note
    metadata: Optional[Dict[str, Any]]
