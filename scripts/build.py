import os
from dataclasses import dataclass
from itertools import chain
import argparse
from typing import Any
from argparse import ArgumentParser
import tomllib
from pathlib import Path
import re
import subprocess
import sys

@dataclass(frozen=True)
class ProjectInfo:
    name: str
    version: str

def path_deps(project_dir: Path) -> dict[str, Path]:
    data = tomllib.loads((project_dir / "pyproject.toml").read_text())
    deps: dict[str, Any] = data.get("tool", {}).get("poetry", {}).get("dependencies", {})

    return {
        name: (project_dir / dep["path"]).resolve()
        for name, dep in deps.items()
        if isinstance(dep, dict) and "path" in dep
    }

def project_info(project_dir: Path) -> ProjectInfo:
    data = tomllib.loads((project_dir / "pyproject.toml").read_text())
    project = data["project"]
    return ProjectInfo(name = project["name"], version = project["version"])

def recursive_path_deps(project_dir: Path) -> dict[str, Path]:
    direct_deps = path_deps(project_dir)
    all_deps = direct_deps.copy()

    for dep_path in direct_deps.values():
        all_deps.update(recursive_path_deps(dep_path))

    return all_deps

def wheel_exists(wheelhouse: Path, info: ProjectInfo) -> bool:
    normalized = info.name.replace("-", "_")
    pattern = re.compile(
        rf"{normalized}-{re.escape(info.version)}-.*\.whl"
    )

    return any(pattern.match(p.name) for p in wheelhouse.iterdir())

def main():
    poetry_path = Path(os.environ["APPDATA"]) / "Python/Scripts/poetry.exe"
    if not poetry_path.is_file() and poetry_path.exists():
        raise RuntimeError(f"Error: Poetry executable not found at expected location: {poetry_path!r}")

    argparse = ArgumentParser(description="Builds specified bots and their dependencies (if they were not yet updated).")
    argparse.add_argument(
        "bots",
        type=str,
        nargs="+",
    )
    argparse.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Directory where built wheels will be stored (default: wheelhouse)",
    )

    args = argparse.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    bot_folders = [Path(f"packages/bots/{bot}").resolve() for bot in args.bots]

    for bot_folder in bot_folders:
        if not bot_folder.is_dir() or not (bot_folder / "pyproject.toml").is_file():
            raise RuntimeError(f"Error: Bot folder '{bot_folder}' does not exist or does not contain a pyproject.toml file.")
        bot_project_info = project_info(bot_folder)
        if wheel_exists(args.output, bot_project_info):
            print(f"Wheel for bot {bot_project_info.name}==\"{bot_project_info.version}\" already exists, skipping build.")
            bot_folders.remove(bot_folder)

    path_deps_to_build: set[Path] = set()

    for bot_folder in bot_folders:
        for path in recursive_path_deps(bot_folder).values():
            info = project_info(path)
            if wheel_exists(args.output, info):
                print(f"Wheel for dependency {info.name}==\"{info.version}\" already exists, skipping build.")
            else:
                path_deps_to_build.add(path)


    for dep_path in path_deps_to_build:
        subprocess.run([poetry_path.as_posix(), "-C", dep_path.resolve().as_posix(), "build", "-f", "wheel", "-o", args.output.resolve().as_posix()], check=True)

    for bot_folder in bot_folders:
        subprocess.run([poetry_path.as_posix(), "-C", bot_folder.resolve().as_posix(), "build", "-f", "wheel", "-o", args.output.resolve().as_posix()], check=True)
   
if __name__ == "__main__":
    main()