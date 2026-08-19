ARG silverblue_version=44
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version}

COPY overlay-root/ /
COPY secret-run/secret_run.py /usr/bin/secret-run
COPY secret-run/laptop-backup.sh /usr/bin/laptop-backup

# There are two pieces to getting GUI apps that use `/opt` to work on atomic distros, and
# note that the /opt -> /var/opt symlink already exists by default in the container image.
#
# 1. While building the bootc image, you need to have the /opt->/var/opt link set up so that when
#    the app installer tries to write to `/opt/foo` it gets written to `/usr` instead. It needs to 
#    be in /usr because (1) it's an executable and you want it on your immutable fs and (2) it needs
#    to get delivered to the end user. /var doesn't get shipped, but /usr and /etc do. 
#    So, the idea is that you create /var/opt and you create /usr/lib/opt/foo. Then YOU create (don't
#    let the installer do it) /var/opt/foo as a symlink to /usr/lib/opt/foo. 
#    The installer writes to /opt/foo (-> /var/opt/foo -> /usr/lib/opt/foo) and is none the wiser.
# 2. After the user boots the image, you gotta create that same symlink setup, because the installed 
#    program still expects to see /opt/foo. So you rely on systemd-tpmfiles here to create the files
#    for you at login. At login, systemd creates /opt/foo as a symlink to /usr/lib/opt/foo and it also
#    creates /var/opt/foo as a symlink to the same. 

# Google Chrome
RUN mkdir -p /var/opt \
    && mkdir -p /usr/lib/opt/google \
    && ln -s /usr/lib/opt/google /var/opt/google \
    && echo 'L /opt/google - - - - /usr/lib/opt/google' > /usr/lib/tmpfiles.d/google-chrome.conf \
    && echo 'L /var/opt/google - - - - /usr/lib/opt/google' >> /usr/lib/tmpfiles.d/google-chrome.conf

# Mullvad VPN GUI
RUN mkdir -p /var/opt \
    && mkdir -p '/usr/lib/opt/Mullvad VPN' \
    && ln -s '/usr/lib/opt/Mullvad VPN' '/var/opt/Mullvad VPN' \
    && echo 'L /opt/Mullvad\x20VPN - - - - /usr/lib/opt/Mullvad\x20VPN' > /usr/lib/tmpfiles.d/mullvad-vpn.conf \
    && echo 'L /var/opt/Mullvad\x20VPN - - - - /usr/lib/opt/Mullvad\x20VPN' >> /usr/lib/tmpfiles.d/mullvad-vpn.conf.conf

# 1Password GUI
RUN mkdir -p /var/opt && \
    mkdir -p /usr/lib/opt/1Password && \
    ln -s /usr/lib/opt/1Password /var/opt/1Password && \
    echo 'L /opt/1Password - - - - /usr/lib/opt/1Password' > /usr/lib/tmpfiles.d/1password.conf && \
    echo 'L /var/opt/1Password - - - - /usr/lib/opt/1Password' >> /usr/lib/tmpfiles.d/1password.conf.conf

# And 1Password adds some groups too
RUN printf 'g onepassword -\ng onepassword-mcp -\n' > /usr/lib/sysusers.d/1password.conf

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
