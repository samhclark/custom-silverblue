ARG silverblue_version=42
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version}

COPY overlay-root/ /

RUN mkdir -p /var/opt \
    && mkdir -p /usr/lib/opt/google \
    && ln -s /usr/lib/opt/google /var/opt/google \
    && echo 'L /opt/google - - - - ../../usr/lib/opt/google' > /usr/lib/tmpfiles.d/google-chrome.conf

RUN --mount=type=bind,source=packages.json,target=/packages.json,z \
    rpm --import /etc/pki/rpm-gpg/google-linux-public-key.asc \
    && rpm-ostree override remove \
        $(jq -r '"--install=\(.add[].name)"' /packages.json | paste -d" " -) \
        $(jq -r '.remove[].name' /packages.json | paste -d" " -) \
    && systemctl enable rpm-ostreed-automatic.timer \
    && rpm-ostree cleanup --repomd

RUN ostree container commit
