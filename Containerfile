ARG silverblue_version=43
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version}

COPY overlay-root/ /

# Config for install Google Chrome
RUN mkdir -p /var/opt \
    && mkdir -p /usr/lib/opt/google \
    && ln -s /usr/lib/opt/google /var/opt/google \
    && echo 'L /opt/google - - - - /usr/lib/opt/google' > /usr/lib/tmpfiles.d/google-chrome.conf \
    && echo 'L /var/opt/google - - - - /usr/lib/opt/google' >> /usr/lib/tmpfiles.d/google-chrome.conf

# Install the packages
RUN --mount=type=bind,source=packages.toml,target=/packages.toml,z \
    --mount=type=bind,source=dnfdef.py,target=/dnfdef.py,z <<EOF 
set -xeuo pipefail
python3 /dnfdef.py
systemctl enable tailscaled 

# Remove leftover build artifacts from installing packages in the final built image.
dnf clean all
rm /var/{log,cache,lib}/* -rf

bootc container lint
EOF

# Define required labels for this bootc image to be recognized as such.
LABEL containers.bootc 1
LABEL ostree.bootable 1
# https://pagure.io/fedora-kiwi-descriptions/pull-request/52
ENV container=oci
# Optional labels that only apply when running this image as a container. These keep the default entry point running under systemd.
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
