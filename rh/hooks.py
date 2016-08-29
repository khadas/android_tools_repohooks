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

"""Functions that implement the actual checks."""

from __future__ import print_function

import json
import os
import re
import sys

_path = os.path.realpath(__file__ + '/../..')
if sys.path[0] != _path:
    sys.path.insert(0, _path)
del _path

import rh.results
import rh.git
import rh.utils


def _run_command(cmd, **kwargs):
    """Helper command for checks that tend to gather output."""
    kwargs.setdefault('redirect_stderr', True)
    kwargs.setdefault('combine_stdout_stderr', True)
    kwargs.setdefault('capture_output', True)
    kwargs.setdefault('error_code_ok', True)
    return rh.utils.run_command(cmd, **kwargs)


def _match_regex_list(subject, expressions):
    """Try to match a list of regular expressions to a string.

    Args:
      subject: The string to match regexes on.
      expressions: An iterable of regular expressions to check for matches with.

    Returns:
      Whether the passed in subject matches any of the passed in regexes.
    """
    for expr in expressions:
        if re.search(expr, subject):
            return True
    return False


def _filter_diff(diff, include_list, exclude_list=()):
    """Filter out files based on the conditions passed in.

    Args:
      diff: list of diff objects to filter.
      include_list: list of regex that when matched with a file path will cause
          it to be added to the output list unless the file is also matched with
          a regex in the exclude_list.
      exclude_list: list of regex that when matched with a file will prevent it
          from being added to the output list, even if it is also matched with a
          regex in the include_list.

    Returns:
      A list of filepaths that contain files matched in the include_list and not
      in the exclude_list.
    """
    filtered = []
    for d in diff:
        if (d.status != 'D' and
            _match_regex_list(d.file, include_list) and
            not _match_regex_list(d.file, exclude_list)):
            # We've got a match!
            filtered.append(d)
    return filtered


def _update_options(options, diff):
    """Update various place holders in |options| and return the new args."""
    ret = []
    for option in options:
        if option == '${PREUPLOAD_FILES}':
            ret.extend(x.file for x in diff if x.status != 'D')
        else:
            ret.append(option)
    return ret


# Where helper programs exist.
TOOLS_DIR = os.path.realpath(__file__ + '/../../tools')

def get_helper_path(tool):
    """Return the full path to the helper |tool|."""
    return os.path.join(TOOLS_DIR, tool)


def check_custom(project, commit, diff, options=()):
    """Run a custom hook."""
    cmd = _update_options(options, diff)
    return [rh.results.HookCommandResult(project, commit, _run_command(cmd))]


def check_cpplint(project, commit, diff, options=()):
    """Run cpplint."""
    if not options:
        options = ('${PREUPLOAD_FILES}',)

    # This list matches what cpplint expects.  We could run on more (like .cxx),
    # but cpplint would just ignore them.
    filtered = _filter_diff(diff, [r'\.(cc|h|cpp|cu|cuh)$'])
    if not filtered:
        return

    cmd = ['cpplint.py'] + _update_options(options, filtered)
    return check_custom(project, commit, diff, options=cmd)


def check_gofmt(project, commit, diff, options=()):
    """Checks that Go files are formatted with gofmt."""
    filtered = _filter_diff(diff, [r'\.go$'])
    if not filtered:
        return

    cmd = ['gofmt', '-l'] + _update_options(options, filtered)
    ret = []
    for d in filtered:
        data = rh.git.get_file_content(commit, d.file)
        result = _run_command(cmd, input=data)
        if result.output:
            ret.append(rh.results.HookResult(
                'gofmt', project, commit, error=result.output,
                files=(d.file,)))
    return ret


def check_json(project, commit, diff, options=()):
    """Verify json files are valid."""
    if options:
        raise ValueError('json check takes no options')

    filtered = _filter_diff(diff, [r'\.json$'])
    if not filtered:
        return

    ret = []
    for d in filtered:
        data = rh.git.get_file_content(commit, d.file)
        try:
            json.loads(data)
        except ValueError as e:
            ret.append(rh.results.HookResult(
                'json', project, commit, error=str(e),
                files=(d.file,)))
    return ret


def check_pylint(project, commit, diff, options=()):
    """Run pylint."""
    if not options:
        options = ('${PREUPLOAD_FILES}',)

    filtered = _filter_diff(diff, [r'\.py$'])
    if not filtered:
        return

    pylint = get_helper_path('pylint.py')
    cmd = [pylint] + _update_options(options, filtered)
    return check_custom(project, commit, diff, options=cmd)


def check_xmllint(project, commit, diff, options=()):
    """Run xmllint."""
    if not options:
        options = ('${PREUPLOAD_FILES}',)

    # XXX: Should we drop most of these and probe for <?xml> tags?
    extensions = frozenset((
        'dbus-xml',  # Generated DBUS interface.
        'dia',       # File format for Dia.
        'dtd',       # Document Type Definition.
        'fml',       # Fuzzy markup language.
        'form',      # Forms created by IntelliJ GUI Designer.
        'fxml',      # JavaFX user interfaces.
        'glade',     # Glade user interface design.
        'grd',       # GRIT translation files.
        'iml',       # Android build modules?
        'kml',       # Keyhole Markup Language.
        'mxml',      # Macromedia user interface markup language.
        'nib',       # OS X Cocoa Interface Builder.
        'plist',     # Property list (for OS X).
        'pom',       # Project Object Model (for Apache Maven).
        'sgml',      # Standard Generalized Markup Language.
        'svg',       # Scalable Vector Graphics.
        'uml',       # Unified Modeling Language.
        'vcproj',    # Microsoft Visual Studio project.
        'vcxproj',   # Microsoft Visual Studio project.
        'wxs',       # WiX Transform File.
        'xhtml',     # XML HTML.
        'xib',       # OS X Cocoa Interface Builder.
        'xlb',       # Android locale bundle.
        'xml',       # Extensible Markup Language.
        'xsd',       # XML Schema Definition.
        'xsl',       # Extensible Stylesheet Language.
    ))

    filtered = _filter_diff(diff, [r'\.(%s)$' % '|'.join(extensions)])
    if not filtered:
        return

    # TODO: Figure out how to integrate schema validation.
    # XXX: Should we use python's XML libs instead?
    cmd = ['xmllint'] + _update_options(options, filtered)
    return check_custom(project, commit, diff, options=cmd)


# Hooks that projects can opt into.
# Note: Make sure to keep the top level README.md up to date when adding more!
BUILTIN_HOOKS = {
    'cpplint': check_cpplint,
    'gofmt': check_gofmt,
    'jsonlint': check_json,
    'pylint': check_pylint,
    'xmllint': check_xmllint,
}
