#!/usr/bin/python
# -*- coding:utf-8 -*-
# Copyright 2016 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Repo pre-upload hook.

Normally this is loaded indirectly by repo itself, but it can be run directly
when developing.
"""

from __future__ import print_function

import argparse
import collections
import os
import sys

try:
    __file__
except NameError:
    # Work around repo until it gets fixed.
    # https://gerrit-review.googlesource.com/75481
    __file__ = os.path.join(os.getcwd(), 'pre-upload.py')
_path = os.path.dirname(os.path.realpath(__file__))
if sys.path[0] != _path:
    sys.path.insert(0, _path)
del _path

import rh.results
import rh.config
import rh.git
import rh.hooks
import rh.terminal
import rh.utils


# Repohooks homepage.
REPOHOOKS_URL = 'https://android.googlesource.com/platform/tools/repohooks/'


Project = collections.namedtuple('Project', ['name', 'dir', 'remote'])


def _process_hook_results(project, commit, commit_desc, results):
    """Prints the hook error to stderr with project and commit context

    Args:
      project: The project name.
      commit: The commit hash the errors belong to.
      commit_desc: A string containing the commit message.
      results: A list of HookResult objects.

    Returns:
      False if any errors were found, else True.
    """
    color = rh.terminal.Color()
    def _print_banner():
        print('%s: %s: hooks failed' %
              (color.color(color.RED, 'ERROR'), project),
              file=sys.stderr)

        commit_summary = commit_desc.splitlines()[0]
        print('COMMIT: %s (%s)' % (commit[0:12], commit_summary),
              file=sys.stderr)

    ret = True
    for result in results:
        if result:
            if ret:
                _print_banner()
                ret = False

            print('%s: %s' % (color.color(color.CYAN, 'HOOK'), result.hook),
                  file=sys.stderr)
            if result.files:
                print('  FILES: %s' % (result.files,), file=sys.stderr)
            lines = result.error.splitlines()
            print('\n'.join('    %s' % (x,) for x in lines), file=sys.stderr)
            print('', file=sys.stderr)

    return ret


def _get_project_hooks():
    """Returns a list of hooks that need to be run for a project.

    Expects to be called from within the project root.
    """
    global_paths = (
        # Load the global config found in the manifest repo.
        os.path.join(rh.git.find_repo_root(), '.repo', 'manifests'),
        # Load the global config found in the root of the repo checkout.
        rh.git.find_repo_root(),
    )
    paths = (
        # Load the config for this git repo.
        '.',
    )
    try:
        config = rh.config.PreSubmitConfig(paths=paths,
                                           global_paths=global_paths)
    except rh.config.ValidationError as e:
        print('invalid config file: %s' % (e,), file=sys.stderr)
        sys.exit(1)
    return config.callable_hooks()


def _run_project_hooks(project_name, proj_dir=None,
                       commit_list=None):
    """For each project run its project specific hook from the hooks dictionary.

    Args:
      project_name: The name of project to run hooks for.
      proj_dir: If non-None, this is the directory the project is in.  If None,
          we'll ask repo.
      commit_list: A list of commits to run hooks against.  If None or empty
          list then we'll automatically get the list of commits that would be
          uploaded.

    Returns:
      False if any errors were found, else True.
    """
    if proj_dir is None:
        cmd = ['repo', 'forall', project_name, '-c', 'pwd']
        result = rh.utils.run_command(cmd, capture_output=True)
        proj_dirs = result.output.split()
        if len(proj_dirs) == 0:
            print('%s cannot be found.' % project_name, file=sys.stderr)
            print('Please specify a valid project.', file=sys.stderr)
            return 0
        if len(proj_dirs) > 1:
            print('%s is associated with multiple directories.' % project_name,
                  file=sys.stderr)
            print('Please specify a directory to help disambiguate.',
                  file=sys.stderr)
            return 0
        proj_dir = proj_dirs[0]

    pwd = os.getcwd()
    # Hooks assume they are run from the root of the project.
    os.chdir(proj_dir)

    # If the repo has no pre-upload hooks enabled, then just return.
    hooks = list(_get_project_hooks())
    if not hooks:
        return True

    # Set up the environment like repo would with the forall command.
    remote = rh.git.get_upstream_remote()
    os.environ.update({
        'REPO_PROJECT': project_name,
        'REPO_PATH': proj_dir,
        'REPO_REMOTE': remote,
    })

    project = Project(name=project_name, dir=proj_dir, remote=remote)

    if not commit_list:
        commit_list = rh.git.get_commits()

    ret = True
    for commit in commit_list:
        # Mix in some settings for our hooks.
        os.environ['PREUPLOAD_COMMIT'] = commit
        diff = rh.git.get_affected_files(commit)
        desc = rh.git.get_commit_desc(commit)
        os.environ['PREUPLOAD_COMMIT_MESSAGE'] = desc

        results = []
        for hook in hooks:
            hook_results = hook(project, commit, desc, diff)
            if hook_results:
                results.extend(hook_results)
        if results:
            if not _process_hook_results(project.name, commit, desc, results):
                ret = False

    os.chdir(pwd)
    return ret


def main(project_list, worktree_list=None, **_kwargs):
    """Main function invoked directly by repo.

    We must use the name "main" as that is what repo requires.

    This function will exit directly upon error so that repo doesn't print some
    obscure error message.

    Args:
      project_list: List of projects to run on.
      worktree_list: A list of directories.  It should be the same length as
          project_list, so that each entry in project_list matches with a
          directory in worktree_list.  If None, we will attempt to calculate
          the directories automatically.
      kwargs: Leave this here for forward-compatibility.
    """
    found_error = False
    if not worktree_list:
        worktree_list = [None] * len(project_list)
    for project, worktree in zip(project_list, worktree_list):
        if not _run_project_hooks(project, proj_dir=worktree):
            found_error = True

    if found_error:
        color = rh.terminal.Color()
        print('%s: Preupload failed due to above error(s).\n'
              'For more info, please see:\n%s' %
              (color.color(color.RED, 'FATAL'), REPOHOOKS_URL),
              file=sys.stderr)
        sys.exit(1)


def _identify_project(path):
    """Identify the repo project associated with the given path.

    Returns:
      A string indicating what project is associated with the path passed in or
      a blank string upon failure.
    """
    cmd = ['repo', 'forall', '.', '-c', 'echo ${REPO_PROJECT}']
    return rh.utils.run_command(cmd, capture_output=True, redirect_stderr=True,
                                cwd=path).output.strip()


def direct_main(argv):
    """Run hooks directly (outside of the context of repo).

    Args:
      argv: The command line args to process.

    Returns:
      0 if no pre-upload failures, 1 if failures.

    Raises:
      BadInvocation: On some types of invocation errors.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', default=None,
                        help='The directory that the project lives in.  If not '
                        'specified, use the git project root based on the cwd.')
    parser.add_argument('--project', default=None,
                        help='The project repo path; this can affect how the '
                        'hooks get run, since some hooks are project-specific.'
                        'If not specified, `repo` will be used to figure this '
                        'out based on the dir.')
    parser.add_argument('commits', nargs='*',
                        help='Check specific commits')
    opts = parser.parse_args(argv)

    # Check/normalize git dir; if unspecified, we'll use the root of the git
    # project from CWD.
    if opts.dir is None:
        cmd = ['git', 'rev-parse', '--git-dir']
        git_dir = rh.utils.run_command(cmd, capture_output=True,
                                       redirect_stderr=True).output.strip()
        if not git_dir:
            parser.error('The current directory is not part of a git project.')
        opts.dir = os.path.dirname(os.path.abspath(git_dir))
    elif not os.path.isdir(opts.dir):
        parser.error('Invalid dir: %s' % opts.dir)
    elif not os.path.isdir(os.path.join(opts.dir, '.git')):
        parser.error('Not a git directory: %s' % opts.dir)

    # Identify the project if it wasn't specified; this _requires_ the repo
    # tool to be installed and for the project to be part of a repo checkout.
    if not opts.project:
        opts.project = _identify_project(opts.dir)
        if not opts.project:
            parser.error("Repo couldn't identify the project of %s" % opts.dir)

    if _run_project_hooks(opts.project, proj_dir=opts.dir,
                          commit_list=opts.commits):
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(direct_main(sys.argv[1:]))
