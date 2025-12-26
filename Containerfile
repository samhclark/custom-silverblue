ARG silverblue_version=43
FROM quay.io/fedora-ostree-desktops/silverblue:${silverblue_version}

COPY overlay-root/ /

RUN mkdir -p /var/opt \
    && mkdir -p /usr/lib/opt/google \
    && ln -s /usr/lib/opt/google /var/opt/google \
    && echo 'L /opt/google - - - - ../../usr/lib/opt/google' > /usr/lib/tmpfiles.d/google-chrome.conf

RUN --mount=type=bind,source=packages.json,target=/packages.json,z \
    rpm -qa gpg-pubkey* --qf '%{NAME}-%{VERSION}-%{RELEASE} %{PACKAGER}\n' | grep 'linux-packages-keymaster@google.com' | sed 's/ .*$//' | xargs -r rpm -e \
    && rpm --import /etc/pki/rpm-gpg/google-linux-public-key.asc \
    && rpm --import /etc/pki/rpm-gpg/tailscale-public-key.asc \
    && rpm --import /etc/pki/rpm-gpg/microsoft-release-public-key.asc \
    # Temporary Fedora 43 RPM 6 workaround: disable repo GPG checks during rpm-ostree layering (see README).
    && sed -i 's/^gpgcheck=1/gpgcheck=0/' /etc/yum.repos.d/google-chrome.repo \
    && sed -i 's/^gpgcheck=1/gpgcheck=0/' /etc/yum.repos.d/tailscale.repo \
    && sed -i 's/^gpgcheck=1/gpgcheck=0/' /etc/yum.repos.d/vscode.repo \
    && sed -i 's/^repo_gpgcheck=1/repo_gpgcheck=0/' /etc/yum.repos.d/google-chrome.repo \
    && sed -i 's/^repo_gpgcheck=1/repo_gpgcheck=0/' /etc/yum.repos.d/tailscale.repo \
    && sed -i 's/^repo_gpgcheck=1/repo_gpgcheck=0/' /etc/yum.repos.d/vscode.repo \
    && rpm-ostree override remove \
        $(jq -r '"--install=\(.add[].name)"' /packages.json | paste -d" " -) \
        $(jq -r '.remove[].name' /packages.json | paste -d" " -) \
    && sed -i 's/^gpgcheck=0/gpgcheck=1/' /etc/yum.repos.d/google-chrome.repo \
    && sed -i 's/^gpgcheck=0/gpgcheck=1/' /etc/yum.repos.d/tailscale.repo \
    && sed -i 's/^gpgcheck=0/gpgcheck=1/' /etc/yum.repos.d/vscode.repo \
    && sed -i 's/^repo_gpgcheck=0/repo_gpgcheck=1/' /etc/yum.repos.d/google-chrome.repo \
    && sed -i 's/^repo_gpgcheck=0/repo_gpgcheck=1/' /etc/yum.repos.d/tailscale.repo \
    && sed -i 's/^repo_gpgcheck=0/repo_gpgcheck=1/' /etc/yum.repos.d/vscode.repo \
    && systemctl enable rpm-ostreed-automatic.timer \
    && systemctl enable tailscaled \
    && rpm-ostree cleanup --repomd

RUN ostree container commit
