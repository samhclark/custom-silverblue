#!/usr/bin/env bash

# Log in to Container Registry

username="$1"
password="$2"
registry="$3"

log_info() {
    1>&2 echo "[INFO]: $*"
}

# Setup
set -e
log_info "Using $(podman -v)"

podman login \
    --username "$username" \
    --password "$password" \
    "$registry"

log_info "Successfully logged in to $registry as $username"

exit 0