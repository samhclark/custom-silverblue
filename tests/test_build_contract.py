from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
CONTAINERFILE = (REPO / "Containerfile").read_text()
WORKFLOW = (REPO / ".github/workflows/reusable-build.yaml").read_text()
MAIN_WORKFLOW = (REPO / ".github/workflows/build.yaml").read_text()
RELEASE_WORKFLOW = (REPO / ".github/workflows/release.yaml").read_text()


class BuildContractTests(unittest.TestCase):
    def test_selinux_policy_store_is_copied_up_before_dnf(self):
        package_layer = CONTAINERFILE[
            CONTAINERFILE.index("# Install the packages") : CONTAINERFILE.index(
                '\n\nRUN ["bootc", "container", "lint"]'
            )
        ]
        steps = (
            "cp -a /etc/selinux/targeted /etc/selinux/targeted.rebuilt",
            "rm -rf /etc/selinux/targeted",
            "mv /etc/selinux/targeted.rebuilt /etc/selinux/targeted",
            "python3 /dnfdef.py",
        )
        positions = [package_layer.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(CONTAINERFILE.count(steps[0]), 1)

    def test_runtime_inputs_follow_package_layer(self):
        package_layer = CONTAINERFILE.index("RUN --mount=type=bind")

        self.assertLess(
            CONTAINERFILE.index("COPY overlay-root/etc/pki/rpm-gpg/"),
            package_layer,
        )
        self.assertLess(
            CONTAINERFILE.index("COPY overlay-root/etc/yum.repos.d/"),
            package_layer,
        )
        self.assertGreater(CONTAINERFILE.index("COPY overlay-root/ /"), package_layer)
        self.assertGreater(
            CONTAINERFILE.index("COPY secret-run/secret_run.py"),
            package_layer,
        )
        self.assertGreater(
            CONTAINERFILE.index("COPY secret-run/laptop-backup.sh"),
            package_layer,
        )

    def test_ci_preserves_layers_and_omits_remote_cache(self):
        self.assertIn("layers: true", WORKFLOW)
        self.assertIn("squash: false", WORKFLOW)
        self.assertNotIn("cache_ref:", WORKFLOW)
        self.assertNotIn("cache_ref:", MAIN_WORKFLOW)
        self.assertNotIn("--cache-from", WORKFLOW)
        self.assertNotIn("--cache-to", WORKFLOW)

    def test_scheduled_build_has_no_release_privileges_or_gate(self):
        self.assertIn("  schedule:", MAIN_WORKFLOW)
        self.assertIn("      publish: false", MAIN_WORKFLOW)
        self.assertNotIn("publish: true", MAIN_WORKFLOW)
        self.assertNotIn(": write", MAIN_WORKFLOW)
        self.assertNotIn("secrets:", MAIN_WORKFLOW)
        self.assertNotIn("environment:", MAIN_WORKFLOW)
        # Checks and builds must also run on the schedule, without event guards.
        self.assertNotIn("    if:", MAIN_WORKFLOW)

    def test_release_requires_manual_dispatch_on_main_and_passing_checks(self):
        triggers = RELEASE_WORKFLOW.split("on:\n", 1)[1].split("\npermissions:")[0]
        self.assertEqual(triggers.strip(), "workflow_dispatch:")
        publish_job = RELEASE_WORKFLOW.split("  publish-custom-silverblue:", 1)[1]
        self.assertIn("    needs: lint", publish_job)
        self.assertIn("github.ref == 'refs/heads/main'", publish_job)
        self.assertIn("      publish: true", publish_job)
        self.assertIn("  cancel-in-progress: false", RELEASE_WORKFLOW)

        # Keep the guard at the privileged job too, for other reusable callers.
        privileged_job = WORKFLOW.split("  build-sign-push-custom-silverblue:", 1)[1]
        self.assertIn("github.event_name == 'workflow_dispatch'", privileged_job)
        self.assertIn("github.ref == 'refs/heads/main'", privileged_job)
        self.assertIn("    environment: release", privileged_job)

    def test_release_verifies_signature_of_the_published_digest(self):
        push = WORKFLOW.index("      - name: Push to Container Registry")
        sign = WORKFLOW.index("      - name: Sign the published OCI image")
        verify = WORKFLOW.index(
            "      - name: Verify the published OCI image signature"
        )
        self.assertLess(push, sign)
        self.assertLess(sign, verify)
        verification_step = WORKFLOW[verify:].split("\n      - name:", 1)[0]
        self.assertIn(
            "verify --key overlay-root/etc/pki/cosign/cosign.pub", verification_step
        )
        self.assertIn("@${{ steps.push.outputs.digest }}", verification_step)


if __name__ == "__main__":
    unittest.main()
