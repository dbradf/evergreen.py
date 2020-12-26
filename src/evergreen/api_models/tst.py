# -*- encoding: utf-8 -*-
"""Test representation of evergreen."""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional

from pydantic import PrivateAttr
from pydantic.main import BaseModel

if TYPE_CHECKING:
    from evergreen.api import EvergreenApi


class Logs(BaseModel):
    """Representation of test logs from evergreen."""

    url: Optional[str]
    line_num: int
    url_raw: Optional[str]
    log_id: Optional[str]


class Tst(BaseModel):
    """Representation of a test object from evergreen."""

    task_id: str
    status: str
    test_file: str
    exit_code: int
    start_time: datetime
    end_time: Optional[datetime]
    logs: Logs

    _api: "EvergreenApi" = PrivateAttr()

    def __init__(self, api: "EvergreenApi", **json: Dict[str, Any]) -> None:
        """Create an instance of a Test object."""
        super().__init__(**json)

        self._api = api

    def stream_log(self) -> Iterable[str]:
        """
        Retrieve an iterator of the streamed contents of this log.

        :return: Iterable to stream contents of log.
        """
        if self.logs.url_raw:
            return self._api.stream_log(self.logs.url_raw)
        return []
