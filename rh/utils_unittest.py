#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Copyright 2019 The Android Open Source Project
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

"""Unittests for the utils module."""

from __future__ import print_function

import os
import sys
import unittest

_path = os.path.realpath(__file__ + '/../..')
if sys.path[0] != _path:
    sys.path.insert(0, _path)
del _path

# We have to import our local modules after the sys.path tweak.  We can't use
# relative imports because this is an executable program, not a module.
# pylint: disable=wrong-import-position
import rh
import rh.utils
from rh.sixish import mock


class CommandResultTests(unittest.TestCase):
    """Verify behavior of CommandResult object."""

    def test_empty_cmdstr(self):
        """Check cmdstr with an empty command."""
        result = rh.utils.CommandResult(cmd=[])
        self.assertEqual('', result.cmdstr)

    def test_basic_cmdstr(self):
        """Check cmdstr with a basic command command."""
        result = rh.utils.CommandResult(cmd=['ls', 'a b'])
        self.assertEqual("ls 'a b'", result.cmdstr)

    def test_str(self):
        """Check str() handling."""
        # We don't enforce much, just that it doesn't crash.
        result = rh.utils.CommandResult()
        self.assertNotEqual('', str(result))
        result = rh.utils.CommandResult(cmd=[])
        self.assertNotEqual('', str(result))

    def test_repr(self):
        """Check repr() handling."""
        # We don't enforce much, just that it doesn't crash.
        result = rh.utils.CommandResult()
        self.assertNotEqual('', repr(result))
        result = rh.utils.CommandResult(cmd=[])
        self.assertNotEqual('', repr(result))


class RunCommandErrorTests(unittest.TestCase):
    """Verify behavior of RunCommandError object."""

    def setUp(self):
        self.result = rh.utils.CommandResult(cmd=['mycmd'])

    def test_basic(self):
        """Basic test we can create a normal instance."""
        rh.utils.RunCommandError('msg', self.result)
        rh.utils.RunCommandError('msg', self.result, exception=Exception('bad'))

    def test_stringify(self):
        """Check stringify() handling."""
        # We don't assert much so we leave flexibility in changing format.
        err = rh.utils.RunCommandError('msg', self.result)
        self.assertIn('mycmd', err.stringify())
        err = rh.utils.RunCommandError('msg', self.result,
                                       exception=Exception('bad'))
        self.assertIn('mycmd', err.stringify())

    def test_str(self):
        """Check str() handling."""
        # We don't assert much so we leave flexibility in changing format.
        err = rh.utils.RunCommandError('msg', self.result)
        self.assertIn('mycmd', str(err))
        err = rh.utils.RunCommandError('msg', self.result,
                                       exception=Exception('bad'))
        self.assertIn('mycmd', str(err))

    def test_repr(self):
        """Check repr() handling."""
        # We don't assert much so we leave flexibility in changing format.
        err = rh.utils.RunCommandError('msg', self.result)
        self.assertNotEqual('', repr(err))
        err = rh.utils.RunCommandError('msg', self.result,
                                       exception=Exception('bad'))
        self.assertNotEqual('', repr(err))

    def test_eq(self):
        """Check object equality."""
        # Note: We explicitly do not use assertEqual here.
        err1 = rh.utils.RunCommandError('msg', self.result)
        self.assertTrue(err1 == err1)
        err2 = rh.utils.RunCommandError('msg', self.result)
        self.assertTrue(err1 == err2)
        err3 = rh.utils.RunCommandError('foo', self.result)
        self.assertFalse(err1 == err3)

    def test_ne(self):
        """Check object inequality."""
        # Note: We explicitly do not use assertNotEqual here.
        err1 = rh.utils.RunCommandError('msg', self.result)
        self.assertFalse(err1 != err1)
        err2 = rh.utils.RunCommandError('msg', self.result)
        self.assertFalse(err1 != err2)
        err3 = rh.utils.RunCommandError('foo', self.result)
        self.assertTrue(err1 != err3)


# We shouldn't require sudo to run unittests :).
@mock.patch.object(rh.utils, 'run_command')
@mock.patch.object(os, 'geteuid', return_value=1000)
class SudoRunCommandTests(unittest.TestCase):
    """Verify behavior of sudo_run_command helper."""

    def test_run_as_root_as_root(self, mock_geteuid, mock_run):
        """Check behavior when we're already root."""
        mock_geteuid.return_value = 0
        ret = rh.utils.sudo_run_command(['ls'], user='root')
        self.assertIsNotNone(ret)
        args, _kwargs = mock_run.call_args
        self.assertEqual((['ls'],), args)

    def test_run_as_root_as_nonroot(self, _mock_geteuid, mock_run):
        """Check behavior when we're not already root."""
        ret = rh.utils.sudo_run_command(['ls'], user='root')
        self.assertIsNotNone(ret)
        args, _kwargs = mock_run.call_args
        self.assertEqual((['sudo', '--', 'ls'],), args)

    def test_run_as_nonroot_as_nonroot(self, _mock_geteuid, mock_run):
        """Check behavior when we're not already root."""
        ret = rh.utils.sudo_run_command(['ls'], user='nobody')
        self.assertIsNotNone(ret)
        args, _kwargs = mock_run.call_args
        self.assertEqual((['sudo', '-u', 'nobody', '--', 'ls'],), args)

    def test_env(self, _mock_geteuid, mock_run):
        """Check passing through env vars."""
        ret = rh.utils.sudo_run_command(['ls'], extra_env={'FOO': 'bar'})
        self.assertIsNotNone(ret)
        args, _kwargs = mock_run.call_args
        self.assertEqual((['sudo', 'FOO=bar', '--', 'ls'],), args)

    def test_shell(self, _mock_geteuid, _mock_run):
        """Check attempts to use shell code are rejected."""
        with self.assertRaises(AssertionError):
            rh.utils.sudo_run_command('foo')
        with self.assertRaises(AssertionError):
            rh.utils.sudo_run_command(['ls'], shell=True)


class RunCommandTests(unittest.TestCase):
    """Verify behavior of run_command helper."""

    def test_basic(self):
        """Simple basic test."""
        ret = rh.utils.run_command(['true'])
        self.assertEqual('true', ret.cmdstr)
        self.assertIsNone(ret.output)
        self.assertIsNone(ret.error)

    def test_stdout_capture(self):
        """Verify output capturing works."""
        ret = rh.utils.run_command(['echo', 'hi'], redirect_stdout=True)
        self.assertEqual('hi\n', ret.output)
        self.assertIsNone(ret.error)

    def test_stderr_capture(self):
        """Verify stderr capturing works."""
        ret = rh.utils.run_command(['sh', '-c', 'echo hi >&2'],
                                   redirect_stderr=True)
        self.assertIsNone(ret.output)
        self.assertEqual('hi\n', ret.error)

    def test_stdout_utf8(self):
        """Verify reading UTF-8 data works."""
        ret = rh.utils.run_command(['printf', r'\xc3\x9f'],
                                   redirect_stdout=True)
        self.assertEqual(u'ß', ret.output)
        self.assertIsNone(ret.error)

    def test_stdin_utf8(self):
        """Verify writing UTF-8 data works."""
        ret = rh.utils.run_command(['cat'], redirect_stdout=True, input=u'ß')
        self.assertEqual(u'ß', ret.output)
        self.assertIsNone(ret.error)


if __name__ == '__main__':
    unittest.main()
