#!/usr/bin/env python3
# ABOUTME: CLI tool that seals secrets via systemd-creds (TPM + host key).
# Secrets are stored as encrypted blobs on disk and injected into processes
# as environment variables at runtime. This keeps credentials off disk in
# plaintext, defeating commodity supply-chain malware that scrapes well-known
# paths like ~/.aws/credentials. See README.md for threat model details.

import argparse
import getpass
import json
import os
import pathlib
import subprocess
import sys
import tomllib

XDG_CONFIG_HOME = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config"))
XDG_DATA_HOME = pathlib.Path(os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share"))

SEALED_CREDS_DIR = XDG_DATA_HOME / "sealed-creds"
PROFILES_TOML = XDG_CONFIG_HOME / "secret-run" / "profiles.toml"


def cred_path(base: pathlib.Path, profile: str, name: str) -> pathlib.Path:
    return base / f"{profile}.{name}.cred"


def toml_snippet(profile: str, var: str, cred_filename: str) -> str:
    return (
        f"[profiles.{profile}.env]\n"
        f'{var} = "{cred_filename}"'
    )


def build_encrypt_command(name: str, output_path: pathlib.Path) -> list[str]:
    # tpm2+host binds to both TPM and host key. --user scopes to the user's
    # keyring, avoiding the PAM password prompt that --with-key=tpm2 alone
    # triggers on every encrypt/decrypt.
    return [
        "systemd-creds", "encrypt",
        "--with-key=tpm2+host",
        "--user",
        f"--name={name}",
        "-",
        str(output_path),
    ]


def seal(profile: str, var: str, name: str, from_stdin: bool = False) -> str:
    SEALED_CREDS_DIR.mkdir(parents=True, exist_ok=True)

    if from_stdin:
        secret = sys.stdin.read().rstrip("\n")
    else:
        secret = getpass.getpass(prompt=f"Enter secret value for {var}: ")
    if not secret:
        print("Error: empty secret provided.", file=sys.stderr)
        sys.exit(1)

    out = cred_path(SEALED_CREDS_DIR, profile, name)
    cmd = build_encrypt_command(name, out)

    subprocess.run(cmd, input=secret.encode(), check=True)

    # tomllib is read-only, so we can't auto-update profiles.toml.
    # Print a snippet for the user to paste manually.
    filename = out.name
    snippet = toml_snippet(profile, var, filename)
    return snippet


def cred_name_from_filename(filename: str) -> str:
    """Extract the credential name from a .cred filename.

    The convention is {profile}.{name}.cred, and the --name used at seal
    time is just {name}. systemd-creds requires --name at decrypt time to
    match what was used at encrypt time, so we must extract it from the
    filename rather than passing the full filename.
    """
    parts = filename.removesuffix(".cred").split(".", maxsplit=1)
    return parts[1] if len(parts) > 1 else parts[0]


def build_decrypt_command(cred_file: pathlib.Path) -> list[str]:
    name = cred_name_from_filename(cred_file.name)
    return [
        "systemd-creds", "decrypt",
        "--user",
        f"--name={name}",
        str(cred_file),
        "-",
    ]


def decrypt_credential(cred_file: pathlib.Path) -> str:
    cmd = build_decrypt_command(cred_file)
    result = subprocess.run(cmd, check=True, capture_output=True)
    return result.stdout.decode()


def load_profile(profile_name: str, toml_str: str) -> dict:
    config = tomllib.loads(toml_str)
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        print(f"Error: profile '{profile_name}' not found in profiles.toml.", file=sys.stderr)
        sys.exit(1)
    profile = profiles[profile_name]
    return {
        "env": profile.get("env", {}),
        "env-literal": profile.get("env-literal", {}),
    }


def build_run_env(
    base_env: dict[str, str],
    sealed_env: dict[str, str],
    literal_env: dict[str, str],
    creds_dir: pathlib.Path,
) -> dict[str, str]:
    env = dict(base_env)
    for var, cred_filename in sealed_env.items():
        env[var] = decrypt_credential(creds_dir / cred_filename)
    for var, value in literal_env.items():
        env[var] = value
    return env


def run_profile(profile_name: str, cmd: list[str]) -> None:
    toml_text = PROFILES_TOML.read_text()
    profile = load_profile(profile_name, toml_text)
    env = build_run_env(
        base_env=dict(os.environ),
        sealed_env=profile["env"],
        literal_env=profile["env-literal"],
        creds_dir=SEALED_CREDS_DIR,
    )
    # exec replaces this process, so no parent lingers holding secrets.
    os.execvpe(cmd[0], cmd, env)


def build_credential_process_json(access_key_id: str, secret_access_key: str) -> str:
    return json.dumps({
        "Version": 1,
        "AccessKeyId": access_key_id,
        "SecretAccessKey": secret_access_key,
    })


def credential_process(profile_name: str) -> str:
    toml_text = PROFILES_TOML.read_text()
    profile = load_profile(profile_name, toml_text)
    sealed_env = profile["env"]

    if "AWS_ACCESS_KEY_ID" not in sealed_env:
        print(f"Error: profile '{profile_name}' missing AWS_ACCESS_KEY_ID in env.", file=sys.stderr)
        sys.exit(1)
    if "AWS_SECRET_ACCESS_KEY" not in sealed_env:
        print(f"Error: profile '{profile_name}' missing AWS_SECRET_ACCESS_KEY in env.", file=sys.stderr)
        sys.exit(1)

    key_id = decrypt_credential(SEALED_CREDS_DIR / sealed_env["AWS_ACCESS_KEY_ID"])
    secret = decrypt_credential(SEALED_CREDS_DIR / sealed_env["AWS_SECRET_ACCESS_KEY"])

    return build_credential_process_json(key_id, secret)


def list_profiles(toml_str: str) -> str:
    config = tomllib.loads(toml_str) if toml_str else {}
    profiles = config.get("profiles", {})
    if not profiles:
        return "No profiles configured."

    lines = []
    for name, profile in profiles.items():
        desc = profile.get("description", "")
        lines.append(f"{name}: {desc}")
        for var, cred_file in profile.get("env", {}).items():
            lines.append(f"  {var} = {cred_file} (sealed)")
        for var, value in profile.get("env-literal", {}).items():
            lines.append(f"  {var} = {value} (literal)")
    return "\n".join(lines)


def verify_profile(
    profile_name: str, toml_str: str, creds_dir: pathlib.Path
) -> list[dict]:
    profile = load_profile(profile_name, toml_str)
    results = []
    for var, cred_filename in profile["env"].items():
        cred_file = creds_dir / cred_filename
        try:
            decrypt_credential(cred_file)
            results.append({"var": var, "ok": True, "error": None})
        except FileNotFoundError as e:
            results.append({"var": var, "ok": False, "error": str(e)})
        except subprocess.CalledProcessError as e:
            results.append({"var": var, "ok": False, "error": str(e)})
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="secret-run",
        description="Seal and inject TPM-bound secrets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal_parser = subparsers.add_parser("seal", help="Seal a new secret to the TPM.")
    seal_parser.add_argument("--profile", required=True, help="Profile name (e.g. aws-backup).")
    seal_parser.add_argument("--var", required=True, help="Environment variable name (e.g. AWS_ACCESS_KEY_ID).")
    seal_parser.add_argument("--name", required=True, help="Credential name used in the .cred filename (e.g. key-id).")
    seal_parser.add_argument("--stdin", action="store_true", help="Read secret from stdin instead of prompting.")

    run_parser = subparsers.add_parser("run", help="Unseal secrets and run a command.")
    run_parser.add_argument("--profile", required=True, help="Profile name to load from profiles.toml.")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (after --).")

    cp_parser = subparsers.add_parser("credential-process", help="Output AWS credential JSON.")
    cp_parser.add_argument("profile", help="Profile name to load from profiles.toml.")

    subparsers.add_parser("list", help="List all profiles and their env var mappings.")

    verify_parser = subparsers.add_parser("verify", help="Verify all sealed creds in a profile can be decrypted.")
    verify_parser.add_argument("--profile", required=True, help="Profile name to verify.")

    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    if args.command == "seal":
        snippet = seal(profile=args.profile, var=args.var, name=args.name, from_stdin=args.stdin)
        print(f"\nSealed successfully. Add this to {PROFILES_TOML}:\n")
        print(snippet)
    elif args.command == "run":
        cmd = [arg for arg in args.cmd if arg != "--"]
        if not cmd:
            print("Error: no command specified after --.", file=sys.stderr)
            sys.exit(1)
        run_profile(profile_name=args.profile, cmd=cmd)
    elif args.command == "credential-process":
        print(credential_process(args.profile))
    elif args.command == "list":
        toml_text = PROFILES_TOML.read_text()
        print(list_profiles(toml_text))
    elif args.command == "verify":
        toml_text = PROFILES_TOML.read_text()
        results = verify_profile(args.profile, toml_text, SEALED_CREDS_DIR)
        all_ok = True
        for r in results:
            if r["ok"]:
                print(f"  OK: {r['var']}")
            else:
                print(f"  FAIL: {r['var']} — {r['error']}")
                all_ok = False
        if not all_ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
