FROM quay.io/fedora-ostree-desktops/silverblue:40 as silverblue

COPY docker-ce.repo /etc/yum.repos.d/docker-ce.repo
COPY vscode.repo /etc/yum.repos.d/vscode.repo
COPY custom-origin.yaml /etc/rpm-ostree/origin.d/custom-origin.yaml
COPY checksums /tmp/checksums

ADD https://desktop.docker.com/linux/main/amd64/160616/docker-desktop-x86_64.rpm /tmp/docker-desktop-x86_64.rpm 

RUN sha256sum -c checksums \
    && rpm-ostree ex rebuild \
    && rpm-ostree install --cache-only /tmp/docker-desktop-x86_64.rpm \
    && rm -f /tmp/docker-desktop-x86_64.rpm
    && systemctl enable rpm-ostreed-automatic.timer \
    && rpm-ostree cleanup -m \
    && ostree container commit
