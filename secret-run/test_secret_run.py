# ABOUTME: Tests for the secret-run CLI tool.
# Covers seal, run (profile loading, decryption, env building, exec),
# credential-process (AWS SDK credential_process JSON output), list, and verify.
# Run with: python -m unittest test_secret_run -v (no pytest)

import json
import os
import pathlib
import subprocess
import unittest
from unittest import mock

import secret_run


class TestCredPath(unittest.TestCase):
    """Output .cred file path follows the convention {profile}.{name}.cred."""

    def test_cred_path(self):
        base = pathlib.Path("/home/user/.local/share/sealed-creds")
        result = secret_run.cred_path(base, profile="aws-backup", name="key-id")
        self.assertEqual(result, base / "aws-backup.key-id.cred")

    def test_cred_path_different_profile(self):
        base = pathlib.Path("/home/user/.local/share/sealed-creds")
        result = secret_run.cred_path(base, profile="gitlab", name="token")
        self.assertEqual(result, base / "gitlab.token.cred")


class TestTomlSnippet(unittest.TestCase):
    """The printed TOML snippet tells the user what to add to profiles.toml."""

    def test_snippet_contains_profile_header(self):
        snippet = secret_run.toml_snippet(
            profile="aws-backup",
            var="AWS_ACCESS_KEY_ID",
            cred_filename="aws-backup.key-id.cred",
        )
        self.assertIn('[profiles.aws-backup.env]', snippet)

    def test_snippet_contains_var_mapping(self):
        snippet = secret_run.toml_snippet(
            profile="aws-backup",
            var="AWS_ACCESS_KEY_ID",
            cred_filename="aws-backup.key-id.cred",
        )
        self.assertIn('AWS_ACCESS_KEY_ID = "aws-backup.key-id.cred"', snippet)


class TestBuildEncryptCommand(unittest.TestCase):
    """The systemd-creds encrypt command is constructed correctly."""

    def test_command_structure(self):
        out = pathlib.Path("/home/user/.local/share/sealed-creds/aws-backup.key-id.cred")
        cmd = secret_run.build_encrypt_command(name="key-id", output_path=out)
        self.assertEqual(cmd, [
            "systemd-creds", "encrypt",
            "--with-key=tpm2+host",
            "--user",
            "--name=key-id",
            "-",
            str(out),
        ])


