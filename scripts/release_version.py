"""Validate release prerequisites before changing any tracked files."""

import re
import runpy
import subprocess
import tomllib
from pathlib import Path


def main() -> None:
    with Path("pyproject.toml").open("rb") as config:
        version = tomllib.load(config)["project"]["version"]
    if re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version) is None:
        raise SystemExit("Release version must have the form X.Y.Z")
    generator_version = runpy.run_path("src/pixel_world/__init__.py")["__version__"]
    if version != generator_version:
        raise SystemExit("Project and generator versions differ")
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/v{version}"], check=False
    )
    if result.returncode == 0:
        raise SystemExit(f"Tag v{version} already exists")
    if result.returncode != 1:
        raise SystemExit("Could not check existing release tags")
    fragments = [
        fragment
        for category in ("added", "changed", "fixed", "removed")
        for fragment in Path("changelog.d").glob(f"*.{category}.md")
        if fragment.read_text().strip()
    ]
    if not fragments:
        raise SystemExit("No changelog fragments to release")
    print(version)


if __name__ == "__main__":
    main()
