"""
Tests for shared/infrastructure/version_compatibility.py

This module is the gate on the front door of every workfile. workfile/
CLAUDE.md: "A workfile whose file version id is not in this build's readable
list is refused at Open. No partial read, no migration attempt."

The rule that most needs pinning is the treatment of a missing version. The
docstring says an empty or absent file_version_id "is treated as
incompatible, not assumed safe -- it hasn't been through this check before".
The tempting change is to let a blank through as "probably an old file, and
old files were fine". That would hand a partially-understood workfile to the
rest of the application, which is exactly what refusing at the door exists
to prevent.

These tests read the real version_compatibility.csv rather than a stand-in,
so they also assert the file itself stays well-formed.
"""

from chartgen.shared.infrastructure.version_compatibility import (
    get_file_version_written,
    get_file_versions_readable,
    get_software_id,
    is_file_version_compatible,
)


# ---------------------------------------------------------------------------
# The reference file is readable and holds all three values
# ---------------------------------------------------------------------------

def test_the_build_reports_a_software_id():
    assert get_software_id().strip() != ""


def test_the_build_reports_the_file_version_it_writes():
    assert get_file_version_written().strip() != ""


def test_the_build_reports_at_least_one_readable_file_version():
    assert len(get_file_versions_readable()) >= 1


def test_the_readable_list_has_no_blank_entries():
    """
    file_versions_readable is a semicolon-delimited list, so a trailing
    semicolon would otherwise produce an empty entry -- and an empty entry
    would make is_file_version_compatible("") return True, defeating the
    missing-version rule below.
    """
    assert all(v.strip() for v in get_file_versions_readable())


# ---------------------------------------------------------------------------
# The two versions are independent of each other
# ---------------------------------------------------------------------------

def test_the_software_id_and_the_file_version_are_separate_numbers():
    """
    The module exists to keep these apart: a build can be released without
    changing the .cgw structure, and vice versa. Nothing should make one
    derive from the other.
    """
    software = get_software_id()
    file_version = get_file_version_written()
    assert isinstance(software, str) and isinstance(file_version, str)
    # Independent values, not the same field read twice under two names.
    assert get_software_id() == software
    assert get_file_version_written() == file_version


# ---------------------------------------------------------------------------
# The compatibility gate
# ---------------------------------------------------------------------------

def test_this_build_can_open_what_it_writes():
    """
    If this ever fails, ChartGen cannot reopen a workfile it just saved.
    """
    assert is_file_version_compatible(get_file_version_written()) is True


def test_every_version_on_the_readable_list_is_accepted():
    for version in get_file_versions_readable():
        assert is_file_version_compatible(version) is True


def test_an_unknown_version_is_refused():
    assert is_file_version_compatible("99.99.99") is False


def test_a_missing_version_is_refused_rather_than_assumed_safe():
    """
    The documented rule. A workfile predating the field has not been through
    this check before, so it is not known to be readable.
    """
    assert is_file_version_compatible("") is False
    assert is_file_version_compatible(None) is False


def test_a_version_is_matched_exactly_and_not_by_prefix():
    """
    "0.0.4" must not admit "0.0.40". Loose matching here would let a future
    format in through a build that cannot read it.
    """
    written = get_file_version_written()
    assert is_file_version_compatible(written + "0") is False