class TestSeal(unittest.TestCase):
    """Integration-level test for the seal function with mocked I/O."""

    @mock.patch("secret_run.subprocess.run")
    @mock.patch("secret_run.getpass.getpass", return_value="my-secret-value")
    def test_seal_calls_systemd_creds(self, mock_getpass, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        base = pathlib.Path("/tmp/test-sealed-creds")

        with mock.patch("secret_run.SEALED_CREDS_DIR", base):
            with mock.patch("pathlib.Path.mkdir"):
                result = secret_run.seal(
                    profile="aws-backup", var="AWS_ACCESS_KEY_ID", name="key-id"
                )

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        self.assertEqual(cmd[0], "systemd-creds")
        self.assertEqual(cmd[1], "encrypt")
        self.assertIn("--with-key=tpm2+host", cmd)
        self.assertIn("--user", cmd)
        self.assertIn("--name=key-id", cmd)
        self.assertEqual(call_args[1]["input"], b"my-secret-value")
        self.assertEqual(call_args[1]["check"], True)

    @mock.patch("secret_run.subprocess.run")
    @mock.patch("secret_run.getpass.getpass", return_value="my-secret-value")
    def test_seal_returns_toml_snippet(self, mock_getpass, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        base = pathlib.Path("/tmp/test-sealed-creds")

        with mock.patch("secret_run.SEALED_CREDS_DIR", base):
            with mock.patch("pathlib.Path.mkdir"):
                result = secret_run.seal(
                    profile="aws-backup", var="AWS_ACCESS_KEY_ID", name="key-id"
                )

        self.assertIn("AWS_ACCESS_KEY_ID", result)
        self.assertIn("aws-backup.key-id.cred", result)


class TestSealFromStdin(unittest.TestCase):
    """seal reads from stdin when --stdin is passed."""

    @mock.patch("secret_run.subprocess.run")
    @mock.patch("secret_run.sys.stdin")
    def test_seal_reads_stdin_instead_of_getpass(self, mock_stdin, mock_run):
        mock_stdin.read.return_value = "piped-secret\n"
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        base = pathlib.Path("/tmp/test-sealed-creds")

        with mock.patch("secret_run.SEALED_CREDS_DIR", base):
            with mock.patch("pathlib.Path.mkdir"):
                result = secret_run.seal(
                    profile="aws-backup", var="AWS_ACCESS_KEY_ID",
                    name="key-id", from_stdin=True,
                )

        call_args = mock_run.call_args
        self.assertEqual(call_args[1]["input"], b"piped-secret")

    @mock.patch("secret_run.subprocess.run")
    @mock.patch("secret_run.sys.stdin")
    def test_seal_stdin_strips_trailing_newline(self, mock_stdin, mock_run):
        mock_stdin.read.return_value = "secret-with-newline\n"
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        base = pathlib.Path("/tmp/test-sealed-creds")

        with mock.patch("secret_run.SEALED_CREDS_DIR", base):
            with mock.patch("pathlib.Path.mkdir"):
                secret_run.seal(
                    profile="test", var="TOKEN",
                    name="tok", from_stdin=True,
                )

        call_args = mock_run.call_args
        self.assertEqual(call_args[1]["input"], b"secret-with-newline")


class TestParseArgs(unittest.TestCase):
    """Argument parsing for the seal subcommand."""

    def test_seal_args(self):
        args = secret_run.parse_args([
            "seal", "--profile", "aws-backup",
            "--var", "AWS_ACCESS_KEY_ID", "--name", "key-id",
        ])
        self.assertEqual(args.command, "seal")
        self.assertEqual(args.profile, "aws-backup")
        self.assertEqual(args.var, "AWS_ACCESS_KEY_ID")
        self.assertEqual(args.name, "key-id")

    def test_seal_stdin_flag(self):
        args = secret_run.parse_args([
            "seal", "--profile", "test", "--var", "TOKEN",
            "--name", "tok", "--stdin",
        ])
        self.assertTrue(args.stdin)


class TestCredNameFromFilename(unittest.TestCase):
    """Credential name is extracted from the {profile}.{name}.cred convention."""

    def test_extracts_name(self):
        self.assertEqual(secret_run.cred_name_from_filename("aws-backup.key-id.cred"), "key-id")

    def test_extracts_name_with_dots(self):
        self.assertEqual(secret_run.cred_name_from_filename("myprofile.api.token.cred"), "api.token")

    def test_no_profile_prefix(self):
        self.assertEqual(secret_run.cred_name_from_filename("token.cred"), "token")


class TestBuildDecryptCommand(unittest.TestCase):
    """The systemd-creds decrypt command is constructed correctly."""

    def test_command_structure(self):
        cred = pathlib.Path("/home/user/.local/share/sealed-creds/aws-backup.key-id.cred")
        cmd = secret_run.build_decrypt_command(cred)
        self.assertEqual(cmd, [
            "systemd-creds", "decrypt",
            "--user",
            "--name=key-id",
            str(cred),
            "-",
        ])


SAMPLE_PROFILES_TOML = """\
[profiles.aws-backup]
description = "S3 credentials for NAS backup via Garage"

[profiles.aws-backup.env]
AWS_ACCESS_KEY_ID = "aws-backup.key-id.cred"
AWS_SECRET_ACCESS_KEY = "aws-backup.secret.cred"

[profiles.aws-backup.env-literal]
AWS_DEFAULT_REGION = "garage"
AWS_ENDPOINT_URL = "https://nas.example.ts.net:3900"
"""


class TestLoadProfile(unittest.TestCase):
    """Profile loading extracts env and env-literal mappings."""

    def test_load_env_mappings(self):
        profile = secret_run.load_profile("aws-backup", SAMPLE_PROFILES_TOML)
        self.assertEqual(profile["env"]["AWS_ACCESS_KEY_ID"], "aws-backup.key-id.cred")
        self.assertEqual(profile["env"]["AWS_SECRET_ACCESS_KEY"], "aws-backup.secret.cred")

    def test_load_env_literal_mappings(self):
        profile = secret_run.load_profile("aws-backup", SAMPLE_PROFILES_TOML)
        self.assertEqual(profile["env-literal"]["AWS_DEFAULT_REGION"], "garage")

    def test_missing_profile_raises(self):
        with self.assertRaises(SystemExit):
            secret_run.load_profile("nonexistent", SAMPLE_PROFILES_TOML)

    def test_profile_without_env_literal(self):
        toml_str = """\
[profiles.minimal]
description = "Just secrets, no literals"

[profiles.minimal.env]
TOKEN = "minimal.token.cred"
"""
        profile = secret_run.load_profile("minimal", toml_str)
        self.assertEqual(profile["env"]["TOKEN"], "minimal.token.cred")
        self.assertEqual(profile["env-literal"], {})


class TestDecryptCredential(unittest.TestCase):
    """decrypt_credential calls systemd-creds and returns plaintext."""

    @mock.patch("secret_run.subprocess.run")
    def test_returns_stdout(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"AKIAIOSFODNN7EXAMPLE"
        )
        cred = pathlib.Path("/home/user/.local/share/sealed-creds/aws-backup.key-id.cred")
        result = secret_run.decrypt_credential(cred)
        self.assertEqual(result, "AKIAIOSFODNN7EXAMPLE")

    @mock.patch("secret_run.subprocess.run")
    def test_calls_decrypt_with_user(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"secret"
        )
        cred = pathlib.Path("/tmp/myprofile.test.cred")
        secret_run.decrypt_credential(cred)
        cmd = mock_run.call_args[0][0]
        self.assertIn("--user", cmd)
        self.assertIn("--name=test", cmd)
        self.assertEqual(cmd[0:2], ["systemd-creds", "decrypt"])


class TestRunParseArgs(unittest.TestCase):
    """Argument parsing for the run subcommand."""

    def test_run_args(self):
        args = secret_run.parse_args([
            "run", "--profile", "aws-backup", "--", "aws", "s3", "ls",
        ])
        self.assertEqual(args.command, "run")
        self.assertEqual(args.profile, "aws-backup")
        # REMAINDER includes the -- separator; main() strips it before use
        self.assertEqual(args.cmd, ["--", "aws", "s3", "ls"])

    def test_run_args_single_command(self):
        args = secret_run.parse_args([
            "run", "--profile", "aws-backup", "--", "bash",
        ])
        self.assertEqual(args.cmd, ["--", "bash"])


class TestBuildRunEnv(unittest.TestCase):
    """build_run_env merges decrypted secrets and literals into the env."""

    @mock.patch("secret_run.decrypt_credential")
    def test_merges_secrets_and_literals(self, mock_decrypt):
        mock_decrypt.side_effect = lambda path: {
            "aws-backup.key-id.cred": "AKIAEXAMPLE",
            "aws-backup.secret.cred": "SECRETEXAMPLE",
        }[path.name]

        base = pathlib.Path("/home/user/.local/share/sealed-creds")
        env = secret_run.build_run_env(
            base_env={"HOME": "/home/user", "PATH": "/usr/bin"},
            sealed_env={"AWS_ACCESS_KEY_ID": "aws-backup.key-id.cred",
                        "AWS_SECRET_ACCESS_KEY": "aws-backup.secret.cred"},
            literal_env={"AWS_DEFAULT_REGION": "garage"},
            creds_dir=base,
        )

        self.assertEqual(env["AWS_ACCESS_KEY_ID"], "AKIAEXAMPLE")
        self.assertEqual(env["AWS_SECRET_ACCESS_KEY"], "SECRETEXAMPLE")
        self.assertEqual(env["AWS_DEFAULT_REGION"], "garage")
        self.assertEqual(env["HOME"], "/home/user")


class TestCredentialProcessParseArgs(unittest.TestCase):
    """Argument parsing for the credential-process subcommand."""

    def test_credential_process_args(self):
        args = secret_run.parse_args(["credential-process", "aws-backup"])
        self.assertEqual(args.command, "credential-process")
        self.assertEqual(args.profile, "aws-backup")


class TestBuildCredentialProcessJson(unittest.TestCase):
    """credential_process JSON output matches the AWS SDK contract."""

    def test_has_required_fields(self):
        result = secret_run.build_credential_process_json(
            access_key_id="AKIAEXAMPLE",
            secret_access_key="SECRETEXAMPLE",
        )
        parsed = json.loads(result)
        self.assertEqual(parsed["Version"], 1)
        self.assertEqual(parsed["AccessKeyId"], "AKIAEXAMPLE")
        self.assertEqual(parsed["SecretAccessKey"], "SECRETEXAMPLE")

    def test_no_extra_fields(self):
        result = secret_run.build_credential_process_json(
            access_key_id="AKIAEXAMPLE",
            secret_access_key="SECRETEXAMPLE",
        )
        parsed = json.loads(result)
        self.assertEqual(set(parsed.keys()), {"Version", "AccessKeyId", "SecretAccessKey"})

    def test_output_is_valid_json(self):
        result = secret_run.build_credential_process_json(
            access_key_id="AKIA",
            secret_access_key="SECRET",
        )
        json.loads(result)  # Should not raise


class TestCredentialProcess(unittest.TestCase):
    """Integration test for credential_process with mocked decryption."""

    @mock.patch("secret_run.decrypt_credential")
    def test_returns_json_with_decrypted_values(self, mock_decrypt):
        mock_decrypt.side_effect = lambda path: {
            "aws-backup.key-id.cred": "AKIAEXAMPLE",
            "aws-backup.secret.cred": "SECRETEXAMPLE",
        }[path.name]

        base = pathlib.Path("/home/user/.local/share/sealed-creds")
        with mock.patch("secret_run.SEALED_CREDS_DIR", base):
            with mock.patch("secret_run.PROFILES_TOML") as mock_toml:
                mock_toml.read_text.return_value = SAMPLE_PROFILES_TOML
                result = secret_run.credential_process("aws-backup")

        parsed = json.loads(result)
        self.assertEqual(parsed["Version"], 1)
        self.assertEqual(parsed["AccessKeyId"], "AKIAEXAMPLE")
        self.assertEqual(parsed["SecretAccessKey"], "SECRETEXAMPLE")

    def test_missing_key_id_raises(self):
        toml_str = """\
[profiles.bad]
description = "Missing key id"

[profiles.bad.env]
AWS_SECRET_ACCESS_KEY = "bad.secret.cred"
"""
        with mock.patch("secret_run.PROFILES_TOML") as mock_toml:
            mock_toml.read_text.return_value = toml_str
            with self.assertRaises(SystemExit):
                secret_run.credential_process("bad")

    def test_missing_secret_key_raises(self):
        toml_str = """\
[profiles.bad]
description = "Missing secret"

[profiles.bad.env]
AWS_ACCESS_KEY_ID = "bad.key-id.cred"
"""
        with mock.patch("secret_run.PROFILES_TOML") as mock_toml:
            mock_toml.read_text.return_value = toml_str
            with self.assertRaises(SystemExit):
                secret_run.credential_process("bad")


MULTI_PROFILE_TOML = """\
[profiles.aws-backup]
description = "S3 credentials for NAS backup via Garage"

[profiles.aws-backup.env]
AWS_ACCESS_KEY_ID = "aws-backup.key-id.cred"
AWS_SECRET_ACCESS_KEY = "aws-backup.secret.cred"

[profiles.aws-backup.env-literal]
AWS_DEFAULT_REGION = "garage"
AWS_ENDPOINT_URL = "https://nas.example.ts.net:3900"

[profiles.restic-backup]
description = "Restic repo password"

[profiles.restic-backup.env]
RESTIC_PASSWORD = "restic-backup.password.cred"
"""


class TestListProfiles(unittest.TestCase):
    """list_profiles returns a summary of all configured profiles."""

    def test_lists_all_profiles(self):
        result = secret_run.list_profiles(MULTI_PROFILE_TOML)
        self.assertIn("aws-backup", result)
        self.assertIn("restic-backup", result)

    def test_shows_description(self):
        result = secret_run.list_profiles(MULTI_PROFILE_TOML)
        self.assertIn("S3 credentials for NAS backup via Garage", result)
        self.assertIn("Restic repo password", result)

    def test_shows_sealed_env_vars(self):
        result = secret_run.list_profiles(MULTI_PROFILE_TOML)
        self.assertIn("AWS_ACCESS_KEY_ID", result)
        self.assertIn("AWS_SECRET_ACCESS_KEY", result)
        self.assertIn("RESTIC_PASSWORD", result)

    def test_shows_literal_env_vars(self):
        result = secret_run.list_profiles(MULTI_PROFILE_TOML)
        self.assertIn("AWS_DEFAULT_REGION", result)

    def test_empty_profiles(self):
        result = secret_run.list_profiles("")
        self.assertIn("No profiles", result)


class TestListParseArgs(unittest.TestCase):
    """Argument parsing for the list subcommand."""

    def test_list_args(self):
        args = secret_run.parse_args(["list"])
        self.assertEqual(args.command, "list")


class TestVerifyProfile(unittest.TestCase):
    """verify_profile checks that all sealed creds in a profile can decrypt."""

    @mock.patch("secret_run.decrypt_credential")
    def test_all_ok(self, mock_decrypt):
        mock_decrypt.return_value = "decrypted"
        base = pathlib.Path("/home/user/.local/share/sealed-creds")

        results = secret_run.verify_profile("aws-backup", SAMPLE_PROFILES_TOML, base)

        self.assertTrue(all(r["ok"] for r in results))
        self.assertEqual(len(results), 2)

    @mock.patch("secret_run.decrypt_credential")
    def test_reports_failure(self, mock_decrypt):
        mock_decrypt.side_effect = subprocess.CalledProcessError(1, "systemd-creds")
        base = pathlib.Path("/home/user/.local/share/sealed-creds")

        results = secret_run.verify_profile("aws-backup", SAMPLE_PROFILES_TOML, base)

        self.assertTrue(all(not r["ok"] for r in results))

    @mock.patch("secret_run.decrypt_credential")
    def test_reports_missing_file(self, mock_decrypt):
        mock_decrypt.side_effect = FileNotFoundError("not found")
        base = pathlib.Path("/home/user/.local/share/sealed-creds")

        results = secret_run.verify_profile("aws-backup", SAMPLE_PROFILES_TOML, base)

        self.assertTrue(all(not r["ok"] for r in results))
        self.assertTrue(any("not found" in r["error"].lower() or "no such file" in r["error"].lower() for r in results))

    @mock.patch("secret_run.decrypt_credential")
    def test_result_includes_var_name(self, mock_decrypt):
        mock_decrypt.return_value = "decrypted"
        base = pathlib.Path("/home/user/.local/share/sealed-creds")

        results = secret_run.verify_profile("aws-backup", SAMPLE_PROFILES_TOML, base)

        var_names = [r["var"] for r in results]
        self.assertIn("AWS_ACCESS_KEY_ID", var_names)
        self.assertIn("AWS_SECRET_ACCESS_KEY", var_names)


class TestVerifyParseArgs(unittest.TestCase):
    """Argument parsing for the verify subcommand."""

    def test_verify_args(self):
        args = secret_run.parse_args(["verify", "--profile", "aws-backup"])
        self.assertEqual(args.command, "verify")
        self.assertEqual(args.profile, "aws-backup")


if __name__ == "__main__":
    unittest.main()
