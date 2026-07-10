"""Verify that every built distribution includes the project license texts."""

from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path
from zipfile import ZipFile

LICENSE_DIRECTORY = Path(__file__).parents[1] / "LICENSES"


def required_license_files() -> set[str]:
    """Return the license files required by the REUSE project convention."""
    license_files = {
        path.name for path in LICENSE_DIRECTORY.iterdir() if path.is_file()
    }
    if not license_files:
        msg = f"No license files found in {LICENSE_DIRECTORY}"
        raise ValueError(msg)
    return license_files


def archive_members(artifact: Path) -> list[str]:
    if artifact.suffix == ".whl":
        with ZipFile(artifact) as archive:
            return archive.namelist()

    if artifact.name.endswith(".tar.gz"):
        with tarfile.open(artifact) as archive:
            return archive.getnames()

    msg = f"Unsupported distribution artifact: {artifact}"
    raise ValueError(msg)


def missing_license_files(artifact: Path, required_files: set[str]) -> set[str]:
    members = archive_members(artifact)
    return {
        license_file
        for license_file in required_files
        if not any(member.endswith(f"LICENSES/{license_file}") for member in members)
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    required = required_license_files()

    for artifact in args.artifacts:
        missing = missing_license_files(artifact, required)
        if missing:
            names = ", ".join(sorted(missing))
            msg = f"{artifact} is missing required license files: {names}"
            raise SystemExit(msg)

        sys.stdout.write(f"{artifact}: required license files present\n")


if __name__ == "__main__":
    main()
