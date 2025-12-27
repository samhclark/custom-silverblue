"""
Inspired by https://github.com/mogsor/dnfdef (GPL-3).

DNF layering flow for the container build:

1. Install configured groups (if any).
2. Install configured packages, honoring the exclude list.
3. Remove excluded packages explicitly.
4. Run autoremove to clean up now-unneeded dependencies.

Notes:
- DNF group install does not accept an exclude list, so exclusions are applied
  after group/package installs.
- The config file is packages.toml.
"""


# Setup
import pathlib
import subprocess
import sys
import tomllib

DNF = ["dnf", "--assumeyes"]


def run_cmd(args: list[str], step: str) -> None:
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"{step} failed.", file=sys.stderr)
        sys.exit(exc.returncode)


def read_config(path: pathlib.Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


config = read_config(pathlib.Path("packages.toml"))
groups = config.get("groups", [])
packages = config.get("packages", {})
packages_install = packages.get("install", [])
packages_exclude = packages.get("exclude", [])

exclude_arg = ["--exclude=" + ",".join(packages_exclude)] if packages_exclude else []


# Process

if groups:
    print("Installing groups...", flush=True)
    run_cmd(
        DNF + ["group", "install"] + groups,
        "Installing groups",
    )


if packages_install:
    print("Installing packages...", flush=True)
    run_cmd(
        DNF + ["install"] + packages_install + exclude_arg,
        "Installing packages",
    )

print("Removing excluded packages...", flush=True)

if packages_exclude:
    run_cmd(
        DNF
        + ["remove"]
        + packages_exclude
        + (["--exclude=" + ",".join(packages_install)] if packages_install else []),
        "Removing excluded packages",
    )

print("Running dnf autoremove...", flush=True)

run_cmd(DNF + ["autoremove"], "DNF autoremove")

print("Complete.", flush=True)
