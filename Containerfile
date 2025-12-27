ARG silverblue_version=43
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version}

COPY overlay-root/ /

# Config for install Google Chrome
RUN mkdir -p /var/opt \
    && mkdir -p /usr/lib/opt/google \
    && ln -s /usr/lib/opt/google /var/opt/google \
    && echo 'L /opt/google - - - - ../../usr/lib/opt/google' > /usr/lib/tmpfiles.d/google-chrome.conf

# The rest of the packages
RUN --mount=type=bind,source=packages.toml,target=/packages.toml,z \
    --mount=type=bind,source=dnfdef.py,target=/dnfdef.py,z  \
    python3 /dnfdef.py \
    && systemctl enable tailscaled \
    && dnf list --installed
