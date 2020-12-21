"""Command line driver for evergreen API."""
from __future__ import absolute_import

import json
from enum import Enum
from itertools import islice

import click
import yaml

from evergreen import EvergreenApi

DisplayFormat = Enum("DisplayFormat", "human json yaml")


def fmt_output(fmt, data):
    """
    Convert the given data into the specified format.

    :param fmt: DisplayFormat to use.
    :param data: Data to convert.
    :return: Data is specified format.
    """
    if fmt == DisplayFormat.json:
        return json.dumps(data, indent=4, default=str)
    if fmt == DisplayFormat.yaml:
        return yaml.safe_dump(data)
    return data


@click.group()
@click.option(
    "--json", "display_format", flag_value=DisplayFormat.json, help="Write output in json."
)
@click.option(
    "--yaml", "display_format", flag_value=DisplayFormat.yaml, help="Write output in yaml."
)
@click.option(
    "--human-readable",
    "display_format",
    flag_value=DisplayFormat.human,
    default=True,
    help="Write output in a human readable format.",
)
@click.pass_context
def cli(ctx, display_format):
    """Create common CLI options."""
    ctx.ensure_object(dict)
    ctx.obj["api"] = EvergreenApi.get_api(use_config_file=True)
    ctx.obj["format"] = display_format


@cli.command()
@click.pass_context
def list_hosts(ctx):
    """List the hosts running in evergreen."""
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]
    host_list = api.all_hosts()
    click.echo(fmt_output(fmt, [host.dict() for host in host_list]))


@cli.command()
@click.pass_context
@click.option("-p", "--project", required=True)
@click.option("-l", "--limit", type=int)
def list_patches(ctx, project, limit):
    """Get the patches for the given project."""
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]
    patches = []
    for i, p in enumerate(api.patches_by_project(project)):
        patches.append(p.dict())
        if limit and i > limit:
            break
    click.echo(fmt_output(fmt, patches))


@cli.command()
@click.pass_context
def list_projects(ctx):
    """List the evergreen projects."""
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]
    project_list = api.all_projects()
    projects = [project.dict() for project in project_list]
    click.echo(fmt_output(fmt, projects))


@cli.command()
@click.pass_context
@click.option("--project", required=True)
@click.option("--limit", type=int)
def list_versions(ctx, project, limit):
    """Get the versions for the given project."""
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]
    version_list = api.versions_by_project(project)
    versions_to_display = [version for version in islice(version_list, None, limit)]

    click.echo(fmt_output(fmt, versions_to_display))


@cli.command()
@click.pass_context
@click.option("-a", "--after-date", required=True)
@click.option("-b", "--before-date", required=True)
@click.option("-p", "--project", required=True)
@click.option("-d", "--distros", multiple=True)
@click.option("--group-by")
@click.option("-g", "--group-num-days")
@click.option("-r", "--requesters", multiple=True)
@click.option("-s", "--sort")
@click.option("--tests", multiple=True)
@click.option("-t", "--tasks", multiple=True)
@click.option("-v", "--variants", multiple=True)
def test_stats(
    ctx,
    after_date,
    before_date,
    project,
    distros,
    group_by,
    group_num_days,
    requesters,
    sort,
    tests,
    tasks,
    variants,
):
    """Get the test stats specified."""
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]

    test_stat_list = api.test_stats_by_project(
        project,
        after_date,
        before_date,
        group_num_days,
        requesters,
        tests,
        tasks,
        variants,
        distros,
        group_by,
        sort,
    )
    test_statistics = [t.json for t in test_stat_list]
    click.echo(fmt_output(fmt, test_statistics))


@cli.command()
@click.pass_context
@click.option("-a", "--after-date", required=True)
@click.option("-b", "--before-date", required=True)
@click.option("-p", "--project", required=True)
@click.option("-d", "--distros", multiple=True)
@click.option("--group-by")
@click.option("-g", "--group-num-days")
@click.option("-r", "--requesters", multiple=True)
@click.option("-s", "--sort")
@click.option("-t", "--tasks", multiple=True)
@click.option("-v", "--variants", multiple=True)
def task_stats(
    ctx,
    after_date,
    before_date,
    project,
    distros,
    group_by,
    group_num_days,
    requesters,
    sort,
    tasks,
    variants,
):
    """Get the specified task stats."""
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]

    task_stat_list = api.task_stats_by_project(
        project,
        after_date,
        before_date,
        group_num_days,
        requesters,
        tasks,
        variants,
        distros,
        group_by,
        sort,
    )
    task_statistics = [t.json for t in task_stat_list]
    click.echo(fmt_output(fmt, task_statistics))


RELIABILITY_GROUP_MAPPING = {
    "task": "task",
    "variant": "task_variant",
    "distro": "task_variant_distro",
}


