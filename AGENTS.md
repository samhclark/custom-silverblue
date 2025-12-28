# AGENTS.md

This file provides guidance to Codex CLI and other LLM agents when working in this repository.

## Project Overview

This repository builds a custom Fedora Silverblue (bootable container) image that is published to GitHub Container Registry. Package changes are applied via `dnf` during the container build (bootc-based workflow).

## Key Files

- `Containerfile`: Defines the Silverblue-based bootable container build.
- `packages.toml`: Source of truth for DNF package groups, installs, and removals.
- `dnfdef.py`: Applies the package config from `packages.toml` during the build.
- `overlay-root/`: Files copied into the image filesystem.
- `install-cosign.sh`: Helper for installing cosign locally.
- `log-in-to-registry.sh`: Helper for authenticating to GHCR.
- `README.md`: Rebase and signing instructions for consumers.

## Build & Publish Notes

- Use `podman` or `docker` to build. Example:
  `podman build -f Containerfile --build-arg silverblue_version=43 -t custom-silverblue .`
- `dnf` is the package manager inside the build; avoid `rpm-ostree`.
- Package changes should be made by editing `packages.toml` (and, if needed, `dnfdef.py`), not by modifying `Containerfile` directly.
- `bootc container lint` runs during the build; keep the image bootc-compatible.

## Development Guidelines

- Keep overlay changes in `overlay-root/` and ensure paths match the final filesystem layout.
- When adjusting packages, preserve the intent comments in `packages.toml`.
- Avoid introducing Unicode in new files unless already present.

## bootc Primer (Tips)

- Treat `/usr` as immutable at runtime; bootc bind-mounts it read-only.
- Only `/var` persists across upgrades; avoid relying on updates to existing `/var` files from new images.
- Standard writable paths are symlinks into `/var` (e.g. `/home` -> `/var/home`, `/opt` -> `/var/opt`).
- Use systemd `tmpfiles.d` or unit `StateDirectory=` to seed `/var` content on first boot.
- Prefer packaging static content into `/usr`; avoid dropping mutable content into `/var` during image builds.

## Testing & Verification

- There are no automated tests. Verify by building the container and, if needed, rebasing onto it in a Silverblue environment per `README.md`.
