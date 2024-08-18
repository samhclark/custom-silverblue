FROM quay.io/fedora-ostree-desktops/silverblue:40 as docker-desktop-rpm 
COPY checksums checksums
ADD https://desktop.docker.com/linux/main/amd64/160616/docker-desktop-x86_64.rpm docker-desktop-x86_64.rpm 
RUN sha256sum -c checksums

FROM quay.io/fedora-ostree-desktops/silverblue:40 as silverblue

COPY docker-ce.repo /etc/yum.repos.d/docker-ce.repo
COPY vscode.repo /etc/yum.repos.d/vscode.repo
COPY custom-origin.yaml /etc/rpm-ostree/origin.d/custom-origin.yaml

RUN rpm-ostree ex rebuild \
    && systemctl enable rpm-ostreed-automatic.timer

# Copying this pattern from here https://github.com/coreos/rpm-ostree/issues/233#issuecomment-1301194050
# There have been updates since this was written in Nov 2022 but as of July 2024, this is still the 
# recommended way https://github.com/coreos/fedora-coreos-tracker/issues/1681#issuecomment-2211137520 
COPY --from=docker-desktop-rpm docker-desktop-x86_64.rpm docker-desktop-x86_64.rpm
RUN mkdir /var/opt \
    && rpm -Uvh docker-desktop-x86_64.rpm \
    && mv /var/opt/docker-desktop /usr/lib/opt/docker-desktop \
    && echo 'L /opt/docker-desktop - - - - ../../usr/lib/opt/docker-desktop' > /usr/lib/tmpfiles.d/docker-desktop.conf \
    && rm -f docker-desktop-x86_64.rpm

RUN rpm-ostree cleanup -m \
    && ostree container commit
