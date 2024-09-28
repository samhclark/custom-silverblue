ARG silverblue_version=40
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version}

COPY vscode.repo /etc/yum.repos.d/vscode.repo
COPY microsoft-release-public-key.asc /etc/pki/rpm-gpg/microsoft-release-public-key.asc

RUN --mount=type=bind,source=packages.json,target=/packages.json,z \
    rpm-ostree override remove \
        $(jq -r '"--install=\(.add[].name)"' /packages.json | xargs) \
        $(jq -r '.remove[].name' /packages.json | xargs) \
    && systemctl enable rpm-ostreed-automatic.timer \
    && rpm-ostree cleanup --repomd

RUN ostree container commit
