#!/usr/bin/env bash
set -euo pipefail

system_config="${1:-/etc/containers/storage.conf}"
config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
user_config="${2:-${config_home}/containers/storage.conf}"

if [[ ! -r "${system_config}" ]]; then
    printf 'container storage config is not readable: %s\n' "${system_config}" >&2
    exit 1
fi

mapfile -t configured_drivers < <(
    sed -nE 's/^[[:space:]]*driver[[:space:]]*=[[:space:]]*"([^"]+)"[[:space:]]*$/\1/p' \
        "${system_config}"
)
if [[ "${#configured_drivers[@]}" -ne 1 ]]; then
    printf 'expected exactly one storage driver in %s\n' "${system_config}" >&2
    exit 1
fi
if [[ "${configured_drivers[0]}" != "overlay" && "${configured_drivers[0]}" != "vfs" ]]; then
    printf 'unsupported container storage driver: %s\n' "${configured_drivers[0]}" >&2
    exit 1
fi

mkdir -p "$(dirname "${user_config}")"
cp -- "${system_config}" "${user_config}"
sed -i -E \
    's/^[[:space:]]*driver[[:space:]]*=[[:space:]]*"(overlay|vfs)"[[:space:]]*$/driver = "vfs"/' \
    "${user_config}"

if [[ "$(grep -cFx 'driver = "vfs"' "${user_config}")" -ne 1 ]]; then
    printf 'failed to select VFS storage in %s\n' "${user_config}" >&2
    exit 1
fi

printf 'Buildah storage driver: vfs (%s)\n' "${user_config}"
