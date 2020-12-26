"""Objects for making requests to the API."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional

from evergreen.api_models.version import Requester
from evergreen.util import format_evergreen_date


class IssueLinkRequest(NamedTuple):
    """Issue to add to a task annotation."""

    issue_key: str
    url: str

    def as_dict(self) -> Dict[str, str]:
        """Get a dictionary representation of the issue link."""
        return {"issue_key": self.issue_key, "url": self.url}


@dataclass
class StatsSpecification:
    """
    Specification for what stats to query.

    project_id: Id of patch to query for.
    after_date: Collect stats after this date.
    before_date: Collect stats before this date.
    group_num_days: Aggregate statistics to this size.
    requesters: Filter by requesters (mainline, patch, trigger, or adhoc).
    tests: Only include specified tests (Only for test stats).
    tasks: Only include specified tasks.
    variants: Only include specified variants.
    distros: Only include specified distros.
    group_by How to group results (test_task_variant, test_task, or test)
    sort: How to sort results (earliest or latest).
    """

    project_id: str
    after_date: Optional[datetime] = None
    before_date: Optional[datetime] = None
    group_num_days: Optional[int] = None
    requesters: Optional[Requester] = None
    tests: Optional[List[str]] = None
    tasks: Optional[List[str]] = None
    variants: Optional[List[str]] = None
    distros: Optional[List[str]] = None
    group_by: Optional[str] = None
    sort: Optional[str] = None

    def get_params(self) -> Dict[str, Any]:
        """Get the options as a dictionary of parameters."""
        params: Dict[str, Any] = {}
        if self.after_date:
            params["after_date"] = format_evergreen_date(self.after_date)
        if self.before_date:
            params["before_date"] = format_evergreen_date(self.before_date)
        if self.group_num_days:
            params["group_num_days"] = self.group_num_days
        if self.requesters:
            params["requesters"] = self.requesters
        if self.tests:
            params["tests"] = self.tests
        if self.tasks:
            params["tasks"] = self.tasks
        if self.variants:
            params["variants"] = self.variants
        if self.distros:
            params["distros"] = self.distros
        if self.group_by:
            params["group_by"] = self.group_by
        if self.sort:
            params["sort"] = self.sort

        return params
