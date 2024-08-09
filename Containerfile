FROM quay.io/fedora-ostree-desktops/silverblue:40 as silverblue

RUN echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" \
        | sudo tee /etc/yum.repos.d/vscode.repo > /dev/null \
    && rpm-ostree override remove \
        gnome-software-rpm-ostree \
        gnome-terminal \
        gnome-terminal-nautilus \
        gnome-tour \
        firefox \
        firefox-langpacks \
    && rpm-ostree install --idempotent \
        adw-gtk3-theme \
        bootc \
        code \
        distrobox \
        firewall-config \
        gnome-tweaks \
        ptyxis \
        wireguard-tools \
    && systemctl enable rpm-ostreed-automatic.timer \
    && rpm-ostree cleanup -m \
    && ostree container commit
