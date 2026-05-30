#!/usr/bin/env bash

# Log in to Container Registry

set -euo pipefail

username="${1:-}"
registry="${2:-}"

log_info() {
    1>&2 echo "[INFO]: $*"
}

log_fatal_die() {
    1>&2 echo "[FATAL]: $*"
    exit 1
}

# Required parameters
if [ -z "$username" ] || [ -z "$registry" ]; then
  log_fatal_die "Usage: printf '%s' <password> | $0 <username> <registry>"
fi

if [ -t 0 ]; then
  log_fatal_die "Registry password must be provided on stdin."
fi

# Setup
log_info "Using $(podman -v)"

# Determine default podman auth file location
if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
  auth_file_dir="$XDG_RUNTIME_DIR"
else
  auth_file_dir="/tmp/podman-run-$(id -u)"
fi
podman_auth_file="${auth_file_dir}/containers/auth.json"

# Set environment variable for buildah
export REGISTRY_AUTH_FILE="$podman_auth_file"
echo "Exporting REGISTRY_AUTH_FILE=${podman_auth_file}"

podman login \
    --username "$username" \
    --password-stdin \
    --verbose \
    "$registry"

# Make sure Docker config directory exists
docker_config_dir="${HOME}/.docker"
mkdir -p "$docker_config_dir"
docker_config_path="${docker_config_dir}/config.json"

# Create Docker config if it doesn't exist
if [ ! -f "$docker_config_path" ]; then
  echo '{"auths":{}}' > "$docker_config_path"
fi

# Read Podman auth for this registry and add to Docker config
log_info "Writing registry credentials to ${docker_config_path}"
podman_auth=$(jq -c --arg registry "$registry" '.auths[$registry]' "$podman_auth_file")
if [ "$podman_auth" = "null" ]; then
  log_fatal_die "No Podman auth entry found for ${registry}"
fi
jq --arg registry "$registry" --argjson podman_auth "$podman_auth" '.auths[$registry] = $podman_auth' "$docker_config_path" > "${docker_config_path}.new"
mv "${docker_config_path}.new" "$docker_config_path"

log_info "Successfully logged in to ${registry} as ${username}"

exit 0
