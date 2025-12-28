# custom-silverblue

Following Jorge Castro's lead and making my own spin on Silverblue

[![Build bootc image](https://github.com/samhclark/custom-silverblue/actions/workflows/build.yaml/badge.svg)](https://github.com/samhclark/custom-silverblue/actions/workflows/build.yaml)

## Rebasing onto this image

This bootstrapping process helps get the public keys onto your machine 
and makes sure everything is configured right. 

From another Silverblue based image, first, rebase onto the _unverified_ image.

```
sudo bootc switch ghcr.io/samhclark/custom-silverblue:43
```

Optional: Manually verify that the image you just rebased onto is signed.

```
$ wget -O - https://raw.githubusercontent.com/samhclark/custom-silverblue/refs/heads/main/overlay-root/usr/etc/pki/cosign/cosign.pub \
    | cosign verify --key /dev/stdin ghcr.io/samhclark/custom-silverblue@$( \
        sudo bootc status --json | jq '.status.staged.image.iamgeDigest'
    )
```

If the above command fails (returns with a non-zero exit code), then you should abort the rebase

```
sudo bootc rollback
```

Assuming it succeeded, then reboot: `systemctl reboot`.
After that, rebase onto the signed image. 

```
sudo bootc switch --enforce-container-sigpolicy ghcr.io/samhclark/custom-silverblue:43
```

## Google Linux Signing Keys

Google does something weird with their keys for signing RPMs.
They add new subkeys every year or so and start signing with that.
When things start breaking eventually, get the new key with:

```
wget -O overlay-root/etc/pki/rpm-gpg/google-linux-public-key.asc https://dl.google.com/linux/linux_signing_key.pub
```

## Cosign Signing Keys

The resulting container images are signed by Cosign.
The keys were generated with the following command:

```
$ GITHUB_TOKEN="$(gh auth token)" COSIGN_PASSWORD="$(head -c 33 /dev/urandom | base64)" cosign generate-key-pair github://samhclark/custom-silverblue --output-file cosign.pub
Password written to COSIGN_PASSWORD github actions secret
Private key written to COSIGN_PRIVATE_KEY github actions secret
Public key written to COSIGN_PUBLIC_KEY github actions secret
Public key also written to cosign.pub
```

The key is included in the image at `/etc/pki/cosign/cosign.pub`. 
You can also download the key with:

```
wget https://raw.githubusercontent.com/samhclark/custom-silverblue/refs/heads/main/cosign.pub
```

The SHA-256 checksum of the key that I originally created on October 18, 2024 is

```
$ sha256sum cosign.pub 
55e391488bbbfe28209e09963edf38a612e306572b2dd72bbcc97402690ff000  cosign.pub
```

