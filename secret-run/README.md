# secret-run

CLI tool that keeps secrets off disk in plaintext by sealing them with
`systemd-creds` (TPM + host key) and injecting them into processes as
environment variables at runtime.

## Threat Model

**In scope:**

- Supply-chain malware running as the user that scrapes well-known credential
  paths (`~/.aws/credentials`, `~/.ssh/id_*`, `~/.config/**`) and exfiltrates
  them.
- Disk compromise (stolen laptop, imaged disk) — sealed secrets are unreadable
  without the TPM and host key.

**Out of scope:**

- Root-level malware (can talk to the TPM directly).
- Runtime memory scraping (`/proc/<pid>/environ`, process memory dumps).
- Process execution hooking (intercepting secrets at injection time).
- Physical TPM attacks.

This raises the bar from "read a plaintext file" to "understand the unsealing
mechanism, hook the right process at the right time, and extract secrets from
memory." That defeats commodity credential-stealing malware.

## Usage

```bash
# Seal a new secret (prompts for value, no echo)
secret-run seal --profile aws-backup --var AWS_ACCESS_KEY_ID --name key-id

# Run a command with secrets injected as env vars
secret-run run --profile aws-backup -- aws s3 ls s3://my-bucket/

# AWS SDK credential_process integration (used in ~/.aws/config)
secret-run credential-process aws-backup

# List all profiles
secret-run list

# Verify all sealed creds in a profile can be decrypted
secret-run verify --profile aws-backup
```

### AWS SDK Integration

Set `credential_process` in `~/.aws/config` so the AWS SDK unseals credentials
on demand. No `~/.aws/credentials` file needed.

```ini
[profile nas-backup]
credential_process = /home/user/.local/bin/secret-run credential-process nas-backup
endpoint_url = https://nas.tailnet-name.ts.net:3900
region = garage
```

## Sealing a Secret

```bash
# Create the sealed creds directory (first time only)
mkdir -p ~/.local/share/sealed-creds

# Seal interactively
secret-run seal --profile myprofile --var MY_SECRET --name secret-name
# Prints a TOML snippet to paste into profiles.toml

# Or pipe from stdin
echo -n "the-secret-value" | secret-run seal \
  --profile myprofile --var MY_SECRET --name secret-name --stdin
```

After sealing, paste the printed snippet into your `profiles.toml`.

### Rotating a Secret

Re-run `seal` with the same `--profile`, `--var`, and `--name`. The `.cred`
file is overwritten. No config changes needed.

## File Layout

```
~/.config/secret-run/
  profiles.toml              # Profile definitions (which env vars, which .cred files)

~/.local/share/sealed-creds/
  {profile}.{name}.cred      # Sealed blobs (one per secret)

~/.aws/config                # credential_process references (no credentials file)
```

Config and data are separated per XDG conventions.

## Gotchas

**`systemd-creds --name` must match at decrypt time.** The credential name
embedded at encrypt time must be passed at decrypt time. Our filenames use the
convention `{profile}.{name}.cred`, but the `--name` is just `{name}`. The
tool handles this automatically, but if you're debugging manually, pass
`--name={name}` not the full filename.

**Renaming a profile doesn't require re-sealing.** The profile name is in the
`.cred` filename by convention, but `systemd-creds` only checks the `--name`
part. You can rename a profile in `profiles.toml` and keep pointing at the old
`.cred` files — they'll decrypt fine.

**`tomllib` is read-only.** `seal` prints a TOML snippet for you to paste
into `profiles.toml` manually. Python's stdlib has no TOML writer.

**Sealed secrets are machine-bound.** The `.cred` files are tied to this
machine's TPM and host key. If the machine is replaced, they're unrecoverable.
Keep a separate offline backup of the raw secret values (e.g., in a password
manager).
