ARG silverblue_version=40
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version} as silverblue

COPY docker-ce.repo /etc/yum.repos.d/docker-ce.repo
COPY docker-release-public-key.asc /etc/pki/rpm-gpg/docker-release-public-key.asc
COPY vscode.repo /etc/yum.repos.d/vscode.repo
COPY microsoft-release-public-key.asc /etc/pki/rpm-gpg/microsoft-release-public-key.asc

ADD https://desktop.docker.com/linux/main/amd64/160616/docker-desktop-x86_64.rpm /docker-desktop-x86_64.rpm
RUN --mount=type=bind,source=checksums,target=/checksums,z sha256sum -c checksums

# Copying the pattern for installing Docker Desktop from here
# https://github.com/coreos/rpm-ostree/issues/233#issuecomment-1301194050
# There have been updates since this was written in Nov 2022 but as of July 2024, this is still the
# recommended way https://github.com/coreos/fedora-coreos-tracker/issues/1681#issuecomment-2211137520
RUN --mount=type=bind,source=packages.json,target=/packages.json,z \
    rpm-ostree override remove \
        $(jq -r '"--install=\(.add[].name)"' /packages.json | xargs) \
        $(jq -r '.remove[].name' /packages.json | xargs) \
    && systemctl enable rpm-ostreed-automatic.timer \
    && mkdir /var/opt \
    && rpm -Uvh docker-desktop-x86_64.rpm \
    && mv /var/opt/docker-desktop /usr/lib/opt/docker-desktop \
    && echo 'L /opt/docker-desktop - - - - ../../usr/lib/opt/docker-desktop' > /usr/lib/tmpfiles.d/docker-desktop.conf \
    && rpm-ostree cleanup --repomd

RUN ostree container commit
