FROM quay.io/fedora-ostree-desktops/silverblue:40 as silverblue

COPY vscode.repo /etc/yum.repos.d/vscode.repo
COPY custom-origin.yaml /etc/rpm-ostree/origin.d/custom-origin.yaml

RUN rpm-ostree ex rebuild
    && systemctl enable rpm-ostreed-automatic.timer \
    && rpm-ostree cleanup -m \
    && ostree container commit
