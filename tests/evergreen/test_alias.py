"""Unit tests for src/evergreen/alias.py."""

from evergreen.alias import DisplayTaskAlias, VariantAlias


class TestVariantAlias(object):
    def test_get_attributes(self, sample_version_alias):
        alias = VariantAlias(**sample_version_alias)

        assert alias.variant == sample_version_alias["Variant"]
        assert len(alias.tasks) == len(sample_version_alias["Tasks"])

    def test_display_tasks(self, sample_version_alias):
        alias = VariantAlias(**sample_version_alias)

        display_tasks = alias.display_tasks

        assert len(display_tasks) == len(sample_version_alias["DisplayTasks"])
        assert type(display_tasks[0]) == DisplayTaskAlias
        assert display_tasks[0].name == sample_version_alias["DisplayTasks"][0]["Name"]
