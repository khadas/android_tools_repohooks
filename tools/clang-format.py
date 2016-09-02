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

"""Wrapper to run git-clang-format and parse its output."""

from __future__ import print_function

import argparse
import os
import sys

_path = os.path.realpath(__file__ + '/../..')
if sys.path[0] != _path:
    sys.path.insert(0, _path)
del _path

import rh.shell
import rh.utils


# Since we're asking git-clang-format to print a diff, all modified filenames
# that have formatting errors are printed with this prefix.
DIFF_MARKER_PREFIX = '+++ b/'


def get_parser():
    """Return a command line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clang-format', default='clang-format',
                        help='The path of the clang-format executable.')
    parser.add_argument('--git-clang-format', default='git-clang-format',
                        help='The path of the git-clang-format executable.')
    parser.add_argument('--commit', type=str, default='HEAD',
                        help='Specify the commit to validate.')
    return parser


def main(argv):
    """The main entry."""
    parser = get_parser()
    opts, unknown = parser.parse_known_args(argv)

    # TODO(b/31305183): Avoid false positives by limiting git-clang-format's
    # diffs to just that commit instead of from the parent of the commit against
    # the working tree.
    cmd = [opts.git_clang_format, '--binary',
           opts.clang_format, '--commit=%s^' % opts.commit] + unknown

    stdout = rh.utils.run_command(cmd + ['--diff'], capture_output=True).output
    if stdout.rstrip('\n') == 'no modified files to format':
        # This is always printed when only files that clang-format does not
        # understand were modified.
        return 0

    diff_filenames = []
    for line in stdout.splitlines():
        if line.startswith(DIFF_MARKER_PREFIX):
            diff_filenames.append(line[len(DIFF_MARKER_PREFIX):].rstrip())

    if diff_filenames:
        print('The following files have formatting errors:')
        for filename in diff_filenames:
            print('\t%s' % filename)
        print('You can run `%s` to fix this' % rh.shell.cmd_to_str(cmd))
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
