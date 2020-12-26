# -*- encoding: utf-8 -*-
"""Unit tests for src/evergreen/host.py."""
from __future__ import absolute_import

from evergreen.api_models.commitqueue import CommitQueue


class TestCommitQueue(object):
    def test_get_attributes(self, sample_commit_queue):
        commit_queue = CommitQueue(**sample_commit_queue)
        assert commit_queue.queue_id == sample_commit_queue["queue_id"]
        assert commit_queue.queue[0].issue == sample_commit_queue["queue"][0]["issue"]

    def test_empty_queue(self, sample_commit_queue):
        sample_commit_queue["queue"] = None
        commit_queue = CommitQueue(**sample_commit_queue)
        assert commit_queue.queue is None
