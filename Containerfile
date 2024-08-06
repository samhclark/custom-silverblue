FROM quay.io/fedora-ostree-desktops/silverblue:40 as silverblue

RUN rpm-ostree override remove \
        gnome-software-rpm-ostree \
        gnome-terminal-nautilus \
        gnome-tour \
        firefox \
        firefox-langpacks \
    && rpm-ostree install \
        adw-gtk3-theme \
        bootc \
        distrobox \
        firewall-config \
        gnome-tweaks \
        ptyxis \
        wireguard-tools \
    && systemctl enable rpm-ostreed-automatic.timer \
    && systemctl enable flatpak-system-update.timer \
    && systemctl --global enable flatpak-user-update.timer \
    && rpm-ostree cleanup -m \
    && ostree container commit
