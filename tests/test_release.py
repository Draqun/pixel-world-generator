import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/release_version.py"


@pytest.fixture
def release_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    package = tmp_path / "src/pixel_world"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n')
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    (fragments / "+release.added.md").write_text("Add releases.\n")
    return tmp_path


def run_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=root, capture_output=True, text=True)


def test_release_version(release_repo: Path) -> None:
    result = run_check(release_repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0.1.0"


def test_rejects_version_mismatch(release_repo: Path) -> None:
    (release_repo / "src/pixel_world/__init__.py").write_text('__version__ = "0.2.0"\n')
    result = run_check(release_repo)
    assert result.returncode != 0
    assert "versions differ" in result.stderr


def test_rejects_existing_tag(release_repo: Path) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "Initial",
        ],
        cwd=release_repo,
        check=True,
    )
    subprocess.run(["git", "tag", "v0.1.0"], cwd=release_repo, check=True)
    result = run_check(release_repo)
    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_rejects_missing_fragments(release_repo: Path) -> None:
    (release_repo / "changelog.d/+release.added.md").unlink()
    result = run_check(release_repo)
    assert result.returncode != 0
    assert "No changelog fragments" in result.stderr


@pytest.mark.parametrize("version", ["1.2", "1.2.3rc1", "1.2.3\ninvalid"])
def test_rejects_invalid_version(release_repo: Path, version: str) -> None:
    (release_repo / "pyproject.toml").write_text(f"[project]\nversion = {version!r}\n")
    result = run_check(release_repo)
    assert result.returncode != 0
    assert "X.Y.Z" in result.stderr