@cli.command()
@click.pass_context
@click.option("-a", "--after-date", help="The earliest date to use. iso-8601 format.")
@click.option("-b", "--before-date", help="The latest date to use. iso-8601 format.")
@click.option(
    "-p", "--project", required=True, help="The evergreen project, eg 'mongodb-mongo-master'"
)
@click.option("-d", "--distros", multiple=True, help="The list of distributions.")
@click.option(
    "--group-by",
    type=click.Choice(RELIABILITY_GROUP_MAPPING.keys()),
    default="task",
    help="Group the results by 'task', 'variant' or 'distro'. Defaults to 'task'",
)
@click.option(
    "-g",
    "--group-num-days",
    default=28,
    help="The number of days to group results by. Defaults to 28.",
)
@click.option("-r", "--requesters", multiple=True, help="The requesters.")
@click.option("-s", "--sort", help="The sort order, can be earliest or latest.")
@click.option(
    "-t",
    "--tasks",
    multiple=True,
    required=True,
    help="The list of tasks, e.g. 'lint' , 'compile'. Required, no default.",
)
@click.option("-v", "--variants", multiple=True, help="The list of build variants.")
def task_reliability(
    ctx,
    after_date,
    before_date,
    project,
    distros,
    group_by,
    group_num_days,
    requesters,
    sort,
    tasks,
    variants,
):
    """
    Get the Task Reliability scores for the matching tasks.

    \b
    Examples:
    \b
        # Get the scores for mongodb-mongo-master project, compile task (grouped by task)
        # for today (1 day, grouped by days 1).
        $> evg-api --json task-reliability -p mongodb-mongo-master -t compile
    OR
        $> evg-api --json task-reliability -p mongodb-mongo-master -t compile \\
            --group-by task

    \b
        # Get the scores for mongodb-mongo-master project, compile task (grouped by variant)
        # for today (1 day, grouped by days 1).
        $> evg-api --json task-reliability -p mongodb-mongo-master -t compile \\
            --group-by variant

    \b
        # Get the scores for mongodb-mongo-master project, compile and lint tasks (grouped by distro)
        # for today (1 day, grouped by days 1).
        $> evg-api --json task-reliability -p mongodb-mongo-master -t compile -t lint \\
            --group-by distro
    \b
        # Get the scores for mongodb-mongo-master project, lint and compile tasks (grouped by distro)
        # for the last 28 days.
        $> evg-api --json task-reliability -p mongodb-mongo-master -t lint -t compile -g 1 \\
            -a $(date -I --date="27 days ago")
    OR
        $> evg-api --json task-reliability -p mongodb-mongo-master -t lint -t compile -g 1 \\
            -a $(date -I --date="27 days ago") -b $(date -I)
    OR
        $> evg-api --json task-reliability -p mongodb-mongo-master -t lint -t compile -g 1 \\
            --group_num_days 28

    \b
        # Get the scores for mongodb-mongo-master project, lint and compile tasks (grouped by distro)
        # for each day for the last 28 days.
        $> evg-api --json task-reliability -p mongodb-mongo-master -t lint -t compile \\
            --group_by distro -a $(date -I --date="27 days ago")

    \b
        # Get the scores for mongodb-mongo-master project, lint task (grouped by task) , grouped in
        # batches of 28 days for all dates after 168 days ago.
        $> evg-api   --json task-reliability   -p mongodb-mongo-master -t lint  --group-by task \\
            -g 28 -a $(date -I --date="$((28 * 6 - 1)) days ago")

    \f
    :see: 'task reliability
        <https://github.com/evergreen-ci/evergreen/wiki/REST-V2-Usage#taskreliability>'
    """
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]

    task_reliability_list = api.task_reliability_by_project(
        project,
        after_date,
        before_date,
        group_num_days,
        requesters,
        tasks,
        variants,
        distros,
        RELIABILITY_GROUP_MAPPING[group_by],
        sort,
    )
    task_reliability_scores = [t.json for t in task_reliability_list]
    click.echo(fmt_output(fmt, task_reliability_scores))


@cli.command()
@click.pass_context
@click.option("-v", "--version", "version_id", required=True)
@click.option("--builds", is_flag=True, default=False, help="Include builds of version in output")
def version_stats(ctx, version_id, builds):
    """
    Collect stats for the given evergreen version.

    :param ctx: Command context.
    :param version_id: Id of version to analyze.
    :param builds: Include builds of version in output.
    """
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]

    version = api.version_by_id(version_id)
    if fmt == DisplayFormat.human:
        click.echo(version.get_metrics())
    else:
        click.echo(fmt_output(fmt, version.get_metrics().as_dict(include_children=builds)))


@cli.command()
@click.pass_context
@click.option("-b", "--build", "build_id", required=True)
@click.option("--tasks", is_flag=True, default=False, help="Include tasks of build in output")
def build_stats(ctx, build_id, tasks):
    """
    Collect stats for the given evergreen build.

    :param ctx: Command context.
    :param build_id: Id of build to analyze.
    :param tasks: If true include tasks in output.
    """
    api = ctx.obj["api"]
    fmt = ctx.obj["format"]

    build = api.build_by_id(build_id)
    if fmt == DisplayFormat.human:
        click.echo(build.get_metrics())
    else:
        click.echo(fmt_output(fmt, build.get_metrics().as_dict(include_children=tasks)))


def main():
    """Create command line application."""
    return cli(obj={})


if __name__ == "__main__":
    main()
