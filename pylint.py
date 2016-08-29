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

"""Wrapper to run pylint with the right settings."""

from __future__ import print_function

import argparse
import os
import sys


def get_parser():
    """Return a command line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+')
    return parser


def main(argv):
    """The main entry."""
    parser = get_parser()
    opts = parser.parse_args(argv)

    pylintrc = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'pylintrc')
    cmd = ['pylint', '--rcfile', pylintrc] + opts.files
    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
