ARG silverblue_version=44
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version}

COPY overlay-root/ /
COPY secret-run/secret_run.py /usr/bin/secret-run
COPY secret-run/laptop-backup.sh /usr/bin/laptop-backup

# Config for install Google Chrome
RUN mkdir -p /var/opt \
    && mkdir -p /usr/lib/opt/google \
    && ln -s /usr/lib/opt/google /var/opt/google \
    && echo 'L /opt/google - - - - /usr/lib/opt/google' > /usr/lib/tmpfiles.d/google-chrome.conf \
    && echo 'L /var/opt/google - - - - /usr/lib/opt/google' >> /usr/lib/tmpfiles.d/google-chrome.conf

    # Config for install Mullvad VPN GUI
RUN mkdir -p /var/opt \
    && mkdir -p '/usr/lib/opt/Mullvad VPN' \
    && ln -s '/usr/lib/opt/Mullvad VPN' '/var/opt/Mullvad VPN' \
    && echo 'L /opt/Mullvad\x20VPN - - - - /usr/lib/opt/Mullvad\x20VPN' > /usr/lib/tmpfiles.d/mullvad-vpn.conf \
    && echo 'L /var/opt/Mullvad\x20VPN - - - - /usr/lib/opt/Mullvad\x20VPN' >> /usr/lib/tmpfiles.d/mullvad-vpn.conf.conf

# Install the packages
# Copy up the SELinux policy store before package scriptlets modify it. Keeping
# the policy transaction in this layer avoids cross-layer rename failures.
RUN --mount=type=bind,source=packages.toml,target=/packages.toml,z \
    --mount=type=bind,source=dnfdef.py,target=/dnfdef.py,z \
    set -xeuo pipefail \
    && cp -a /etc/selinux/targeted /etc/selinux/targeted.rebuilt \
    && rm -rf /etc/selinux/targeted \
    && mv /etc/selinux/targeted.rebuilt /etc/selinux/targeted \
    && python3 /dnfdef.py \
    && systemctl enable tailscaled \
    && systemctl enable mullvad-early-boot-blocking \
    && systemctl enable mullvad-daemon \
    && dnf clean all \
    && rm /var/{log,cache,lib}/* -rf

RUN ["bootc", "container", "lint"]

# Define required labels for this bootc image to be recognized as such.
LABEL containers.bootc 1
LABEL ostree.bootable 1
# https://pagure.io/fedora-kiwi-descriptions/pull-request/52
ENV container=oci
# Optional labels that only apply when running this image as a container. These keep the default entry point running under systemd.
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
