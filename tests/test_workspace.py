import pytest

from agentpath.tools.workspace import WorkspaceError, resolve_inside


def test_normal_path_resolves(tmp_path):
    target = resolve_inside(tmp_path, "notes.txt")
    assert target == (tmp_path / "notes.txt").resolve()


def test_subdirectory_is_allowed(tmp_path):
    (tmp_path / "src").mkdir()
    assert resolve_inside(tmp_path, "src/main.py").name == "main.py"


def test_parent_escape_is_refused(tmp_path):
    with pytest.raises(WorkspaceError, match="outside the workspace"):
        resolve_inside(tmp_path, "../secrets.txt")


def test_absolute_path_outside_is_refused(tmp_path):
    outside = tmp_path.parent / "elsewhere.txt"
    with pytest.raises(WorkspaceError, match="outside the workspace"):
        resolve_inside(tmp_path / "inner", str(outside))


@pytest.mark.parametrize(
    "name", [".env", ".env.local", "id_rsa", "server.pem", "secret.key", ".npmrc"]
)
def test_secret_files_are_refused(tmp_path, name):
    with pytest.raises(WorkspaceError, match="refuses to touch"):
        resolve_inside(tmp_path, name)


def test_a_file_merely_containing_env_is_fine(tmp_path):
    assert resolve_inside(tmp_path, "environment.md").name == "environment.md"
