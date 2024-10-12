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
