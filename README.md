# custom-silverblue

Following Jorge Castro's lead and making my own spin on Silverblue

## Google Linux Signing Keys

Google does something weird with their keys for signing RPMs.
They add new subkeys every year or so and start signing with that.
The subkey 
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