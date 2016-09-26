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

"""Common errors thrown when repo presubmit checks fail."""

from __future__ import print_function

import os
import sys

_path = os.path.realpath(__file__ + '/../..')
if sys.path[0] != _path:
    sys.path.insert(0, _path)
del _path


class HookResult(object):
    """A single hook result."""

    def __init__(self, hook, project, commit, error, files=()):
        self.hook = hook
        self.project = project
        self.commit = commit
        self.error = error
        self.files = files

    def __bool__(self):
        return bool(self.error)

    def __nonzero__(self):
        """Python 2/3 glue."""
        return self.__bool__()


class HookCommandResult(HookResult):
    """A single hook result based on a CommandResult."""

    def __init__(self, hook, project, commit, result, files=()):
        HookResult.__init__(self, hook, project, commit,
                            result.error if result.error else result.output,
                            files=files)
        self.result = result

    def __bool__(self):
        return self.result.returncode not in (None, 0)
