# Changelog

## 3.0.0 - 2020-12-21
- Use pydantic for json serialization.

## 2.2.0 - 2020-12-04
- Add support for the task annotations API.

## 2.1.0 - 2020-11-09
- Only create re-usable session when requested to do so.

## 2.0.6 - 2020-11-03
- Don't add unrequested limit on paginated calls.

## 2.0.5 - 2020-10-30
- Add support for getting a single test by task id and test file

## 2.0.4 - 2020-10-29
- Allow structlog > 19

## 2.0.3 - 2020-10-29
- Add support for support for /projects/{project_id}/revisions/{commit_hash}/tasks

## 2.0.2 - 2020-10-28
- Update recent versions endpoint to return a python class instead of raw JSON

## 2.0.1 - 2020-10-28
- Add endpoints for updating patches and tasks

## 2.0.0 - 2020-10-28
- Add py.typed file to allow clients to use type information.
- Fix type issues in the API interface.

## 1.4.9 - 2020-10-26
- Add API calls to get patches by user.

## 1.4.8 - 2020-10-03
- Add isort for import sorting.
- Add bugbear static analysis.
- Add pre-commit configuration.

## 1.4.7 - 2020-08-25
- Add endpoint to get manifest for a task.

## 1.4.6
- Extend exception types covered in retries.

## 1.4.5
- Fix docs builds.

## 1.4.4 - 2020-08-03
- Add support for any json or json history stored in evergreen.

## 1.4.3 - 2020-07-23
- Add support for the /test_alias endpoint.

## 1.4.2 - 2020-07-21
- Fix wrapping of /projects/<id>/recent_versions API responses into an incompatible object

## 1.4.1 - 2020-07-05
- Add API documentation site.

## 1.4.0 - 2020-06-25
- Get a list of execution tasks from a display task.

## 1.3.1 - 2020-06-17
- Task.get_tests should default to the task execution.

## 1.3.0 - 2020-05-08
* Add python 3.6 support.

## 1.2.1 - 2020-05-07
- Add support for filtering all_projects and fetching a given module for a project.

## 1.2.0 - 2020-04-07
- Rethrow same exception if retries fail.

## 1.1.0 - 2020-02-18
- Switch to poetry for dependency management.
- Add mypy, black and pydocstyle checks.

## 1.0.2 - 2020-02-13
- Handle different timestamp formats from evergreen API.

## 1.0.1 - 2019-12-09
- Add `TRIGGER_REQUEST` request type.

## 1.0.0 - 2019-12-04
- Add `requester` field to `Version`.
- Better handling of `is_patch` in `Version`.
- Drop Python 2 support.

## 0.6.16 - 2019-12-03
- Add displayable counts to builds metrics

## 0.6.15 - 2019-11-22
- Handle empty artifacts in a task.

## 0.6.14 - 2019-11-14
- Do not convert type of start/end in performance results.

## 0.6.13 - 2019-11-04
- Add a windowing iterator.
- Add a common import point.

## 0.6.12 - 2019-10-24
- Update evergreen tasks so that deploy is only done after the test for the
 proposed version already existing finishes

## 0.6.11 - 2019-10-23
- Add support for stream log files.

## 0.6.10 - 2019-10-08
- Fixed formatting of performance results.

## 0.6.9 - 2019-09-11
- Remove pylibversion dependency in setup.

## 0.6.7 - 2019-09-06
- Fix issue with pip install.

## 0.6.6 - 2019-09-05
- Add support for metrics not reporting operations per second

## 0.6.5 - 2019-09-04
- Add CD support from evergreen.

## 0.6.4 - 2019-08-28
- Removed after_date default on task reliability.
- Updated task reliability documentation.

## 0.6.3 - 2019-08-27
- Supported multiprocessing use cases by implementing pickle support

## 0.6.2 - 2019-08-22
- Handle passed config file
- Remove broken project history API

## 0.6.1 - 2019-08-21
- Handle versions with empty`build_variants_status`.

## 0.6.0 - 2019-08-20
- Use new signal_processing supporting endpoints.

## 0.5.0 - 2019-08-14
- Add lazy versions by project endpoint.

## 0.4.1 - 2019-08-14
- Add task stats support.
- Add task reliability support.
- Support reading api_server_host from .evergreen.yml.

## 0.4.0 - 2019-07-30
- Use new commit_queue endpoints.

## 0.3.9 - 2019-07-15
- Update requests version.

## 0.3.8 - 2019-07-15
- Improved logging with structlog.

## 0.3.7 - 2019-07-11
- Better handle builds complete.

## 0.3.6 - 2019-07-11
- Watch for empty builds.

## 0.3.5 - 2019-07-11
- Account for undispatched builds.

## 0.3.4 - 2019-07-11
- Check builds are activated for metrics.

## 0.3.3 - 2019-07-11
- Relax version metrics check.

## 0.3.2 - 2019-06-27
- Add a retrying API.

## 0.3.1 - 2019-06-26
- Add task filter for metrics.

## 0.3.0 - 2019-06-24
- Simplified Metrics API.

## 0.2.3 - 2019-06-22
- Better metrics support.

## 0.2.2 - 2019-06-21
- Add metrics.
- Add network timeout support.

## 0.2.1 - 2019-06-20
- Add /distros support.

## 0.2.0 - 2019-06-16
- Change command line to evg-api.
- Add support for yaml and json command line output.
- Bug fixes.

## 0.1.16 - 2019-06-03
- Add endpoint that returns the wait time between dependencies being fulfilled and start of task

## 0.1.15 - 2019-05-31
- Add endpoint to query commit-queue.

## 0.1.14 - 2019-05-01
- Support for specifying a config file.

## 0.1.13 - 2019-04-18
- Add endpoints to get task logs.

## 0.1.12 - 2019-04-05
- Don't use current directory to search for evergreen config.

## 0.1.11 - 2019-03-29
- Improvements to version object.

## 0.1.10 - 2019-03-29
- Add attributes to evergreen objects.

## 0.1.9 - 2019-03-28
- Add basic task endpoints.
