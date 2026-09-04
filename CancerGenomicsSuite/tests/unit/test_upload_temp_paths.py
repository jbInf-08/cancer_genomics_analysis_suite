"""An uploaded filename must not choose where the file is written.

Both dashboard upload handlers built their temp path by interpolation:

    temp_file = f"temp_{filename}"
    with open(temp_file, "wb") as f: ...
    os.remove(temp_file)

`filename` comes from a dcc.Upload component, so it is whatever the client
sent. "../../x" walks out of the working directory on the write and again on
the remove, and on Windows a name like "C:/x" is absolute outright.

The handlers are Dash callbacks closed over `self`, which makes them awkward to
call directly. These tests pin the two properties the fix rests on instead: the
path now comes from tempfile, and the only thing still taken from the upload is
an extension checked against a fixed set.
"""

from __future__ import annotations

import ast
import io
import os
import pathlib
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
HANDLERS = {
    "tree_dash": REPO / "modules" / "phylogenetic_tree_viewer" / "tree_dash.py",
    "search_dash": REPO / "modules" / "sequence_search_tool" / "search_dash.py",
}


@pytest.mark.parametrize("name", sorted(HANDLERS))
def test_temp_path_is_not_built_from_the_uploaded_filename(name):
    """No f-string interpolating `filename` may be assigned to temp_file.

    Checked over the AST, not the text: the comments in these files quote the
    old `f"temp_{filename}"` to explain the fix, and a substring search would
    match its own explanation.
    """
    tree = ast.parse(io.open(HANDLERS[name], encoding="utf-8").read())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if "temp_file" not in targets:
            continue
        names = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
        if "filename" in names:
            offenders.append(ast.unparse(node))
    assert not offenders, f"temp_file built from the upload filename: {offenders}"


@pytest.mark.parametrize("name", sorted(HANDLERS))
def test_temp_path_comes_from_tempfile(name):
    source = io.open(HANDLERS[name], encoding="utf-8").read()
    assert "tempfile.mkstemp(" in source, "the temp path should be chosen by tempfile"
    assert "os.fdopen(" in source, "mkstemp returns an fd; it has to be closed"


@pytest.mark.parametrize("name", sorted(HANDLERS))
def test_temp_file_is_removed_even_when_loading_raises(name):
    """The remove moved into a finally, so a loader error cannot leak the file."""
    tree = ast.parse(io.open(HANDLERS[name], encoding="utf-8").read())
    removes_in_finally = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        and node.finalbody
        and "os.remove(temp_file)" in ast.unparse(ast.Module(node.finalbody, []))
    ]
    assert removes_in_finally, "os.remove(temp_file) should sit in a finally block"


# The behaviour the fix relies on, pinned directly rather than assumed.


@pytest.mark.parametrize(
    "hostile",
    [
        "../../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "/etc/passwd",
        "subdir/nested.fasta",
    ],
)
def test_suffix_extraction_keeps_nothing_but_an_extension(hostile):
    """This is what tree_dash derives from the upload -- and all it derives."""
    suffix = os.path.splitext(os.path.basename(hostile))[1].lower()
    assert "/" not in suffix and "\\" not in suffix
    assert ".." not in suffix


def test_only_whitelisted_suffixes_survive_the_check():
    allowed = {".fasta", ".fa", ".phylip", ".clustal"}
    for hostile in ["../../../etc/passwd", "x.sh", "x.py", ""]:
        suffix = os.path.splitext(os.path.basename(hostile))[1].lower()
        assert suffix not in allowed, f"{hostile!r} should be rejected"
    for ok in ["align.fasta", "ALIGN.FA", "d/e/f/x.phylip"]:
        suffix = os.path.splitext(os.path.basename(ok))[1].lower()
        assert suffix in allowed, f"{ok!r} should be accepted"


def test_mkstemp_path_stays_inside_the_temp_directory():
    """Whatever suffix is passed, the directory is tempfile's, not the caller's."""
    fd, path = tempfile.mkstemp(suffix=".fasta")
    try:
        assert pathlib.Path(path).parent == pathlib.Path(tempfile.gettempdir())
    finally:
        os.close(fd)
        os.remove(path)


def test_the_old_construction_really_did_escape():
    """Document why this mattered, so the fix is not mistaken for cosmetics."""
    escaped = f"temp_{'../../../etc/passwd'}"
    assert ".." in escaped
    # Resolved against a working directory, it lands outside it.
    base = pathlib.Path("/srv/app").resolve()
    assert base not in (base / escaped).resolve().parents
