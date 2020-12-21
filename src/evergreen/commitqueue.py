# -*- encoding: utf-8 -*-
"""Commit Queue representation of evergreen."""
from __future__ import absolute_import

from typing import Any, List, Optional

from pydantic.main import BaseModel


class CommitQueueItem(BaseModel):
    """Representation of an entry in a commit queue."""

    issue: str
    modules: Optional[Any]


class CommitQueue(BaseModel):
    """Representation of a commit queue from evergreen."""

    queue_id: str
    queue: Optional[List[CommitQueueItem]]
