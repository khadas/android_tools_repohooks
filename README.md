# AOSP Presubmit Hooks

[TOC]

This repo holds hooks that get run by repo during the upload phase.  They
perform various checks automatically such as running linters on your code.

Note: Currently all hooks are disabled by default.  Each repo must explicitly
turn on any hook it wishes to enforce.

## Usage

Normally these execute automatically when you run `repo upload`.  If you want to
run them by hand, you can execute `pre-upload.py` directly.  By default, that
will scan the active repo and process all commits that haven't yet been merged.
See its help for more info.

### Bypassing

Sometimes you might want to bypass the upload checks.  While this is **strongly
discouraged** (often failures you add will affect others and block them too),
sometimes there are valid reasons for this.  You can simply use the option
`--no-verify` when running `repo upload` to skip all upload checks.  This will
skip **all** checks and not just specific ones.  It should be used only after
having run & evaluated the upload output previously.

# Config Files

These files are checked in the top of a specific git repository.  Stacking
them in subdirectories (to try and override parent settings) is not supported.

## PREUPLOAD.cfg

This file controls the hooks/checks that get run when running `repo upload`.

### Example

```
[Hook Scripts]
name = script --with args ${PREUPLOAD_FILES}

[Builtin Hooks]
cpplint = true

[Builtin Hooks Options]
cpplint = --filter=-x ${PREUPLOAD_FILES}
```

### Environment

Hooks are executed in the top directory of the git repository.  All paths should
generally be relative to that point.

A few environment variables are set so scripts don't need to discover things.

* `REPO_PROJECT`: The name of the project.
   e.g. `platform/tools/repohooks`
* `REPO_PATH`: The path to the project relative to the root.
   e.g. `tools/repohooks`
* `REPO_REMOTE`: The remote git URL.
   e.g. `https://android.googlesource.com/platform/tools/repohooks`
* `PREUPLOAD_COMMIT`: The commit that is currently being checked.
   e.g. `1f89dce0468448fa36f632d2fc52175cd6940a91`

### `[Hook Scripts]`

This section allows for completely arbitrary hooks to run on a per-repo basis.

The key can be any name (as long as the syntax is valid), as can the program
that is executed.

```
[Hook Scripts]
my_first_hook = program --gogog ${PREUPLOAD_FILES}
another_hook = funtimes --i-need "some space" ${PREUPLOAD_FILES}
some_fish = linter --ate-a-cat ${PREUPLOAD_FILES}
some_cat = formatter --cat-commit ${PREUPLOAD_COMMIT}
some_dog = tool --no-cat-in-commit-message ${PREUPLOAD_COMMIT_MESSAGE}
```

### `[Builtin Hooks]`

This section allows for turning on common/builtin hooks.  There are a bunch of
canned hooks already included geared towards AOSP style guidelines.

* `checkpatch`: Run commits through the Linux kernel's `checkpatch.pl` script.
* `commit_msg_bug_field`: Require a valid `Bug:` line.
* `commit_msg_changeid_field`: Require a valid `Change-Id:` Gerrit line.
* `commit_msg_test_field`: Require a `Test:` line.
* `cpplint`: Run through the cpplint tool (for C++ code).
* `gofmt`: Run Go code through `gofmt`.
* `jsonlint`: Verify JSON code is sane.
* `pylint`: Run Python code through `pylint`.
* `xmllint`: Run XML code through `xmllint`.

Note: Builtin hooks tend to match specific filenames (e.g. `.json`).  If no
files match in a specific commit, then the hook will be skipped for that commit.

```
[Builtin Hooks]
# Turn on cpplint checking.
cpplint = true
# Turn off gofmt checking.
gofmt = false
```

### `[Builtin Hooks Options]`

Used to customize the behavior of specific `[Builtin Hooks]`.  Any arguments set
here will be passed directly to the linter in question.  This will completely
override any existing default options, so be sure to include everything you need
(especially `${PREUPLOAD_FILES}` -- see below).

Quoting is handled naturally.  i.e. use `"a b c"` to pass an argument with
whitespace.

A few keywords are recognized to pass down settings.  These are **not**
environment variables, but are expanded inline.  Files with whitespace and
such will be expanded correctly via argument positions, so do not try to
force your own quote handling.

* `${PREUPLOAD_FILES}`: List of files to operate on.
* `${PREUPLOAD_COMMIT}`: Commit hash.
* `${PREUPLOAD_COMMIT_MESSAGE}`: Commit message.

```
[Builtin Hooks Options]
# Pass more filter args to cpplint.
cpplint = --filter=-x ${PREUPLOAD_FILES}
```

# Hook Developers

These are notes for people updating the `pre-upload.py` hook itself:

* Don't worry about namespace collisions.  The `pre-upload.py` script is loaded
  and exec-ed in its own context.  The only entry-point that matters is `main`.
* New hooks can be added in `rh/hooks.py`.  Be sure to keep the list up-to-date
  with the documentation in this file.

## TODO/Limitations

* `pylint` should support per-repo pylintrc files.
* Some checkers operate on the files as they exist in the filesystem.  This is
  not easy to fix because the linters require not just the modified file but the
  entire repo in order to perform full checks.  e.g. `pylint` needs to know what
  other modules exist locally to verify their API.  We can support this case by
  doing a full checkout of the repo in a temp dir, but this can slow things down
  a lot.  Will need to consider a `PREUPLOAD.cfg` knob.
* We need to add `cpplint` and `pylint` tools to the AOSP manifest and use those
  local copies instead of relying on versions that are in $PATH.
* Should make file extension filters configurable.  All hooks currently declare
  their own list of files like `.cc` and `.py` and `.xml`.
* Add more checkers.
  * `clang-format`: Checks style/formatting of code.
  * `clang-check`: Runs static analyzers against code.
  * License checking (like require AOSP header).
  * Whitespace checking (trailing/tab mixing/etc...).
  * Long line checking.
  * Commit message checks (correct format/BUG/TEST/SOB tags/etc...).
  * Markdown (gitiles) validator.
  * Spell checker.
